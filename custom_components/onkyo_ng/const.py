"""Constants for the Onkyo integration."""

from enum import Enum
import typing
from typing import ClassVar, Literal, Self

import pyeiscp

DOMAIN = "onkyo"

DEVICE_INTERVIEW_TIMEOUT = 5
DEVICE_DISCOVERY_TIMEOUT = 5

CONF_SOURCES = "sources"
CONF_MODES = "modes"
CONF_RECEIVER_MAX_VOLUME = "receiver_max_volume"

type VolumeResolution = Literal[50, 80, 100, 200]
OPTION_VOLUME_RESOLUTION = "volume_resolution"
OPTION_VOLUME_RESOLUTION_DEFAULT: VolumeResolution = 50
VOLUME_RESOLUTION_ALLOWED: tuple[VolumeResolution, ...] = typing.get_args(
    VolumeResolution.__value__
)

OPTION_MAX_VOLUME = "max_volume"
OPTION_MAX_VOLUME_DEFAULT = 100.0

OPTION_INPUT_SOURCES = "input_sources"
OPTION_LISTENING_MODES = "listening_modes"

_INPUT_SOURCE_MEANINGS = {
    "00": "VIDEO1 ··· VCR/DVR ··· STB/DVR",
    "01": "VIDEO2 ··· CBL/SAT",
    "02": "VIDEO3 ··· GAME/TV ··· GAME",
    "03": "VIDEO4 ··· AUX",
    "04": "VIDEO5 ··· AUX2 ··· GAME2",
    "05": "VIDEO6 ··· PC",
    "06": "VIDEO7",
    "07": "HIDDEN1 ··· EXTRA1",
    "08": "HIDDEN2 ··· EXTRA2",
    "09": "HIDDEN3 ··· EXTRA3",
    "10": "DVD ··· BD/DVD",
    "11": "STRM BOX",
    "12": "TV",
    "20": "TAPE ··· TV/TAPE",
    "21": "TAPE2",
    "22": "PHONO",
    "23": "CD ··· TV/CD",
    "24": "FM",
    "25": "AM",
    "26": "TUNER",
    "27": "MUSIC SERVER ··· P4S ··· DLNA",
    "28": "INTERNET RADIO ··· IRADIO FAVORITE",
    "29": "USB ··· USB(FRONT)",
    "2A": "USB(REAR)",
    "2B": "NETWORK ··· NET",
    "2D": "AIRPLAY",
    "2E": "BLUETOOTH",
    "2F": "USB DAC IN",
    "30": "MULTI CH",
    "31": "XM",
    "32": "SIRIUS",
    "33": "DAB",
    "40": "UNIVERSAL PORT",
    "41": "LINE",
    "42": "LINE2",
    "44": "OPTICAL",
    "45": "COAXIAL",
    "55": "HDMI 5",
    "56": "HDMI 6",
    "57": "HDMI 7",
    "80": "MAIN SOURCE",
}

