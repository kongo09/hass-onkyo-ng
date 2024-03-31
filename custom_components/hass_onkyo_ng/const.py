"""Constants for Onkyo NG integration."""
from __future__ import annotations

DOMAIN = "hass_onkyo_ng"
PLATFORMS = ["media_player"]

POLLING_INTERVAL = 30

ATTR_ZONE = "zone"

POWER_ON = "power_on"
POWER_OFF = "power_off"

ATTR_POWER = "power"
ATTR_SOURCE = "source"
ATTR_SOURCES = "source_list"
ATTR_SOUND_MODE = "sound_mode"
ATTR_SOUND_MODES = "sound_mode_list"
ATTR_AUDIO_INFO = "audio_info"
ATTR_VIDEO_INFO = "video_info"
ATTR_HDMI_OUT = "hdmi_out"
ATTR_MUTE = "mute"
ATTR_VOLUME = "volume"
ATTR_PRESET = "preset"
ATTR_NAME = "name"
ATTR_IDENTIFIER = "identifier"
ATTR_RECEIVER_INFORMATION = "receiver_information"
ATTR_DISPLAY = "display"

DEFAULT_NAME = "Onkyo Receiver"
ONKYO_SUPPORTED_MAX_VOLUME = 100
ONKYO_DEFAULT_RECEIVER_MAX_VOLUME = 80

INFO_IDENTIFIER = "identifier"
INFO_MODEL_NAME = "model_name"
INFO_HOST = "host"
INFO_PORT = "port"

LISTENING_MODE = {
    "00": "STEREO",
    "01": "DIRECT",
    "02": "SURROUND",
    "03": "FILM, Game-RPG",
    "04": "THX",
    "05": "ACTION, Game-Action",
    "06": "MUSICAL, Game-Rock",
    "07": "MONO MOVIE",
    "08": "ORCHESTRA",
    "09": "UNPLUGGED",
    "0A": "STUDIO-MIX",
    "0B": "TV LOGIC",
    "0C": "ALL CH STEREO",
    "0D": "THEATER-DIMENSIONAL",
    "0E": "ENHANCED 7/ENHANCE, Game-Sports",
    "0F": "MONO",
    "11": "PURE AUDIO",
    "12": "MULTIPLEX",
    "13": "FULL MONO",
    "14": "DOLBY VIRTUAL",
    "15": "DTS Surround Sensation",
    "16": "Audyssey DSX",
    "1F": "Whole House Mode",
    "23": "Stage",
    "25": "Action",
    "26": "Music",
    "2E": "Sports",
    "40": "5.1ch Surround",
    "41": "Dolby EX/DTS ES",
    "42": "THX Cinema",
    "43": "THX Surround EX",
    "44": "THX Music",
    "45": "THX Games",
    "50": "THX U2/S2/I/S Cinema/Cinema2",
    "51": "THX MusicMode,THX U2/S2/I/S Music",
    "52": "THX Games Mode,THX U2/S2/I/S Games",
    "80": "PLII/PLIIx Movie",
    "81": "PLII/PLIIx Music",
    "82": "Neo:6 Cinema/Neo:X Cinema",
    "83": "Neo:6 Music/Neo:X Music",
    "84": "PLII/PLIIx THX Cinema",
    "85": "Neo:6/Neo:X THX Cinema",
    "86": "PLII/PLIIx Game",
    "87": "Neural Surr*3",
    "88": "Neural THX/Neural Surround",
    "89": "PLII/PLIIx THX Games",
    "8A": "Neo:6/Neo:X THX Games",
    "8B": "PLII/PLIIx THX Music",
    "8C": "Neo:6/Neo:X THX Music",
    "8D": "Neural THX Cinema",
    "8E": "Neural THX Music",
    "8F": "Neural THX Games",
    "90": "PLIIz Height",
    "91": "Neo:6 Cinema DTS Surround Sensation",
    "92": "Neo:6 Music DTS Surround Sensation",
    "93": "Neural Digital Music",
    "94": "PLIIz Height + THX Cinema",
    "95": "PLIIz Height + THX Music",
    "96": "PLIIz Height + THX Games",
    "97": "PLIIz Height + THX U2/S2 Cinema",
    "98": "PLIIz Height + THX U2/S2 Music",
    "99": "PLIIz Height + THX U2/S2 Games",
    "9A": "Neo:X Game",
    "A0": "PLIIx/PLII Movie + Audyssey DSX",
    "A1": "PLIIx/PLII Music + Audyssey DSX",
    "A2": "PLIIx/PLII Game + Audyssey DSX",
    "A3": "Neo:6 Cinema + Audyssey DSX",
    "A4": "Neo:6 Music + Audyssey DSX",
    "A5": "Neural Surround + Audyssey DSX",
    "A6": "Neural Digital Music + Audyssey DSX",
    "A7": "Dolby EX + Audyssey DSX",
}
