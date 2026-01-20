"""Configure Astro A50 gen 4 devices."""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from enum import Enum
from itertools import takewhile
from types import TracebackType

import usb.core
import usb.util
from hexdump import hexdump

__version__ = "0.3.0"

LOGGER = logging.getLogger(__name__)

_VENDOR = 0x9886
_PRODUCT = 0x002C
_ENDPOINT_IN = 0x85
_ENDPOINT_OUT = 0x05
_INTERFACE = 6
_TIMEOUT_MS = 3000  # `SAVE_VALUES` response can take over 2 seconds.
_EQ_PRESETS = [1, 2, 3]
_EQ_PRESET_BANDS = [1, 2, 3, 4, 5]
_DB_OFFSET = 12
_EQ_PRESET_MIN_GAIN = -7
_EQ_PRESET_MAX_GAIN = 7
_EQ_PRESET_MIN_CENTER_FREQ = 80
_EQ_PRESET_MAX_CENTER_FREQ = 15_000
_EQ_PRESET_MIN_BANDWIDTH = int(4096 * 0.1)
_EQ_PRESET_MAX_BANDWIDTH = int(4096 * 3.0)
_MIC_EQ_PRESETS = [0, 1, 2]


class Device:
    """Astro A50 gen 4 USB device."""

    def __init__(self) -> None:
        self._dev = usb.core.find(idVendor=_VENDOR, idProduct=_PRODUCT)
        if self._dev is None:
            raise DeviceNotConnected
        self._detached_driver = False
        if self._dev.is_kernel_driver_active(_INTERFACE):
            self._dev.detach_kernel_driver(_INTERFACE)
            self._detached_driver = True

    def close(self) -> None:
        """Release the device and reattach kernel driver."""
        if self._dev is not None:
            try:
                usb.util.release_interface(self._dev, _INTERFACE)
            except usb.core.USBError:
                LOGGER.debug("Failed to release interface")
            if self._detached_driver:
                try:
                    self._dev.attach_kernel_driver(_INTERFACE)
                except usb.core.USBError:
                    LOGGER.debug("Failed to re-attach kernel driver")
                self._detached_driver = False
            usb.util.dispose_resources(self._dev)
        self._dev = None

    def __enter__(self) -> "Device":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, ensuring device is closed."""
        self.close()

    def _request(
        self, request_type: _CommandType, payload: list[int] | None = None
    ) -> bytes:
        request = [0x02, request_type.value]
        if payload:
            request.extend([len(payload), *payload])
        assert len(request) <= 64
        LOGGER.debug("Writing %s request\n%s", request_type, hexdump(request))
        assert self._dev.write(_ENDPOINT_OUT, request, _TIMEOUT_MS) == len(request)

        try:
            resp: bytes = self._dev.read(_ENDPOINT_IN, 64, _TIMEOUT_MS)
        except usb.core.USBTimeoutError:
            # Resetting the device after a timeout is necessary to avoid
            # getting garbage in subsequent responses.
            LOGGER.warning("Resetting device due to timeout")
            self._dev.reset()
            raise
        LOGGER.debug("Received %s response\n%s", request_type, hexdump(resp))
        assert resp[0] == 0x02
        assert resp[1] in {_ResponseStatus.NO_RESPONSE.value, _ResponseStatus.OK.value}
        length = resp[2]
        # Cap length at actual response size (some firmware reports incorrect length)
        length = min(length, len(resp) - 3)
        return bytes(resp[3 : 3 + length])

    def get_active_eq_preset(self) -> int:
        """Get the active EQ preset."""
        resp = self._request(_CommandType.GET_ACTIVE_EQ_PRESET)
        assert len(resp) >= 1
        assert resp[0] in _EQ_PRESETS
        return resp[0]

    def set_active_eq_preset(self, preset: int) -> None:
        """Set the active EQ preset."""
        assert preset in _EQ_PRESETS
        resp = self._request(_CommandType.SET_ACTIVE_EQ_PRESET, [preset])
        assert len(resp) >= 2
        assert resp[0] == _CommandType.SET_ACTIVE_EQ_PRESET.value
        assert resp[1] == preset

    def get_eq_preset_name(self, preset: int, saved: bool = False) -> str:
        """Get an EQ preset name.

        If `saved=True`, return the saved name instead of the active name.
        """
        assert preset in _EQ_PRESETS
        resp = self._request(_CommandType.GET_EQ_PRESET_NAME, [preset, int(saved)])
        assert len(resp) > 2
        assert resp[0] == _CommandType.GET_EQ_PRESET_NAME.value
        assert resp[1] == preset
        preset_name = takewhile(lambda c: c > 0, resp[2:])
        return bytes(preset_name).decode()

    def set_eq_preset_name(self, preset: int, name: str) -> None:
        """Set an EQ preset name."""
        assert preset in _EQ_PRESETS
        encoded_name = name.encode() + b"\x00"
        resp = self._request(
            _CommandType.SET_EQ_PRESET_NAME,
            [preset, len(encoded_name), *encoded_name],
        )
        assert len(resp) >= 2
        assert resp[0] == _CommandType.SET_EQ_PRESET_NAME.value
        assert resp[1] == preset

    def get_eq_preset_gain(self, preset: int) -> EQPresetGain:
        """Get the gain for each band in an EQ preset."""
        assert preset in _EQ_PRESETS
        resp = self._request(_CommandType.GET_EQ_PRESET_GAIN, [preset])
        assert len(resp) >= 12
        assert resp[0] == _CommandType.GET_EQ_PRESET_GAIN.value
        assert resp[1] == preset
        values = list(struct.iter_unpack("<BBBBB", resp[2:]))
        return EQPresetGain(
            gain=[db - _DB_OFFSET for db in values[0]],
            saved_gain=[db - _DB_OFFSET for db in values[1]],
        )

    def set_eq_preset_gain(self, preset: int, gain: list[int]) -> None:
        """Set the gain for each band in an EQ preset."""
        assert preset in _EQ_PRESETS
        assert len(gain) == 5
        assert all(
            _EQ_PRESET_MIN_GAIN <= band_gain <= _EQ_PRESET_MAX_GAIN
            for band_gain in gain
        )
        resp = self._request(
            _CommandType.SET_EQ_PRESET_GAIN,
            [preset, *[band_gain + _DB_OFFSET for band_gain in gain]],
        )
        assert len(resp) >= 2
        assert resp[0] == _CommandType.SET_EQ_PRESET_GAIN.value
        assert resp[1] == preset

    def get_eq_preset_freq_and_bw(self, preset: int, band: int) -> EQPresetFreqAndBW:
        """Get the frequency and bandwidth of a band in an EQ preset."""
        assert preset in _EQ_PRESETS
        assert band in _EQ_PRESET_BANDS
        resp = self._request(_CommandType.GET_EQ_PRESET_FREQ_AND_BW, [preset, band])
        assert len(resp) >= 11
        assert resp[0] == _CommandType.GET_EQ_PRESET_FREQ_AND_BW.value
        assert resp[1] == preset
        assert resp[2] == band
        values = list(value for value, in struct.iter_unpack("<H", resp[3:]))
        return EQPresetFreqAndBW(
            bandwidth=values[0],
            saved_bandwidth=values[1],
            center_freq=values[2],
            saved_center_freq=values[3],
        )

    def set_eq_preset_freq_and_bw(
        self, preset: int, band: int, center_freq: int, bandwidth: int
    ) -> None:
        """Set the frequency and bandwidth of a band in an EQ preset."""
        assert preset in _EQ_PRESETS
        assert band in _EQ_PRESET_BANDS
        assert _EQ_PRESET_MIN_CENTER_FREQ <= center_freq <= _EQ_PRESET_MAX_CENTER_FREQ
        if band in {1, 5}:
            assert bandwidth == 0
        else:
            assert _EQ_PRESET_MIN_BANDWIDTH <= bandwidth <= _EQ_PRESET_MAX_BANDWIDTH
        resp = self._request(
            _CommandType.SET_EQ_PRESET_FREQ_AND_BW,
            [
                preset,
                band,
                *struct.pack("<H", bandwidth),
                *struct.pack("<H", center_freq),
            ],
        )
        assert len(resp) >= 4
        assert resp[0] == _CommandType.SET_EQ_PRESET_FREQ_AND_BW.value
        assert resp[1] == preset
        assert resp[2] == band
        assert resp[3] == 0

    def get_battery_status(self) -> BatteryStatus:
        """Get the battery status."""
        resp = self._request(_CommandType.GET_BATTERY_STATUS)
        assert len(resp) >= 1
        return BatteryStatus(
            is_charging=bool(resp[0] & 128),
            charge_percent=resp[0] & 127,
        )

    def get_balance(self) -> int:
        """Get the balance.

        Balance is represented by integer in range 0 (100% game audio) to 255
        (100% chat audio).

        This value is the same as the default balance, until the buttons on the
        headset have adjusted it.
        """
        resp = self._request(_CommandType.GET_BALANCE)
        assert len(resp) >= 1
        assert 0 <= resp[0] <= 255
        return resp[0]

    def get_default_balance(self, saved: bool = False) -> int:
        """Get the default balance.

        Balance is represented by integer in range 0 (100% game audio) to 255
        (100% chat audio).

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_CommandType.GET_DEFAULT_BALANCE, [int(saved)])
        assert len(resp) >= 1
        assert 0 <= resp[0] <= 255
        return resp[0]

    def set_default_balance(self, balance: int) -> None:
        """Set the default balance.

        Balance is represented by integer in range 0 (100% game audio) to 255
        (100% chat audio).
        """
        assert 0 <= balance <= 255
        resp = self._request(_CommandType.SET_DEFAULT_BALANCE, [balance])
        assert len(resp) >= 1
        assert resp[0] == _CommandType.SET_DEFAULT_BALANCE.value

    def get_headset_status(self) -> HeadsetStatus:
        """Get the headset status."""
        resp = self._request(_CommandType.GET_HEADSET_STATUS)
        assert len(resp) >= 1
        return HeadsetStatus(
            is_docked=bool(resp[0] & 0x01),
            is_on=bool(resp[0] & 0x02),
        )

    def get_alert_volume(self, saved: bool = False) -> int:
        """Get the alert volume as percent.

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_CommandType.GET_ALERT_VOLUME, [int(saved)])
        assert len(resp) >= 1
        assert 0 <= resp[0] <= 100
        return resp[0]

    def set_alert_volume(self, volume_percent: int) -> None:
        """Set the alert volume as percent."""
        assert 0 <= volume_percent <= 100
        resp = self._request(_CommandType.SET_ALERT_VOLUME, [volume_percent])
        assert len(resp) >= 1
        assert resp[0] == _CommandType.SET_ALERT_VOLUME.value

    def get_noise_gate_mode(self, saved: bool = False) -> NoiseGateMode:
        """Get the noise gate mode.

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_CommandType.GET_NOISE_GATE_MODE)
        assert len(resp) >= 3
        assert resp[0] == _CommandType.GET_NOISE_GATE_MODE.value
        return NoiseGateMode(resp[1 + int(saved)])

    def set_noise_gate_mode(self, noise_gate_mode: NoiseGateMode) -> None:
        """Set the noise gate mode."""
        assert isinstance(noise_gate_mode, NoiseGateMode)
        resp = self._request(_CommandType.SET_NOISE_GATE_MODE, [noise_gate_mode.value])
        assert len(resp) >= 1
        assert resp[0] == noise_gate_mode.value

    def get_mic_eq(self, saved: bool = False) -> int:
        """Get the microphone EQ preset.

        The valid presets are 0, 1, and 2. Their meanings are unknown.

        If `saved=True`, return the saved value instead of the active value.
        """
        resp = self._request(_CommandType.GET_MIC_EQ, [int(saved)])
        assert len(resp) >= 1
        assert resp[0] in _MIC_EQ_PRESETS
        return resp[0]

    def set_mic_eq(self, mic_eq: int) -> None:
        """Set the microphone EQ preset."""
        assert mic_eq in _MIC_EQ_PRESETS
        resp = self._request(_CommandType.SET_MIC_EQ, [mic_eq])
        assert len(resp) >= 1
        assert resp[0] == _CommandType.SET_MIC_EQ.value

    def get_slider_value(self, slider_type: SliderType, saved: bool = False) -> int:
        """Get slider slider value.

        If `saved=True`, return the saved value instead of the active value.
        """
        assert isinstance(slider_type, SliderType)
        resp = self._request(_CommandType.GET_SLIDER_VALUE, [slider_type.value])
        assert len(resp) >= 4
        assert resp[0] == _CommandType.GET_SLIDER_VALUE.value
        assert resp[1] == slider_type.value
        return resp[2 + int(saved)]

    def set_slider_value(self, slider_type: SliderType, value_percent: int) -> None:
        """Set a slider value as percent."""
        assert isinstance(slider_type, SliderType)
        assert 0 <= value_percent <= 100
        resp = self._request(
            _CommandType.SET_SLIDER_VALUE, [slider_type.value, value_percent]
        )
        assert len(resp) >= 2
        assert resp[0] == _CommandType.SET_SLIDER_VALUE.value
        assert resp[1] == slider_type.value

    def save_values(self) -> None:
        """Save the active configuration values."""
        resp = self._request(_CommandType.SAVE_VALUES)
        assert len(resp) >= 2
        assert resp[0] == _CommandType.SAVE_VALUES.value
        assert resp[1] == 0x00


