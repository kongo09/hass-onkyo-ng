"""The Onkyo AV receiver component."""
from __future__ import annotations
from datetime import timedelta
from typing import Any

from .const import *

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)

from .onkyo import OnkyoReceiver

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup an Onkyo AV receiver from a config entry."""

    # get the host address
    host = entry.data[CONF_HOST]

    # get the receiver
    update_interval = entry.data[CONF_SCAN_INTERVAL]

    try:
        onkyo_receiver = OnkyoReceiver(
            host=host,
            hass=hass,
            max_volume=ONKYO_SUPPORTED_MAX_VOLUME,
            receiver_max_volume=ONKYO_DEFAULT_RECEIVER_MAX_VOLUME,
        )
        await onkyo_receiver.load_data()

        receiver_info = await onkyo_receiver.get_receiver_info()
        basic_receiver_info = await onkyo_receiver.get_basic_receiver_info()
        udp_receiver_info =  await onkyo_receiver.get_udp_receiver_info()

        if not receiver_info:
            _LOGGER.error("Error getting receiver information")
        if not basic_receiver_info:
            _LOGGER.error("Error getting basic receiver information")
        if not udp_receiver_info:
            _LOGGER.error("Error getting basic receiver information via UDP")

        _LOGGER.info(receiver_info)
        _LOGGER.info(basic_receiver_info)
        _LOGGER.info(udp_receiver_info)
        if (not receiver_info) or (not udp_receiver_info and not basic_receiver_info):
            _LOGGER.error("Could not retrieve enough receiver information")
            return False

        name = receiver_info.model if receiver_info else udp_receiver_info['model_name']
        serial = receiver_info.serial if receiver_info else udp_receiver_info['identifier']
        productid = receiver_info.productid if receiver_info else "N/A"
        macaddress = receiver_info.macaddress if receiver_info else udp_receiver_info['identifier']
        _LOGGER.debug("Found %s (Serial: %s) (Product ID: %s) (Mac Address: %s)", name, serial, productid, macaddress)
    except (ConnectionError) as error:
        _LOGGER.error("Cannot load data with error: %s", error)
        return False

    # setup a coordinator
    coordinator = OnkyoDataUpdateCoordinator(
        hass, onkyo_receiver, timedelta(seconds=update_interval)
    )

    # refresh coordinator for the first time to load initial data
    await coordinator.async_config_entry_first_refresh()

    # store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # setup sensors
    for p in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, p))
    # hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    hass_data: dict[str, Any] = hass.data[DOMAIN]
    receiver: OnkyoReceiver = hass_data[entry.entry_id].onkyo_receiver

    for p in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, p)

    hass_data.pop(entry.entry_id)
    receiver.disconnect()

    return True


class OnkyoDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Onkyo data from the receiver."""

    def __init__(
        self,
        hass: HomeAssistant,
        onkyo_receiver: OnkyoReceiver,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.onkyo_receiver: OnkyoReceiver = onkyo_receiver
        self.onkyo_receiver.register_listener(self.receive_data)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.onkyo_receiver.update()

    async def receive_data(self, data):
        _LOGGER.debug(f"Data: {data}")
        self.async_set_updated_data(data)

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        data = {}
        try:
            # Ask the library to reload fresh data
            self.onkyo_receiver.update()
            return self.onkyo_receiver.data
        except (ConnectionError) as error:
            raise UpdateFailed(error) from error


class OnkyoReceiverEntity(CoordinatorEntity):
    """Class to set basics for a receiver entity."""

    def __init__(self, coordinator: OnkyoDataUpdateCoordinator) -> None:
        super().__init__(coordinator, )
        self._model_name = coordinator.data[ATTR_NAME]
        self._name = coordinator.data[ATTR_NAME]
        self._identifier = coordinator.data[ATTR_IDENTIFIER]
        self._serial_number = f"{self._model_name}_{self._identifier}"
        self._available = True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._serial_number)},
            "name": self._name,
            "model": self._model_name,
            "manufacturer": "Onkyo",
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available
