"""The Onkyo AV receiver component."""
from __future__ import annotations
from datetime import timedelta

import eiscp

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
    receiver = eiscp.eISCP(host)
    try:
        name = receiver.info["model_name"]
        _LOGGER.debug("Found %s", name)
    except (ConnectionError) as error:
        _LOGGER.error("Cannot load data with error: %s", error)
        return False

    # check for sources and sound modes
    sources = entry.data.get(CONF_SOURCES)
    sound_modes = entry.data.get(CONF_SOUND_MODES)

    onkyo_receiver = OnkyoReceiver(
        receiver,
        sources=sources,
        sound_modes=sound_modes,
        max_volume=ONKYO_SUPPORTED_MAX_VOLUME,
        receiver_max_volume=ONKYO_DEFAULT_RECEIVER_MAX_VOLUME,
    )

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

    for p in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, p)

    hass.data[DOMAIN].pop(entry.entry_id)

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
        self._onkyo_receiver = onkyo_receiver
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        data = {}
        try:
            # Ask the library to reload fresh data
            data = await self._onkyo_receiver.update()
        except (ConnectionError) as error:
            raise UpdateFailed(error) from error
        return data


class OnkyoReceiverEntity(CoordinatorEntity):
    """Class to set basics for a receiver entity."""

    def __init__(self, coordinator: OnkyoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
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