_LISTENING_MODES_MEANINGS = {
    "00": "STEREO",
    "01": "DIRECT",
    "02": "SURROUND",
    "03": "FILM",
    "04": "THX",
    "05": "ACTION",
    "06": "MUSICAL",
    "07": "MONO MOVIE",
    "08": "ORCHESTRA",
    "09": "UNPLUGGED",
    "0A": "STUDIO-MIX",
    "0B": "TV LOGIC",
    "0C": "ALL CH STEREO",
    "0D": "THEATER-DIMENSIONAL",
    "0E": "ENHANCED 7/ENHANCE",
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
    "40": "Straight Decode",
    "41": "Dolby EX/DTS ES",
    "42": "THX Cinema",
    "43": "THX Surround EX",
    "44": "THX Music",
    "45": "THX Games",
    "50": "THX U2/S2 Cinema/Cinema2",
    "51": "THX U2/S2 Music/Music2",
    "52": "THX U2/S2 Games",
    "80": "PLII/PLIIx Movie",
    "81": "PLII/PLIIx Music",
    "82": "Neo:6 Cinema",
    "83": "Neo:6 Music",
    "84": "PLII/PLIIx THX Cinema",
    "85": "Neo:6 THX Cinema",
    "86": "PLII/PLIIx Game",
    "87": "Neural Surr",
    "88": "Neural THX",
    "89": "PLII/PLIIx THX Games",
    "8A": "Neo:6 THX Games",
    "8B": "PLII/PLIIx THX Music",
    "8C": "Neo:6 THX Music",
    "8D": "Neural THX Cinema",
    "8E": "Neural THX Music",
    "8F": "Neural THX Games",
    "90": "PLIIz Height",
    "91": "Neo 6 Cinema DTS Surround Sensation",
    "92": "Neo 6 Music DTS Surround Sensation",
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


class InputSource(Enum):
    """Receiver input source."""

    DVR = "00"
    CBL = "01"
    GAME = "02"
    AUX = "03"
    GAME2 = "04"
    PC = "05"
    VIDEO7 = "06"
    EXTRA1 = "07"
    EXTRA2 = "08"
    EXTRA3 = "09"
    DVD = "10"
    STRM_BOX = "11"
    TV = "12"
    TAPE = "20"
    TAPE2 = "21"
    PHONO = "22"
    CD = "23"
    FM = "24"
    AM = "25"
    TUNER = "26"
    MUSIC_SERVER = "27"
    INTERNET_RADIO = "28"
    USB = "29"
    USB_REAR = "2A"
    NETWORK = "2B"
    AIRPLAY = "2D"
    BLUETOOTH = "2E"
    USB_DAC_IN = "2F"
    MULTI_CH = "30"
    XM = "31"
    SIRIUS = "32"
    DAB = "33"
    UNIVERSAL_PORT = "40"
    LINE = "41"
    LINE2 = "42"
    OPTICAL = "44"
    COAXIAL = "45"
    HDMI_5 = "55"
    HDMI_6 = "56"
    HDMI_7 = "57"
    MAIN_SOURCE = "80"

    __meaning_mapping: ClassVar[dict[str, Self]] = {}  # type: ignore[misc]

    value_meaning: str

    def __new__(cls, value: str) -> Self:
        """Create InputSource enum."""
        obj = object.__new__(cls)
        obj._value_ = value
        obj.value_meaning = _INPUT_SOURCE_MEANINGS[value]

        cls.__meaning_mapping[obj.value_meaning] = obj

        return obj

    @classmethod
    def from_meaning(cls, meaning: str) -> Self:
        """Get InputSource enum from its meaning."""
        return cls.__meaning_mapping[meaning]


class ListeningMode(Enum):
    """Enum representing listening modes."""

    STEREO = "00"
    DIRECT = "01"
    SURROUND = "02"
    FILM = "03"
    THX = "04"
    ACTION_1 = "05"
    MUSICAL = "06"
    MONO_MOVIE = "07"
    ORCHESTRA = "08"
    UNPLUGGED = "09"
    STUDIO_MIX = "0A"
    TV_LOGIC = "0B"
    ALL_CH_STEREO = "0C"
    THEATER_DIMENSIONAL = "0D"
    ENHANCED_7_ENHANCE = "0E"
    MONO = "0F"
    PURE_AUDIO = "11"
    MULTIPLEX = "12"
    FULL_MONO = "13"
    DOLBY_VIRTUAL = "14"
    DTS_SURROUND_SENSATION = "15"
    AUDYSSEY_DSX = "16"
    WHOLE_HOUSE_MODE = "1F"
    STAGE = "23"
    ACTION_2 = "25"
    MUSIC_1 = "26"
    SPORTS = "2E"
    STRAIGHT_DECODE = "40"
    DOLBY_EX_DTS_ES = "41"
    THX_CINEMA = "42"
    THX_SURROUND_EX = "43"
    THX_MUSIC = "44"
    THX_GAMES = "45"
    THX_U2_S2_CINEMA_CINEMA2 = "50"
    THX_U2_S2_MUSIC_MUSIC2 = "51"
    THX_U2_S2_GAMES = "52"
    PLII_PLIIX_MOVIE = "80"
    PLII_PLIIX_MUSIC = "81"
    NEO6_CINEMA = "82"
    NEO6_MUSIC = "83"
    PLII_PLIIX_THX_CINEMA = "84"
    NEO6_THX_CINEMA = "85"
    PLII_PLIIX_GAME = "86"
    NEURAL_SURROUND = "87"
    NEURAL_THX = "88"
    PLII_PLIIX_THX_GAMES = "89"
    NEO6_THX_GAMES = "8A"
    PLII_PLIIX_THX_MUSIC = "8B"
    NEO6_THX_MUSIC = "8C"
    NEURAL_THX_CINEMA = "8D"
    NEURAL_THX_MUSIC = "8E"
    NEURAL_THX_GAMES = "8F"
    PLIIZ_HEIGHT = "90"
    NEO6_CINEMA_DTS_SURROUND_SENSATION = "91"
    NEO6_MUSIC_DTS_SURROUND_SENSATION = "92"
    NEURAL_DIGITAL_MUSIC = "93"
    PLIIZ_HEIGHT_THX_CINEMA = "94"
    PLIIZ_HEIGHT_THX_MUSIC = "95"
    PLIIZ_HEIGHT_THX_GAMES = "96"
    PLIIZ_HEIGHT_THX_U2_S2_CINEMA = "97"
    PLIIZ_HEIGHT_THX_U2_S2_MUSIC = "98"
    PLIIZ_HEIGHT_THX_U2_S2_GAMES = "99"
    NEOX_GAME = "9A"
    PLIIX_PLII_MOVIE_AUDYSSEY_DSX = "A0"
    PLIIX_PLII_MUSIC_AUDYSSEY_DSX = "A1"
    PLIIX_PLII_GAME_AUDYSSEY_DSX = "A2"
    NEO6_CINEMA_AUDYSSEY_DSX = "A3"
    NEO6_MUSIC_AUDYSSEY_DSX = "A4"
    NEURAL_SURROUND_AUDYSSEY_DSX = "A5"
    NEURAL_DIGITAL_MUSIC_AUDYSSEY_DSX = "A6"
    DOLBY_EX_AUDYSSEY_DSX = "A7"

    __meaning_mapping: ClassVar[dict[str, Self]] = {}  # type: ignore[misc]

    value_meaning: str

    def __new__(cls, value: str) -> Self:
        """Create ListeningMode enum."""
        obj = object.__new__(cls)
        obj._value_ = value
        obj.value_meaning = _LISTENING_MODES_MEANINGS[value]

        cls.__meaning_mapping[obj.value_meaning] = obj

        return obj

    @classmethod
    def from_meaning(cls, meaning: str) -> Self:
        """Get ListeningMode enum from its meaning."""
        return cls.__meaning_mapping[meaning]


ZONES = {"main": "Main", "zone2": "Zone 2", "zone3": "Zone 3", "zone4": "Zone 4"}

PYEISCP_COMMANDS = pyeiscp.commands.COMMANDS
