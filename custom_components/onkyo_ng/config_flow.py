"""Config flow for Onkyo."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    Selector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_MODES,
    CONF_RECEIVER_MAX_VOLUME,
    CONF_SOURCES,
    DOMAIN,
    OPTION_INPUT_SOURCES,
    OPTION_LISTENING_MODES,
    OPTION_MAX_VOLUME,
    OPTION_MAX_VOLUME_DEFAULT,
    OPTION_VOLUME_RESOLUTION,
    OPTION_VOLUME_RESOLUTION_DEFAULT,
    VOLUME_RESOLUTION_ALLOWED,
    InputSource,
    ListeningMode,
)
from .receiver import ReceiverInfo, async_discover, async_interview

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"

INPUT_SOURCES_ALL_MEANINGS = [
    input_source.value_meaning for input_source in InputSource
]
LISTENING_MODES_ALL_MEANINGS = [
    listening_mode.value_meaning for listening_mode in ListeningMode
]

STEP_MANUAL_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})
STEP_CONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(OPTION_VOLUME_RESOLUTION): vol.In(VOLUME_RESOLUTION_ALLOWED),
        vol.Required(OPTION_INPUT_SOURCES): SelectSelector(
            SelectSelectorConfig(
                options=INPUT_SOURCES_ALL_MEANINGS,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(OPTION_LISTENING_MODES): SelectSelector(
            SelectSelectorConfig(
                options=LISTENING_MODES_ALL_MEANINGS,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


class OnkyoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Onkyo config flow."""

    _receiver_info: ReceiverInfo
    _discovered_infos: dict[str, ReceiverInfo]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return self.async_show_menu(
            step_id="user", menu_options=["manual", "eiscp_discovery"]
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual device entry."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            _LOGGER.debug("Config flow start manual: %s", host)
            try:
                info = await async_interview(host)
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if info is None:
                    errors["base"] = "cannot_connect"
                else:
                    self._receiver_info = info

                    await self.async_set_unique_id(
                        info.identifier, raise_on_progress=False
                    )
                    if self.source == SOURCE_RECONFIGURE:
                        self._abort_if_unique_id_mismatch()
                    else:
                        self._abort_if_unique_id_configured()

                    return await self.async_step_configure_receiver()

        suggested_values = user_input
        if suggested_values is None and self.source == SOURCE_RECONFIGURE:
            suggested_values = {
                CONF_HOST: self._get_reconfigure_entry().data[CONF_HOST]
            }

        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(
                STEP_MANUAL_SCHEMA, suggested_values
            ),
            errors=errors,
        )

    async def async_step_eiscp_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start eiscp discovery and handle user device selection."""
        if user_input is not None:
            self._receiver_info = self._discovered_infos[user_input[CONF_DEVICE]]
            await self.async_set_unique_id(
                self._receiver_info.identifier, raise_on_progress=False
            )
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: self._receiver_info.host}
            )
            return await self.async_step_configure_receiver()

        _LOGGER.debug("Config flow start eiscp discovery")

        try:
            infos = await async_discover()
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        _LOGGER.debug("Discovered devices: %s", infos)

        self._discovered_infos = {}
        discovered_names = {}
        current_unique_ids = self._async_current_ids()
        for info in infos:
            if info.identifier in current_unique_ids:
                continue
            self._discovered_infos[info.identifier] = info
            device_name = f"{info.model_name} ({info.host})"
            discovered_names[info.identifier] = device_name

        _LOGGER.debug("Discovered new devices: %s", self._discovered_infos)

        if not discovered_names:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="eiscp_discovery",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE): vol.In(discovered_names)}
            ),
        )

    async def async_step_configure_receiver(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the configuration of a single receiver."""
        errors = {}

        entry = None
        entry_options = None
        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            entry_options = entry.options

        if user_input is not None:
            source_meanings: list[str] = user_input[OPTION_INPUT_SOURCES]
            mode_meanings: list[str] = user_input[OPTION_LISTENING_MODES]

            if not source_meanings:
                errors[OPTION_INPUT_SOURCES] = "empty_input_source_list"
            elif not mode_meanings:
                errors[OPTION_LISTENING_MODES] = "empty_listening_mode_list"
            else:
                sources_store: dict[str, str] = {}
                modes_store: dict[str, str] = {}

                for source_meaning in source_meanings:
                    source = InputSource.from_meaning(source_meaning)

                    source_name = source_meaning
                    if entry_options is not None:
                        source_name = entry_options[OPTION_INPUT_SOURCES].get(
                            source.value, source_name
                        )
                    sources_store[source.value] = source_name

                for mode_meaning in mode_meanings:
                    mode = ListeningMode.from_meaning(mode_meaning)

                    mode_name = mode_meaning
                    if entry_options is not None:
                        mode_name = entry_options[OPTION_LISTENING_MODES].get(
                            mode.value, mode_name
                        )
                    modes_store[mode.value] = mode_name

                volume_resolution = user_input[OPTION_VOLUME_RESOLUTION]

                if entry_options is None:
                    result = self.async_create_entry(
                        title=self._receiver_info.model_name,
                        data={
                            CONF_HOST: self._receiver_info.host,
                        },
                        options={
                            OPTION_VOLUME_RESOLUTION: volume_resolution,
                            OPTION_MAX_VOLUME: OPTION_MAX_VOLUME_DEFAULT,
                            OPTION_INPUT_SOURCES: sources_store,
                            OPTION_LISTENING_MODES: modes_store,
                        },
                    )
                else:
                    assert entry is not None
                    result = self.async_update_reload_and_abort(
                        entry,
                        data={
                            CONF_HOST: self._receiver_info.host,
                        },
                        options={
                            OPTION_VOLUME_RESOLUTION: volume_resolution,
                            OPTION_MAX_VOLUME: entry_options[OPTION_MAX_VOLUME],
                            OPTION_INPUT_SOURCES: sources_store,
                            OPTION_LISTENING_MODES: modes_store,
                        },
                    )

                _LOGGER.debug("Configured receiver, result: %s", result)
                return result

        _LOGGER.debug("Configuring receiver, info: %s", self._receiver_info)

        suggested_values = user_input
        if suggested_values is None:
            if entry_options is None:
                suggested_values = {
                    OPTION_VOLUME_RESOLUTION: OPTION_VOLUME_RESOLUTION_DEFAULT,
                    OPTION_INPUT_SOURCES: [],
                    OPTION_LISTENING_MODES: [],
                }
            else:
                suggested_values = {
                    OPTION_VOLUME_RESOLUTION: entry_options[OPTION_VOLUME_RESOLUTION],
                    OPTION_INPUT_SOURCES: [
                        InputSource(input_source).value_meaning
                        for input_source in entry_options[OPTION_INPUT_SOURCES]
                    ],
                    OPTION_LISTENING_MODES: [
                        ListeningMode(listening_mode).value_meaning
                        for listening_mode in entry_options[OPTION_LISTENING_MODES]
                    ],
                }

        return self.async_show_form(
            step_id="configure_receiver",
            data_schema=self.add_suggested_values_to_schema(
                STEP_CONFIGURE_SCHEMA, suggested_values
            ),
            errors=errors,
            description_placeholders={
                "name": f"{self._receiver_info.model_name} ({self._receiver_info.host})"
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the receiver."""
        return await self.async_step_manual()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Return the options flow."""
        return OnkyoOptionsFlowHandler(config_entry)


class OnkyoOptionsFlowHandler(OptionsFlow):
    """Handle an options flow for Onkyo."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        sources_store: dict[str, str] = config_entry.options[OPTION_INPUT_SOURCES]
        self._input_sources = {InputSource(k): v for k, v in sources_store.items()}
        modes_store: dict[str, str] = config_entry.options[OPTION_LISTENING_MODES]
        self._listening_modes = {ListeningMode(k): v for k, v in modes_store.items()}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            sources_store: dict[str, str] = {}
            for source_meaning, source_name in user_input.items():
                if source_meaning in INPUT_SOURCES_ALL_MEANINGS:
                    source = InputSource.from_meaning(source_meaning)
                    sources_store[source.value] = source_name

            modes_store: dict[str, str] = {}
            for mode_meaning, mode_name in user_input.items():
                if mode_meaning in LISTENING_MODES_ALL_MEANINGS:
                    mode = ListeningMode.from_meaning(mode_meaning)
                    modes_store[mode.value] = mode_name

            return self.async_create_entry(
                data={
                    OPTION_VOLUME_RESOLUTION: self.config_entry.options[
                        OPTION_VOLUME_RESOLUTION
                    ],
                    OPTION_MAX_VOLUME: user_input[OPTION_MAX_VOLUME],
                    OPTION_INPUT_SOURCES: sources_store,
                    OPTION_LISTENING_MODES: modes_store,
                }
            )

        schema_dict: dict[Any, Selector] = {}

        max_volume: float = self.config_entry.options[OPTION_MAX_VOLUME]
        schema_dict[vol.Required(OPTION_MAX_VOLUME, default=max_volume)] = (
            NumberSelector(
                NumberSelectorConfig(min=1, max=100, mode=NumberSelectorMode.BOX)
            )
        )

        for source, source_name in self._input_sources.items():
            schema_dict[vol.Required(source.value_meaning, default=source_name)] = (
                TextSelector()
            )

        for mode, mode_name in self._listening_modes.items():
            schema_dict[vol.Required(mode.value_meaning, default=mode_name)] = (
                TextSelector()
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )
