"""Media Player entity for Onkyo receivers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import voluptuous as vol
from . import OnkyoDataUpdateCoordinator, OnkyoReceiverEntity
from homeassistant.core import SupportsResponse
from homeassistant.helpers import entity_platform, config_validation as cv
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify
from .onkyo import OnkyoReceiver

import logging
import asyncio

from .const import *

_LOGGER = logging.getLogger(__name__)


SUPPORT_ONKYO_WO_VOLUME = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
)

SUPPORT_ONKYO = (
    SUPPORT_ONKYO_WO_VOLUME
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_STEP
)

DEFAULT_PLAYABLE_SOURCES = ("fm", "am", "tuner")


def add_services():
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "onkyo_send_command",
        {
            vol.Required('command'): cv.string
        },
        OnkyoMediaPlayer.send_command.__name__,
        supports_response=SupportsResponse.ONLY
    )
    platform.async_register_entity_service(
        "onkyo_send_raw_command",
        {
            vol.Required('command'): cv.string
        },
        OnkyoMediaPlayer.send_raw_command.__name__,
        supports_response=SupportsResponse.ONLY
    )

async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities: Callable
):
    """Setup media player entity."""
    _LOGGER.debug("async_setup_entry called")
    add_services()

    entities = []

    coordinator = hass.data[DOMAIN][entry.entry_id]
    receiver: OnkyoReceiver = coordinator.onkyo_receiver

    receiver_info = await receiver.get_receiver_info()
    if not receiver_info:
        _LOGGER.error("Could not retrieve receiver info")
        return False

    _LOGGER.info(f"Creating mediaplayer entities for zones: {receiver_info.zones}")

    # Create a media player entity for each supported zone
    for zone in receiver_info.zones:
        _LOGGER.info(f"Set up Onkyo zone: {zone.name}")
        entities.append(OnkyoMediaPlayer(coordinator, zone))

    async_add_entities(entities, update_before_add=True)
    return True


class OnkyoMediaPlayer(OnkyoReceiverEntity, MediaPlayerEntity):
    """Representation of the media player."""

    @property
    def zone_data(self):
        return self.coordinator.data.get(f"{ATTR_ZONE}_{self._zone_name}", {})

    def __init__(self, coordinator: OnkyoDataUpdateCoordinator, zone: OnkyoReceiver.ReceiverZone) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._zone_name = zone.name
        self._zone_key = f"{ATTR_ZONE}_{zone.name}"
        self._attr_name = self._model_name
        if zone != "main":
            self._attr_name += "_" + zone.name
        self.entity_id = "media_player." + slugify("Onkyo" + " " + self._model_name + " " + zone.name)
        self._attr_supported_features = SUPPORT_ONKYO
        self._attr_device_class = "receiver"

        self._onkyo_receiver = coordinator.onkyo_receiver
        self._attr_is_volume_muted = False
        self._attr_volume_level = 0
        self._attr_state = MediaPlayerState.OFF
        self._attr_unique_id = self._serial_number + "_" + zone.name
        self._max_volume = self._onkyo_receiver._max_volume
        self._receiver_max_volume = self._onkyo_receiver._receiver_max_volume
        self._attr_source_list = [source.name for source in zone.sources]

        self._attr_extra_state_attributes = {}
        self._hdmi_out_supported = True
        self._audio_info_supported = True
        self._video_info_supported = True

    @property
    def is_on(self) -> bool:
        """True, if the receiver is on."""
        if ATTR_POWER in self.zone_data:
            return self.coordinator.data[self._zone_key][ATTR_POWER] == POWER_ON
        else:
            return False

    @property
    def state(self) -> str:
        """Return media player state."""
        if self.is_on:
            return MediaPlayerState.ON
        else:
            return MediaPlayerState.OFF

    @property
    def source(self) -> str | None:
        """Return readable source."""
        source_id = self.zone_data[ATTR_SOURCE]
        for source in self._zone.sources:
            if source.id == source_id:
                return source.name
        return None

    @property
    def sound_mode_list(self) -> list[str] | None:
        """List of available sound modes"""
        return self.zone_data[ATTR_SOUND_MODES]

    @property
    def sound_mode(self) -> str | None:
        """Return sound mode."""
        sound_mode = self.zone_data[ATTR_SOUND_MODE]
        return sound_mode

    @property
    def is_volume_muted(self) -> bool | None:
        """True, if volume is muted."""
        return self.zone_data[ATTR_MUTE]

    @property
    def volume_level(self) -> float | None:
        """Return volume level."""
        return self.zone_data[ATTR_VOLUME]

    @property
    def icon(self) -> str:
        """Return icon depending on state."""
        if self.is_on:
            return "mdi:audio-video"
        else:
            return "mdi:audio-video-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        extra_state_attributes = {}
        data = self.coordinator.data[self._zone_key]

        if ATTR_PRESET in data:
            extra_state_attributes[ATTR_PRESET] = data[ATTR_PRESET]

        if ATTR_AUDIO_INFO in data:
            extra_state_attributes[ATTR_AUDIO_INFO] = data[ATTR_AUDIO_INFO]

        if ATTR_VIDEO_INFO in data:
            extra_state_attributes[ATTR_VIDEO_INFO] = data[ATTR_VIDEO_INFO]

        if ATTR_HDMI_OUT in data:
            extra_state_attributes[ATTR_HDMI_OUT] = data[ATTR_HDMI_OUT]

        if ATTR_DISPLAY in data:
            extra_state_attributes[ATTR_DISPLAY] = data[ATTR_DISPLAY]

        return extra_state_attributes

    def turn_off(self) -> None:
        """Turn the media player off."""
        self._onkyo_receiver.command(f"{self._zone_name}.power=standby")

    def set_volume_level(self, volume: float) -> None:
        """
        Set volume level, input is range 0..1.
        However full volume on the amp is usually far too loud so allow the user to specify the upper range
        with CONF_MAX_VOLUME.  we change as per max_volume set by user. This means that if max volume is 80 then full
        volume in HA will give 80% volume on the receiver. Then we convert
        that to the correct scale for the receiver.
        """
        #        HA_VOL * (MAX VOL / 100) * MAX_RECEIVER_VOL
        self._onkyo_receiver.command(
            f"{self._zone_name}.volume={int(volume * (self._max_volume / 100) * self._receiver_max_volume)}"
        )

    def volume_up(self) -> None:
        """Increase volume by 1 step."""
        self._onkyo_receiver.command(f"{self._zone_name}.volume=level-up")

    def volume_down(self) -> None:
        """Decrease volume by 1 step."""
        self._onkyo_receiver.command(f"{self._zone_name}.volume=level-down")

    def mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        cmd = "audio-muting" if self._zone_name == "main" else "muting"
        if mute:
            self._onkyo_receiver.command(f"{self._zone_name}.{cmd}=on")
        else:
            self._onkyo_receiver.command(f"{self._zone_name}.{cmd}=off")

    def turn_on(self) -> None:
        """Turn the media player on."""
        self._onkyo_receiver.command(f"{self._zone_name}.power=on")

    def select_source(self, source: str) -> None:
        """Set the input source."""
        try:
            source = next(filter(lambda s: s.name.lower() == source.lower(), self._zone.sources))
            self._onkyo_receiver.select_source(self._zone, source.id)
        except StopIteration:
            _LOGGER.error(f"Cannot find source {source}")
            raise Exception(f"Cannot find source {source}")

    def select_sound_mode(self, sound_mode: str) -> None:
        """Set the sound mode."""
        self._onkyo_receiver.select_sound_mode(self._zone, sound_mode)

    def play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play radio station by preset number."""
        source = self._attr_source
        if media_type.lower() == "radio" and source.lower() in DEFAULT_PLAYABLE_SOURCES:
            self._onkyo_receiver.command(f"{self._zone_name}.preset={media_id}")

    def select_output(self, output):
        """Set hdmi-out."""
        self._onkyo_receiver.command(f"{self._zone_name}.hdmi-output-selector={output}")

    async def send_command(self, command):
        result = await asyncio.wait_for(self._onkyo_receiver.command_async(command), 5.0)
        return {
            'result': result
        }

    async def send_raw_command(self, command):
        result = await asyncio.wait_for(self._onkyo_receiver.raw_async(command), 5.0)
        return {
            'result': result
        }