class DeviceNotConnected(Exception):
    """Device not connected."""


class _CommandType(Enum):

    GET_HEADSET_STATUS = 0x54
    SAVE_VALUES = 0x61
    SET_SLIDER_VALUE = 0x62
    SET_EQ_PRESET_GAIN = 0x63
    SET_NOISE_GATE_MODE = 0x64
    SET_ACTIVE_EQ_PRESET = 0x67
    GET_SLIDER_VALUE = 0x68
    GET_EQ_PRESET_GAIN = 0x69
    GET_NOISE_GATE_MODE = 0x6A
    GET_ACTIVE_EQ_PRESET = 0x6C
    SET_EQ_PRESET_NAME = 0x6D
    GET_EQ_PRESET_NAME = 0x6E
    SET_EQ_PRESET_FREQ_AND_BW = 0x6F
    GET_EQ_PRESET_FREQ_AND_BW = 0x70
    SET_MIC_EQ = 0x71
    GET_BALANCE = 0x72
    SET_DEFAULT_BALANCE = 0x73
    SET_ALERT_VOLUME = 0x76
    GET_DEFAULT_BALANCE = 0x77
    GET_ALERT_VOLUME = 0x7A
    GET_MIC_EQ = 0x7B
    GET_BATTERY_STATUS = 0x7C


class _ResponseStatus(Enum):

    NO_RESPONSE = 0
    ERROR = 1
    OK = 2


@dataclass
class EQPresetGain:
    """The gain for each band of an EQ preset.

    Each list contains the gain for the band at the corresponding index.

    Gain is represented in decibels and may vary from -7 to 7 dB.
    """

    gain: list[int]
    saved_gain: list[int]


@dataclass
class EQPresetFreqAndBW:
    """Frequency and bandwidth for single band of an EQ preset.

    Bandwidth is a multiple of the center frequency, which has been quantized
    to an integer by multiplying it by 4096.

    Center frequency is represented by hertz.
    """

    bandwidth: int
    saved_bandwidth: int
    center_freq: int
    saved_center_freq: int


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
class BatteryStatus:
    """Headset battery status."""

    is_charging: bool
    charge_percent: int


@dataclass
class HeadsetStatus:
    """Headset status."""

    is_on: bool
    is_docked: bool
