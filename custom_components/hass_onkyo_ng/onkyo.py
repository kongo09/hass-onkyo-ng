from __future__ import annotations
from eiscp import eISCP
from .const import *
from collections import defaultdict

import logging

_LOGGER = logging.getLogger(__name__)


class OnkyoReceiver:
    """Class to manage fetching Onkyo data from the receiver."""

    def __init__(
        self,
        receiver: eISCP,
        sources: dict = None,
        sound_modes: dict = None,
        zones: int = 1,
        max_volume=ONKYO_SUPPORTED_MAX_VOLUME,
        receiver_max_volume=ONKYO_DEFAULT_RECEIVER_MAX_VOLUME,

    ) -> None:
        """Initialize."""
        self._receiver = receiver
        self._zones = zones
        self._source_mapping = sources
        self._reverse_source_mapping = defaultdict(dict)
        self._sound_mode_mapping = sound_modes
        self._reverse_sound_mode_mapping = {}
        self._max_volume = max_volume
        self._receiver_max_volume = receiver_max_volume
        self._hdmi_out_supported = True
        self._audio_info_supported = True
        self._video_info_supported = True

        # if source mapping has not been defined as part of config, try to get it from the device and use the first source
        if not self._source_mapping:
            self._source_mapping = defaultdict(dict)
            for zone in ["main", "zone2"]:
                sources = {}
                source_list = self.get_sources(zone)
                for item in source_list:
                    first = item.split("_")[0]
                    sources[first] = item
                self._source_mapping[zone] = sources

        # prepare reverse source mapping
        for zone in ["main", "zone2"]:
            for key, value in self._source_mapping[zone].items():
                self._reverse_source_mapping[zone][value] = key

        # try to get the sound modes from the device
        if not self._sound_mode_mapping:
            sound_modes = {}
            sound_mode_list = self.get_sound_modes()
            for item in sound_mode_list:
                if item in LISTENING_MODE:
                    sound_modes[item] = LISTENING_MODE[item]
            self._sound_mode_mapping = sound_modes

        # prepare reverse sound mode mapping
        for key, value in self._sound_mode_mapping.items():
            self._reverse_sound_mode_mapping[value] = key

    def _parse_onkyo_payload(self, payload):
        """Parse a payload returned from the eiscp library."""
        if isinstance(payload, bool):
            # command not supported by the device
            return False

        if len(payload) < 2:
            # no value
            return None

        if isinstance(payload[1], str):
            return payload[1].split(",")

        return payload[1]

    def _tuple_get(self, tup, index, default=None):
        """Return a tuple item at index or a default value if it doesn't exist."""
        return (tup[index : index + 1] or [default])[0]

    def get_sources(self, zone="main") -> list:
        """Iterate through the sources of the receiver."""

        # find the power state and switch on if needed
        status = self.command(zone, "power=query")
        _LOGGER.debug(f"Status: {status}")
        if not status:
            _LOGGER.error("Failed to get power status")
            return []
        power_state = status[1]
        if power_state != "on":
            self.command(zone, "power=on")

        muting_command = "audio-muting" if zone == "main" else "muting"

        # check if muted, if not, mute to avoid funny sound
        status = self.command(zone, f"{muting_command}=query")
        muting_state = status[1]
        if muting_state != "on":
            self.command(zone, f"{muting_command}=on")

        # iterate over all available source until we hit the first source again to compile the list
        first_source = None
        source_list = []

        selector_command = "input-selector" if zone == "main" else "selector"
        while True:
            current_source_raw = self.command(zone, f"{selector_command}=up")
            current_source = ""
            if current_source_raw:
                sources = self._parse_onkyo_payload(current_source_raw)
                current_source = "_".join(sources)

            # if we find the first source again, we're done
            if current_source == first_source:
                break

            # remember the first source
            if not first_source:
                first_source = current_source

            # store the found source in the list
            source_list.append(current_source)

        # get receiver back into original state
        self.command(zone, f"{selector_command}=down")

        self.command(zone, f"{muting_command}={muting_state}")
        if power_state != "on":
            self.command(zone, "power=off")
        _LOGGER.debug(f"Sources for {zone}: {source_list}")
        return source_list

    def get_sound_modes(self, zone="main") -> list:
        """Iterate through the sound modes of the receiver."""

        # find the power state and switch on if needed
        status = self.command(zone, "power=query")
        power_state = status[1]
        if power_state != "on":
            self.command(zone, "power=on")

        # check if muted, if not, mute to avoid funny sound
        status = self.command(zone, "audio-muting=query")
        muting_state = status[1]
        if muting_state != "on":
            self.command(zone, "audio-muting=on")

        # iterate over all available sound modes until we hit the first sound mode again to compile the list
        first_sound_mode = None
        sound_mode_list = []
        count = 0

        while True:
            current_sound_mode_raw = self.raw(zone, "LMDUP")
            current_sound_mode = ""
            if current_sound_mode_raw:
                current_sound_mode = current_sound_mode_raw[3:]
                count += 1

            # if we find the first sound mode again, we're done
            if current_sound_mode == first_sound_mode and count > 5:
                break

            # remember the first source
            if not first_sound_mode:
                first_sound_mode = current_sound_mode

            # store the found source in the list
            sound_mode_list.append(current_sound_mode)

        # get receiver back into original state
        self.raw(zone, f"LMD{first_sound_mode}")
        self.command(zone, f"audio-muting={muting_state}")
        if power_state != "on":
            self.command(zone, "power=off")

        return sound_mode_list

    def _parse_audio_information(self, audio_information_raw):
        values = self._parse_onkyo_payload(audio_information_raw)
        if values is False or values is None:
            self._audio_info_supported = False
            return None

        info = {
            "format": self._tuple_get(values, 1),
            "input_frequency": self._tuple_get(values, 2),
            "input_channels": self._tuple_get(values, 3),
            "listening_mode": self._tuple_get(values, 4),
            "output_channels": self._tuple_get(values, 5),
            "output_frequency": self._tuple_get(values, 6),
        }
        return info

    def _parse_video_information(self, video_information_raw):
        values = self._parse_onkyo_payload(video_information_raw)
        if values is False or values is None:
            self._video_info_supported = False
            return None

        info = {
            "input_resolution": self._tuple_get(values, 1),
            "input_color_schema": self._tuple_get(values, 2),
            "input_color_depth": self._tuple_get(values, 3),
            "output_resolution": self._tuple_get(values, 5),
            "output_color_schema": self._tuple_get(values, 6),
            "output_color_depth": self._tuple_get(values, 7),
            "picture_mode": self._tuple_get(values, 8),
        }
        return info

    def raw(self, zone, command):
        """Run a raw eiscp command and catch connection errors."""
        retries = 5
        while retries > 0:
            try:
                result = self._receiver.raw(command)
                break
            except (ValueError, OSError, AttributeError, AssertionError):
                _LOGGER.info("Resetting connection")
                self._receiver.disconnect()
                retries -= 1
        if retries == 0:
            return False
        _LOGGER.debug("Result for %s: %s", command, result)
        return result

    def command(self, zone, command):
        """Run an eiscp command and catch connection errors."""
        retries = 5
        while retries > 0:
            try:
                _LOGGER.info(f"Command: {command}, zone: {zone}")
                result = self._receiver.command(f"{zone}.{command}")
                break
            except (ValueError, OSError, AttributeError, AssertionError):
                _LOGGER.info("Resetting connection")
                self._receiver.disconnect()
                retries -= 1
        if retries == 0:
            return False
        _LOGGER.info("Result for %s: %s", command, result)
        return result

    async def update(self) -> dict:
        """Get the latest state from the device."""
        data = defaultdict(dict)

        # some basic info
        data[ATTR_NAME] = self._receiver.info["model_name"]
        data[ATTR_IDENTIFIER] = self._receiver.info["identifier"]

        for zone in ["main", "zone2"]:
            zone_data = data[zone]
            # retrieve power information
            status = self.command(zone, "power=query")

            if not status:
                continue

            if status[1] == "on":
                zone_data[ATTR_POWER] = POWER_ON
            else:
                zone_data[ATTR_POWER] = POWER_OFF
                continue
            _LOGGER.info(f"{zone} zone_data[ATTR_POWER]={zone_data[ATTR_POWER]}")

            # retrieve audio information
            if self._audio_info_supported:
                audio_information_raw = self.command(zone, "audio-information=query")
                info = self._parse_audio_information(audio_information_raw)
                if info:
                    zone_data[ATTR_AUDIO_INFO] = info
                else:
                    zone_data[ATTR_AUDIO_INFO] = None

            # retrieve video information
            if self._video_info_supported:
                video_information_raw = self.command(zone, "video-information=query")
                info = self._parse_video_information(video_information_raw)
                if info:
                    zone_data[ATTR_VIDEO_INFO] = info
                else:
                    zone_data[ATTR_VIDEO_INFO] = None

            # retrieve mute information
            mute_raw = self.command(zone, "audio-muting=query")
            if mute_raw:
                zone_data[ATTR_MUTE] = bool(mute_raw[1] == "on")
            else:
                zone_data[ATTR_MUTE] = None

            # retrieve volume information
            volume_raw = self.command(zone, "volume=query")
            if volume_raw:
                # AMP_VOL/MAX_RECEIVER_VOL*(MAX_VOL/100)
                zone_data[ATTR_VOLUME] = volume_raw[1] / (
                    self._receiver_max_volume * self._max_volume / 100
                )
            else:
                zone_data[ATTR_VOLUME] = None

            # retrieve source information
            selector_command = "input-selector" if zone == "main" else "selector"
            current_source_raw = self.command(zone, f"{selector_command}=query")
            _LOGGER.info(f"current_source_raw={current_source_raw}")
            if current_source_raw:
                sources = self._parse_onkyo_payload(current_source_raw)
                source = "_".join(sources)
                zone_data[ATTR_SOURCE] = sources[0]
            else:
                zone_data[ATTR_SOURCE] = None
            _LOGGER.info(f"zone_data[ATTR_SOURCE]={zone_data[ATTR_SOURCE]}")

            # retrieve sound mode information
            current_sound_mode_raw = self.raw(zone, "LMDQSTN")
            if current_sound_mode_raw:
                current_sound_mode = current_sound_mode_raw[3:]
                zone_data[ATTR_SOUND_MODE] = current_sound_mode
            else:
                zone_data[ATTR_SOUND_MODE] = None

            # retrieve preset information
            preset_raw = self.command(zone, "preset=query")
            if preset_raw:
                zone_data[ATTR_PRESET] = preset_raw[1]
            else:
                zone_data[ATTR_PRESET] = None

            # If the following command is sent to a device with only one HDMI out,
            # the display shows 'Not Available'.
            # We avoid this by checking if HDMI out is supported
            if zone == "main":
                zone_data[ATTR_HDMI_OUT] = None
                if self._hdmi_out_supported:
                    hdmi_out_raw = self.command(zone, "hdmi-output-selector=query")
                    if hdmi_out_raw:
                        zone_data[ATTR_HDMI_OUT] = ",".join(hdmi_out_raw[1])
                        if hdmi_out_raw[1] == "N/A":
                            self._hdmi_out_supported = False

        return data
