"""The Onkyo NG component."""
from homeassistant import config_entries, exceptions
from homeassistant.components import zeroconf
from homeassistant.data_entry_flow import FlowResult

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.helpers import config_validation as cv

from typing import Any
import ipaddress

import logging
import voluptuous as vol

from .onkyo import OnkyoReceiver

from .const import (
    DOMAIN,
    POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in [4, 6]:
            return True
    except ValueError:
        return False


class UnsupportedModel(Exception):
    """Raised when no model, serial no, firmware data."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate that hostname/IP address is invalid."""


class OnkyoReceiverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Onkyo receivers."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self.host: str = None
        _LOGGER.info("Created Onkyo config flow")

    def _get_schema(self, user_input):
        """Provide schema for user input."""
        if user_input is None:
            user_input = {}

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME, default=user_input.get(CONF_NAME, "")
                ): cv.string,
                vol.Required(
                    CONF_HOST, default=user_input.get(CONF_HOST, "")
                ): cv.string,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=user_input.get(CONF_SCAN_INTERVAL, POLLING_INTERVAL),
                ): vol.All(cv.positive_int, vol.Range(min=10, max=600)),
            }
        )
        return schema

    async def async_confirm_receiver(self, host: str) -> (str, str):
        _LOGGER.info("Connecting to receiver: {}", host)
        onkyo_receiver = OnkyoReceiver(host, hass=None)
        try:
            info = await onkyo_receiver.get_receiver_info()
            if info:
                _LOGGER.debug("Retrieved receiver information")
                return info.macaddress, info.model

            raise UnsupportedModel()
        finally:
            onkyo_receiver.disconnect()

    async def async_step_user(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Handle initial step of user config flow."""

        errors = {}

        # user input was provided, so check and save it
        if user_input is not None:
            try:
                # first some sanitycheck on the host input
                host = user_input[CONF_HOST]
                if not host_valid(host):
                    _LOGGER.debug("Invalid host: %s", host)
                    raise InvalidHost()

                # now let's try and see if we can connect to a receiver
                unique_id, model_name = await self.async_confirm_receiver(host)

                # set the unique id for the entry, abort if it already exists
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # compile a name from model and serial
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or model_name, data=user_input
                )

            except InvalidHost:
                errors[CONF_HOST] = "Wrong host"
            except ConnectionError:
                errors[CONF_HOST] = "Cannot connect to device"
            except UnsupportedModel:
                errors["base"] = "Receiver model not supported"

        # no user_input so far
        # what to ask the user
        schema = self._get_schema(user_input)

        # show the form to the user
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo = None
    ):
        """Handle zeroconf flow."""

        errors = {}

        if discovery_info.hostname.lower().startswith("onkyo"):
            # Found possible Onkyo receiver
            if discovery_info.ip_address.version != 4:
                return self.async_abort(reason="Only IPv4 is supported")
            self.host = discovery_info.host
        else:
            return self.async_abort(reason="Not Onkyo receiver")

        _LOGGER.info("Zeroconf discovered: %s", discovery_info)

        # if the hostname already exists, we can stop
        self._async_abort_entries_match({CONF_HOST: self.host})

        try:
            # now let's try and see if we can connect to a receiver
            _LOGGER.info("Onkyo connect to {}", self.host)
            # now let's try and see if we can connect to a receiver
            unique_id, model_name = await self.async_confirm_receiver(self.host)

            # set the unique id for the entry, abort if it already exists
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # store the data for the next step to get confirmation
            self.context.update(
                {
                    "title_placeholders": {
                        CONF_NAME: model_name,
                        CONF_SCAN_INTERVAL: POLLING_INTERVAL,
                    }
                }
            )

            # show the form to the user
            return await self.async_step_zeroconf_confirm()
        except:
            return self.async_abort(reason="Exception during zeroconf flow")

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Confirm the zeroconf discovered data."""

        # user input was provided, so check and save it
        if user_input is not None:

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )

        # show the form to the user
        name = user_input[CONF_NAME]
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=name): cv.string,
                    vol.Required(CONF_SCAN_INTERVAL, default=POLLING_INTERVAL): vol.All(
                        cv.positive_int, vol.Range(min=10, max=600)
                    ),
                }
            ),
            description_placeholders={CONF_HOST: self.host, "model": name},
        )
