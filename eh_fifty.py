"""Configure Astro A50 gen 4 devices."""

import logging
from dataclasses import dataclass
from enum import Enum
from itertools import takewhile

import usb.core
import usb.util
from hexdump import hexdump

__version__ = "0.2.0"

LOGGER = logging.getLogger(__name__)

_VENDOR = 0x9886
_PRODUCT = 0x002C
_ENDPOINT_IN = 0x85
_ENDPOINT_OUT = 0x05
_INTERFACE = 6
_TIMEOUT_MS = 3000  # `SAVE_VALUES` response can take over 2 seconds.
_EQ_PRESETS = [1, 2, 3]


class Device:
    """Astro A50 gen 4 USB device."""

    def __init__(self):
        self._dev = usb.core.find(idVendor=_VENDOR, idProduct=_PRODUCT)
        if self._dev is None:
            raise DeviceNotConnected
        if self._dev.is_kernel_driver_active(_INTERFACE):
            self._dev.detach_kernel_driver(_INTERFACE)

    def _request(self, request_type, payload=b""):
        request = [0x02, request_type.value] + list(payload)
        assert len(request) <= 64
        LOGGER.debug("Writing %s request\n%s", request_type, hexdump(request))
        assert self._dev.write(_ENDPOINT_OUT, request, _TIMEOUT_MS) == len(request)

        try:
            resp = self._dev.read(_ENDPOINT_IN, 64, _TIMEOUT_MS)
        except usb.core.USBTimeoutError:
            # Resetting the device after a timeout is necessary to avoid
            # getting garbage in subsequent responses.
            LOGGER.warning("Resetting device due to timeout")
            self._dev.reset()
            raise
        LOGGER.debug("Received %s response\n%s", request_type, hexdump(resp))
        assert resp[0] == 0x02
        assert resp[1] == _ResponseStatus.OK.value
        length = resp[2]
        return bytes(resp[3 : 3 + length])

    def get_active_eq_preset(self):
        """Get the active EQ preset."""
        resp = self._request(_RequestType.GET_ACTIVE_EQ_PRESET)
        assert len(resp) == 1
        assert resp[0] in _EQ_PRESETS
        return resp[0]

    def set_active_eq_preset(self, preset):
        """Set the active EQ preset."""
        assert preset in _EQ_PRESETS
        resp = self._request(_RequestType.SET_ACTIVE_EQ_PRESET, [0x01, preset])
        assert len(resp) == 2
        assert resp[0] == _RequestType.SET_ACTIVE_EQ_PRESET.value
        assert resp[1] == preset

    def get_eq_preset_name(self, preset):
        """Get an EQ preset name."""
        assert preset in _EQ_PRESETS
        resp = self._request(_RequestType.GET_EQ_PRESET_NAME, [0x00, preset])
        assert len(resp) > 2
        assert resp[0] == _RequestType.GET_EQ_PRESET_NAME.value
        assert resp[1] == preset
        preset_name = takewhile(lambda c: c > 0, resp[2:])
        return bytes(preset_name).decode()

    def get_charge_status(self):
        """Get the change status."""
        resp = self._request(_RequestType.GET_CHARGE_STATUS)
        assert len(resp) == 1
        return ChargeStatus(
            is_charging=bool(resp[0] & 128),
            charge_percent=resp[0] & 127,
        )

    def get_balance(self, saved=False):
        """Get the game/chat audio balance.

        Balance is represented by integer in range 0 (game-only) to 255
        (chat-only).

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_RequestType.GET_BALANCE, [0x01, int(saved)])
        assert len(resp) == 1
        assert 0 <= resp[0] <= 255
        return resp[0]

    def set_balance(self, balance):
        """Set the game/chat audio balance.

        Balance is represented by integer in range 0 (game-only) to 255
        (chat-only).
        """
        assert 0 <= balance <= 255
        resp = self._request(_RequestType.SET_BALANCE, [0x01, balance])
        assert len(resp) == 1
        assert resp[0] == _RequestType.SET_BALANCE.value

    def get_headset_status(self):
        """Get the headset status."""
        resp = self._request(_RequestType.GET_HEADSET_STATUS)
        assert len(resp) == 1
        return HeadsetStatus(
            is_docked=bool(resp[0] & 0x01),
            is_on=bool(resp[0] & 0x02),
        )

    def get_alert_volume(self, saved=False):
        """Get the alert volume as percent.

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_RequestType.GET_ALERT_VOLUME, [0x01, int(saved)])
        assert len(resp) == 1
        assert 0 <= resp[0] <= 100
        return resp[0]

    def set_alert_volume(self, volume_percent):
        """Set the alert volume as percent."""
        assert 0 <= volume_percent <= 100
        resp = self._request(_RequestType.SET_ALERT_VOLUME, [0x01, volume_percent])
        assert len(resp) == 1
        assert resp[0] == _RequestType.SET_ALERT_VOLUME.value

    def get_noise_gate_mode(self, saved=False):
        """Get the noise gate mode.

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_RequestType.GET_NOISE_GATE_MODE)
        assert len(resp) == 3
        assert resp[0] == _RequestType.GET_NOISE_GATE_MODE.value
        return NoiseGateMode(resp[1 + int(saved)])

    def set_noise_gate_mode(self, noise_gate_mode):
        """Set the noise gate mode."""
        assert isinstance(noise_gate_mode, NoiseGateMode)
        resp = self._request(
            _RequestType.SET_NOISE_GATE_MODE, [0x01, noise_gate_mode.value]
        )
        assert len(resp) == 1
        assert resp[0] == noise_gate_mode.value

    def get_slider_value(self, slider_type, saved=False):
        """Get slider slider value.

        If `saved=True`, return the saved value instead of the active value.
        """
        assert isinstance(slider_type, SliderType)
        resp = self._request(_RequestType.GET_SLIDER_VALUE, [0x01, slider_type.value])
        assert len(resp) == 4
        assert resp[0] == _RequestType.GET_SLIDER_VALUE.value
        assert resp[1] == slider_type.value
        return resp[2 + int(saved)]

    def set_slider_value(self, slider_type, value_percent):
        """Set a slider value as percent."""
        assert isinstance(slider_type, SliderType)
        assert 0 <= value_percent <= 100
        resp = self._request(
            _RequestType.SET_SLIDER_VALUE, [0x02, slider_type.value, value_percent]
        )
        assert len(resp) == 2
        assert resp[0] == _RequestType.SET_SLIDER_VALUE.value
        assert resp[1] == slider_type.value

    def save_values(self):
        """Save the active configuration values."""
        resp = self._request(_RequestType.SAVE_VALUES)
        assert len(resp) == 2
        assert resp[0] == _RequestType.SAVE_VALUES.value
        assert resp[1] == 0x00


class DeviceNotConnected(Exception):
    """Device not connected."""


class _RequestType(Enum):

    GET_HEADSET_STATUS = 0x54
    SAVE_VALUES = 0x61
    SET_SLIDER_VALUE = 0x62
    SET_NOISE_GATE_MODE = 0x64
    SET_ACTIVE_EQ_PRESET = 0x67
    GET_SLIDER_VALUE = 0x68
    GET_NOISE_GATE_MODE = 0x6A
    GET_ACTIVE_EQ_PRESET = 0x6C
    GET_EQ_PRESET_NAME = 0x6E
    SET_BALANCE = 0x73
    SET_ALERT_VOLUME = 0x76
    GET_BALANCE = 0x77
    GET_ALERT_VOLUME = 0x7A
    GET_CHARGE_STATUS = 0x7C


class _ResponseStatus(Enum):

    ERROR = 0x1
    OK = 0x2


class NoiseGateMode(Enum):
    """Noise gate mode."""

    STREAMING = 0x00
    NIGHT = 0x01
    HOME = 0x02
    TOURNAMENT = 0x03


class SliderType(Enum):
    """Slider type."""

    STREAM_PORT_MIX_MIC = 0x00
    STREAM_PORT_MIX_CHAT = 0x01
    STREAM_PORT_MIX_GAME = 0x02
    STREAM_PORT_MIX_AUX = 0x03
    MIC = 0x04
    SIDE_TONE = 0x05


@dataclass
class ChargeStatus:
    """Change status."""

    is_charging: bool
    charge_percent: int


@dataclass
class HeadsetStatus:
    """Headset status."""

    is_on: bool
    is_docked: bool
