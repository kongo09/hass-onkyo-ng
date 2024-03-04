"""Media Player entity for Onkyo receivers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import OnkyoDataUpdateCoordinator, OnkyoReceiverEntity

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

# from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify

import logging

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


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities: Callable
):
    """Setup media player entity."""

    _LOGGER.debug("async_setup_entry called")

    entities = []
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities.append(OnkyoMediaPlayer(coordinator, "main"))
    entities.append(OnkyoMediaPlayer(coordinator, "zone2"))

    async_add_entities(entities, update_before_add=True)
    return True


class OnkyoMediaPlayer(OnkyoReceiverEntity, MediaPlayerEntity):
    """Representation of the media player."""

    def __init__(self, coordinator: OnkyoDataUpdateCoordinator, zone: str) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = self._serial_number + "_" + self._zone
        self._attr_name = self._model_name + "_" + zone
        self.entity_id = "media_player." + slugify("Onkyo" + " " + self._model_name + " " + self._zone)
        self._attr_supported_features = SUPPORT_ONKYO
        self._attr_device_class = "receiver"

        self._onkyo_receiver = coordinator._onkyo_receiver
        self._attr_is_volume_muted = False
        self._attr_volume_level = 0
        self._attr_state = MediaPlayerState.OFF
        #self._attr_unique_id = self._serial_number
        self._max_volume = self._onkyo_receiver._max_volume
        self._receiver_max_volume = self._onkyo_receiver._receiver_max_volume

        # prepare source list
        self._source_mapping = self._onkyo_receiver._source_mapping[zone]
        self._reverse_source_mapping = self._onkyo_receiver._reverse_source_mapping[zone]
        self._attr_source_list = list(self._source_mapping.keys())

        source = coordinator.data.get(self._zone, {}).get(ATTR_SOURCE)
        if source and source in self._reverse_source_mapping:
            self._attr_source = self._reverse_source_mapping[source]

        # prepare sound mode list
        self._sound_mode_mapping = self._onkyo_receiver._sound_mode_mapping
        self._reverse_sound_mode_mapping = (
            self._onkyo_receiver._reverse_sound_mode_mapping
        )
        self._attr_sound_mode_list = list(self._reverse_sound_mode_mapping.keys())

        sound_mode = coordinator.data.get(self._zone, {}).get(ATTR_SOUND_MODE)
        if sound_mode and sound_mode in self._sound_mode_mapping:
            self._attr_sound_mode = self._sound_mode_mapping[sound_mode]

        self._attr_extra_state_attributes = {}
        self._hdmi_out_supported = True
        self._audio_info_supported = True
        self._video_info_supported = True

    @property
    def is_on(self) -> bool:
        """True, if the receiver is on."""
        if ATTR_POWER in self.coordinator.data.get(self._zone, {}):
            return self.coordinator.data[self._zone][ATTR_POWER] == POWER_ON
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
        source = self.coordinator.data[self._zone].get(ATTR_SOURCE, None)
        return source # self._reverse_source_mapping.get(source, None)

    @property
    def sound_mode(self) -> str | None:
        """Return sound mode."""
        sound_mode = self.coordinator.data[self._zone].get(ATTR_SOUND_MODE, None)
        return self._sound_mode_mapping.get(sound_mode, None)

    @property
    def is_volume_muted(self) -> bool | None:
        """True, if volume is muted."""
        return self.coordinator.data[self._zone][ATTR_MUTE]

    @property
    def volume_level(self) -> float | None:
        """Return volume level."""
        return self.coordinator.data[self._zone][ATTR_VOLUME]

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
        data = self.coordinator.data[self._zone]

        if ATTR_PRESET in data:
            extra_state_attributes[ATTR_PRESET] = data[ATTR_PRESET]

        if ATTR_AUDIO_INFO in data:
            extra_state_attributes[ATTR_AUDIO_INFO] = data[ATTR_AUDIO_INFO]

        if ATTR_VIDEO_INFO in data:
            extra_state_attributes[ATTR_VIDEO_INFO] = data[ATTR_VIDEO_INFO]

        if ATTR_HDMI_OUT in data:
            extra_state_attributes[ATTR_HDMI_OUT] = data[ATTR_HDMI_OUT]

        return extra_state_attributes

    def turn_off(self) -> None:
        """Turn the media player off."""
        self._onkyo_receiver.command(self._zone, "power=standby")

    def set_volume_level(self, volume: float) -> None:
        """
        Set volume level, input is range 0..1.
        However full volume on the amp is usually far too loud so allow the user to specify the upper range
        with CONF_MAX_VOLUME.  we change as per max_volume set by user. This means that if max volume is 80 then full
        volume in HA will give 80% volume on the receiver. Then we convert
        that to the correct scale for the receiver.
        """
        #        HA_VOL * (MAX VOL / 100) * MAX_RECEIVER_VOL
        self._onkyo_receiver.command(self._zone,
            f"volume={int(volume * (self._max_volume / 100) * self._receiver_max_volume)}"
        )

    def volume_up(self) -> None:
        """Increase volume by 1 step."""
        self._onkyo_receiver.command(self._zone, "volume=level-up")

    def volume_down(self) -> None:
        """Decrease volume by 1 step."""
        self._onkyo_receiver.command(self._zone, "volume=level-down")

    def mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        if mute:
            self._onkyo_receiver.command(self._zone, "audio-muting=on")
        else:
            self._onkyo_receiver.command(self._zone, "audio-muting=off")

    def turn_on(self) -> None:
        """Turn the media player on."""
        self._onkyo_receiver.command(self._zone, "power=on")

    def select_source(self, source: str) -> None:
        """Set the input source."""
        if self._source_mapping and source in self._source_mapping:
            #source = self._source_mapping[source]
            selector_command = "input-selector" if self._zone == "main" else "selector"
            self._onkyo_receiver.command(self._zone, f"{selector_command}={source}")

    def select_sound_mode(self, sound_mode: str) -> None:
        """Set the sound mode."""
        if (
            self._reverse_sound_mode_mapping
            and sound_mode in self._reverse_sound_mode_mapping
        ):
            sound_mode = self._reverse_sound_mode_mapping[sound_mode]
            self._onkyo_receiver.raw(self._zone, f"LMD{sound_mode}")

    def play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play radio station by preset number."""
        source = self._reverse_source_mapping[self._attr_source]
        if media_type.lower() == "radio" and source in DEFAULT_PLAYABLE_SOURCES:
            self._onkyo_receiver.command(self._zone, f"preset={media_id}")

    def select_output(self, output):
        """Set hdmi-out."""
        self._onkyo_receiver.command(self._zone, f"hdmi-output-selector={output}")
