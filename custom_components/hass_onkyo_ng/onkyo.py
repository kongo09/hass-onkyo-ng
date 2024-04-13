from __future__ import annotations

import asyncio
from collections import defaultdict
from eiscp.core import Receiver, command_to_iscp, iscp_to_command
from eiscp.commands import COMMANDS, COMMAND_MAPPINGS
from .const import *
from .util import dict_merge
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
import threading
import logging
from typing import Any, List
import xml.etree.ElementTree as ET
import re

_LOGGER = logging.getLogger(__name__)
_ZONE_NAMES = ("main", "zone2", "zone3", "zone4")

class OnkyoReceiver:
    """Class to manage fetching Onkyo data from the receiver."""

    class ReceiverZone:
        def __init__(self):
            self.id: int | None = None
            self.name: str | None = None
            self.volmax: int | None = None
            self.sources: List[OnkyoReceiver.ReceiverSource] = []

        def __repr__(self):
            return f"ReceiverZone(id: {self.id}, name: {self.name})"

    class ReceiverSource:
        def __init__(self):
            self.id: int | None = None
            self.name: str | None = None
            self.zones: List[OnkyoReceiver.ReceiverZone] = []

        def __repr__(self):
            return f"ReceiverSource(id: {self.id:02x}, name: {self.name})"

    class ReceiverInfo:
        def __init__(self, model: str, serial: str, productid: str, macaddress: str, zones: List[OnkyoReceiver.ReceiverZone], sources: List[OnkyoReceiver.ReceiverSource]):
            self.model = model
            self.serial = serial
            self.productid = productid
            self.macaddress = macaddress
            self.zones = zones
            self.sources = sources

        def __repr__(self):
            return f"ReceiverInfo(model: {self.model}, serial: {self.serial}, productid: {self.productid}, macaddress: {self.macaddress}, zones: {self.zones}, sources: {self.sources})"

        @staticmethod
        def from_xml(receiver_information_xml: str):
            data = ET.fromstring(receiver_information_xml)
            device = data.find('device')
            model = device.find('model').text
            serial = device.find('deviceserial').text
            productid = device.find('productid').text
            macaddress = device.find('macaddress').text

            zone_map = {}
            zones = []
            for zone in device.find('zonelist').findall('zone'):
                if int(zone.attrib['value']) > 0:
                    receiver_zone = OnkyoReceiver.ReceiverZone()
                    receiver_zone.id = int(zone.attrib['id'], 16)
                    receiver_zone.name = zone.attrib['name'].lower()
                    receiver_zone.volmax = int(zone.attrib['volmax'])

                    zone_map[receiver_zone.id] = receiver_zone
                    zones.append(receiver_zone)

            sources = []
            for source in device.find('selectorlist').findall('selector'):
                if int(source.attrib['value']) > 0:
                    receiver_source = OnkyoReceiver.ReceiverSource()
                    receiver_source.id = int(source.attrib['id'], 16)
                    receiver_source.name = source.attrib['name']

                    # Assume this is a bitwise identifier for which zones support this source
                    source_zones = int(source.attrib['zone'], 16)
                    for zone_id in zone_map.keys():
                        if source_zones & (1 << (zone_id - 1)):
                            receiver_source.zones.append(zone_map[zone_id])
                            zone_map[zone_id].sources.append(receiver_source)
                    sources.append(receiver_source)
            return OnkyoReceiver.ReceiverInfo(model, serial, productid, macaddress, zones, sources)

        @staticmethod
        def default(model: str, serial: str):
            source_selector_cmd = {'main': 'SLI', 'zone2': 'SLZ', 'zone3': 'SL3', 'zone4': 'SL4'}
            source_mapping = {}
            zones = []
            for zone_id in range(1, 5):
                receiver_zone = OnkyoReceiver.ReceiverZone()
                receiver_zone.id = zone_id
                receiver_zone.name = "main" if receiver_zone.id == 1 else "zone" + str(receiver_zone.id)
                zones.append(receiver_zone)

                # For now, provide a list of all zones available in the commands
                source_command_args = COMMANDS[receiver_zone.name][source_selector_cmd[receiver_zone.name]]['values']
                for source_id in source_command_args:
                    if source_id not in ('UP', 'DOWN', 'QSTN'):
                        name = source_command_args[source_id]['name']
                        if not isinstance(name, str):
                            name = "/".join(name)
                        name = name.upper()
                        if not source_id in source_mapping:
                            receiver_source = OnkyoReceiver.ReceiverSource()
                            receiver_source.id = int(source_id, 16)
                            receiver_source.name = name
                            source_mapping[source_id] = receiver_source
                        receiver_source = source_mapping[source_id]
                        receiver_source.zones.append(receiver_zone)
                        receiver_zone.sources.append(receiver_source)

            return OnkyoReceiver.ReceiverInfo(model, serial, 'N/A', serial, zones, source_mapping.values())


    def __init__(
        self,
        host: str,
        hass: HomeAssistant | None,
        max_volume=ONKYO_SUPPORTED_MAX_VOLUME,
        receiver_max_volume=ONKYO_DEFAULT_RECEIVER_MAX_VOLUME,
    ) -> None:
        """Initialize."""
        self._host = host
        self._receiver = Receiver(host)
        self._receiver.on_message = lambda msg: self._on_message_async(msg)
        self._sound_modes = {}
        self._retrieved_receiver_info: bool = False
        self._receiver_info: OnkyoReceiver.ReceiverInfo | None = None
        self._receiver_udp_info = None
        self._max_volume = max_volume
        self._receiver_max_volume = receiver_max_volume
        self._hdmi_out_supported = True
        self._audio_info_supported = True
        self._video_info_supported = True
        self.listeners = []
        self._sync_commands = defaultdict(OnkyoReceiver.SyncCommand)
        self._hass = hass
        if hass:
            self._storage = Store[dict[str, Any]](hass, 1, f'onkyo_{host}')
        else:
            self._storage = None

        self.data = {
            ATTR_PRESET: None,
            ATTR_HDMI_OUT: None,
            ATTR_RECEIVER_INFORMATION: {},
        }
        for zone in _ZONE_NAMES:
            key = f"{ATTR_ZONE}_{zone}"
            self.data[key] = {
                ATTR_POWER: None,
                ATTR_AUDIO_INFO: None,
                ATTR_VIDEO_INFO: None,
                ATTR_MUTE: None,
                ATTR_VOLUME: None,
                ATTR_SOURCE: None,
                ATTR_SOUND_MODE: None,
                ATTR_SOUND_MODES: [],
            }

    async def get_all_receiver_info(self) -> None:
        if not self._retrieved_receiver_info:
            self._retrieved_receiver_info = True
            # TODO: Retry only the failed ones
            retries = 3
            while retries > 0:
                tasks = []
                tasks.append(asyncio.create_task(self.command_async('dock.receiver-information=query')))
                tasks.append(asyncio.create_task(self.command_udp_info()))
                done, pending = await asyncio.wait(tasks, timeout=2)
                for coroutine in pending:
                    _LOGGER.error("Timeout waiting for receiver information")
                    coroutine.cancel()
                if len(pending) == 0:
                    break
                retries -= 1
            if not self._receiver_info and self._receiver_udp_info:
                udp_info = self._receiver_udp_info
                self._receiver_info = OnkyoReceiver.ReceiverInfo.default(udp_info['model_name'], udp_info['identifier'])

    async def get_receiver_info(self) -> OnkyoReceiver.ReceiverInfo:
        await self.get_all_receiver_info()
        return self._receiver_info

    async def get_udp_receiver_info(self):
        await self.get_all_receiver_info()
        return self._receiver_udp_info

    async def get_zones(self) -> List[OnkyoReceiver.ReceiverZone]:
        await self.get_all_receiver_info()
        return self._receiver_info.zones

    async def sources(self) -> List[OnkyoReceiver.ReceiverSource]:
        await self.get_all_receiver_info()
        return self._receiver_info.sources

    async def load_data(self):
        if self._storage:
            data = await self._storage.async_load()
            _LOGGER.info(f"Loaded data {data}")
            if data:
                self._sound_modes = data.get('sound_modes', {})
                for zone in _ZONE_NAMES:
                    zone_key = f"{ATTR_ZONE}_{zone}"
                    self.data[zone_key][ATTR_SOUND_MODES] = self._sound_modes.get(zone_key, [])

                for listener in self.listeners:
                    listener(self.data)

    def store_data(self):
        if self._storage:
            self._storage.async_delay_save(self._data_to_save, 1)

    def _data_to_save(self):
        data = {
            'sound_modes': self._sound_modes
        }
        return data

    def disconnect(self):
        _LOGGER.info("Disconnect from receiver")
        self._receiver.disconnect()

    def register_listener(self, listener):
        self.listeners.append(listener)

    def _on_message_async(self, message):
        """Received a message from the receiver"""
        updates = defaultdict(dict)
        try:
            message_decoded = iscp_to_command(message, with_zone=True)
            _LOGGER.debug(f"Received command: {message_decoded}")
            zone, command, attrib = message_decoded
            if zone in _ZONE_NAMES:
                zone_key = f"{ATTR_ZONE}_{zone}"
                if command in ["system-power", "power"]:
                    updates[zone_key][ATTR_POWER] = POWER_ON if attrib == "on" else POWER_OFF
                elif command == "audio-information":
                    info = self._parse_audio_information((command, attrib))
                    updates[zone_key][ATTR_AUDIO_INFO] = info
                elif command == "video-information":
                    info = self._parse_video_information((command, attrib))
                    updates[zone_key][ATTR_VIDEO_INFO] = info
                elif command in ["audio-muting", "muting"]:
                    updates[zone_key][ATTR_MUTE] = attrib == "on"
                elif command in ("master-volume", "volume"):
                    if attrib == 'N/A':
                        updates[zone_key][ATTR_VOLUME] = 0.0
                    else:
                        updates[zone_key][ATTR_VOLUME] = attrib / (self._receiver_max_volume * self._max_volume / 100)
                elif command in ["input-selector", "selector"]:
                    source_id = int(message[-2:], 16)
                    updates[zone_key][ATTR_SOURCE] = source_id
                elif command == "preset":
                    updates[zone_key][ATTR_PRESET] = attrib
                elif command == "hdmi-output-selector":
                    updates[zone_key][ATTR_HDMI_OUT] = ",".join(attrib)
                    if attrib == "N/A":
                        self._hdmi_out_supported = False
                elif command == "listening-mode":
                    sound_modes = self._parse_onkyo_payload((command, attrib))
                    sound_mode = "_".join(sound_modes)
                    if not zone_key in self._sound_modes:
                        self._sound_modes[zone_key] = []
                    if not sound_mode in self._sound_modes[zone_key]:
                        self._sound_modes[zone_key].append(sound_mode)
                        updates[zone_key][ATTR_SOUND_MODES] = self._sound_modes[zone_key]
                        self.store_data()
                    updates[zone_key][ATTR_SOUND_MODE] = sound_mode
                elif command == 'fl-display-information':
                    data = b''
                    for c in re.findall('..', message[3:]):
                        data += int(c, 16).to_bytes(1)
                    updates[zone_key][ATTR_DISPLAY] = data.decode('utf-8')
            elif zone == 'dock':
                if command == "receiver-information":
                    _LOGGER.debug("Got receiver info. Parsing")
                    info = OnkyoReceiver.ReceiverInfo.from_xml(attrib)
                    self._receiver_info = info
                    updates[ATTR_RECEIVER_INFORMATION] = info
                    updates[ATTR_NAME] = info.model
                    updates[ATTR_IDENTIFIER] = info.serial
                    self.store_data()
            else:
                _LOGGER.warning(f"Ignoring zone {zone}")
        except ValueError:
            _LOGGER.debug(f"Cannot decode raw message: {message}")

        if updates:
            dict_merge(self.data, updates)
            if self._hass:
                _LOGGER.debug(f"Dispatch data to {len(self.listeners)} listeners")
                for listener in self.listeners:
                    asyncio.run_coroutine_threadsafe(listener(self.data), self._hass.loop)
            else:
                _LOGGER.warning("Update lost (no event loop)")

        message_prefix = message[:3]
        if message_prefix in self._sync_commands:
            _LOGGER.debug(f"Received {message} whilst waiting for sync response")
            sync_command = self._sync_commands.pop(message_prefix)
            sync_command._set_result(message)

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

    def raw(self, command):
        """Send a raw command."""
        _LOGGER.debug(f"Sending raw command: {command}")
        self._receiver._ensure_socket_connected()
        self._receiver.send(command)

    def command(self, command):
        """Send an eiscp command."""
        _LOGGER.debug(f"Sending command: {command}")
        self._receiver._ensure_socket_connected()
        self._receiver.send(command_to_iscp(command))

    async def raw_async(self, raw_command: str):
        """Run a raw eiscp command synchronously."""
        _LOGGER.debug(f"Sending sync command {raw_command}")
        sync_command_prefix = raw_command[:3]
        sync_command = self._sync_commands[sync_command_prefix]
        event = Event_ts()
        sync_command.add_event(event)
        self._receiver.send(raw_command)
        await event.wait()
        result_raw = sync_command.result
        _LOGGER.debug(f"Result: {result_raw}")
        return result_raw

    async def command_async(self, command: str, timeout=None):
        """Run command and wait for response"""
        _LOGGER.debug(f"Sending sync command {command}")
        raw_command = command_to_iscp(command)
        result_raw = await asyncio.wait_for(self.raw_async(raw_command), timeout)
        result = iscp_to_command(result_raw)
        _LOGGER.debug(f"Result: {result}")
        return result

    async def command_udp_info(self):
        retries = 5
        while not self._receiver_udp_info and retries > 0:
            retries -= 1
            # This only waits 0.1 seconds and may miss the response, so retry a few times
            self._receiver_udp_info = self._receiver.info
            if self._receiver_udp_info:
                self.data[ATTR_NAME] = self._receiver_udp_info['model_name']
        return self._receiver_udp_info

    def select_source(self, zone: ReceiverZone, source_id: int):
        cmd = "input-selector" if zone.name == "main" else "selector"
        raw_cmd = COMMAND_MAPPINGS[zone.name][cmd] + f"{source_id:02x}"
        self.raw(raw_cmd)

    def select_sound_mode(self, zone: ReceiverZone, sound_mode: str):
        sound_mode_selection = sound_mode.split("_")[0]
        self.command(f"{zone.name}.listening-mode={sound_mode_selection}")

    def update(self):
        """Get the latest state from the device."""

        if not self._receiver_info:
            self.command("dock.receiver-information=query")

        for zone in _ZONE_NAMES:
            # retrieve power information
            self.command(f"{zone}.power=query")
            # retrieve volume information
            self.command(f"{zone}.volume=query")

            if zone == "main":
                # retrieve audio information
                self.command("main.audio-information=query")
                # retrieve video information
                self.command("main.video-information=query")
                # retrieve sound mode information
                self.command("main.listening-mode=query")
                # retrieve preset information
                self.command("main.preset=query")
                # If the following command is sent to a device with only one HDMI out,
                # the display shows 'Not Available'.
                # We avoid this by checking if HDMI out is supported
                if self._hdmi_out_supported:
                    self.command("main.hdmi-output-selector=query")
                # retrieve mute information
                self.command("main.audio-muting=query")
                # retrieve source information
                self.command(f"{zone}.input-selector=query")

            else:
                # retrieve mute information
                self.command(f"{zone}.muting=query")
                # retrieve source information
                self.command(f"{zone}.selector=query")

    class SyncCommand:
        def __init__(self):
            self._event_list: List[threading.Event | Event_ts] = []
            self._result: str | None = None

        def add_event(self, event: threading.Event | Event_ts) -> None:
            self._event_list.append(event)

        def _set_result(self, result: str) -> None:
            self._result = result
            for event in self._event_list:
                event.set()

        @property
        def result(self) -> str:
            return self._result

class Event_ts(asyncio.Event):
    def set(self):
        self._loop.call_soon_threadsafe(super().set)
