"""The Onkyo NG component."""
from homeassistant import config_entries, exceptions
from homeassistant.components import zeroconf
from homeassistant.data_entry_flow import FlowResult

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.helpers import config_validation as cv

import eiscp

from typing import Any
import ipaddress

import logging
import voluptuous as vol

from .onkyo import OnkyoReceiver

from .const import (
    DOMAIN,
    INFO_HOST,
    INFO_IDENTIFIER,
    INFO_MODEL_NAME,
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
        self.receiver: eiscp.eISCP = None
        self.host: str = None

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
                onkyo_receiver = OnkyoReceiver(host, hass=None)
                try:
                    info = onkyo_receiver._receiver_info
                    if info:
                        _LOGGER.debug("Found host: %s", host)
                    else:
                        _LOGGER.debug("Host not found: %s", host)
                        raise ConnectionError()

                    # use the MAC as unique id
                    unique_id = info['macaddress']
                    model_name = info['model']

                    # check if we got something
                    if not unique_id:
                        raise UnsupportedModel()

                    # set the unique id for the entry, abort if it already exists
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                finally:
                    onkyo_receiver.disconnect()

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

        # extract some data from zeroconf
        self.host = discovery_info.host
        _LOGGER.debug("Zeroconf discovered: %s", discovery_info)

        # if the hostname already exists, we can stop
        self._async_abort_entries_match({CONF_HOST: self.host})

        # now let's try and see if we can connect to a printer
        receiver = None
        for device in eiscp.eISCP.discover():
            found_host = device.info[INFO_HOST]
            if found_host == self.host:
                _LOGGER.debug("Found host: %s", self.host)
                receiver = device
                break

        if not receiver:
            _LOGGER.debug("Host not found: %s", self.host)
            raise ConnectionError()

        info = receiver.info

        # use the MAC as unique id
        unique_id = info[INFO_IDENTIFIER]
        model_name = info[INFO_MODEL_NAME]

        # check if we got something
        if not unique_id:
            self.async_abort(reason="unsupported_model")

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
                    CONF_HOST: self.host,
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
