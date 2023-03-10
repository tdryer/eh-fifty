"""Test interaction with device.

WARNING: Running these tests will randomize your device's configuration.
"""

import random
import string
import time

import pytest

from eh_fifty import (
    _EQ_PRESET_BANDS,
    _EQ_PRESET_MAX_BANDWIDTH,
    _EQ_PRESET_MAX_CENTER_FREQ,
    _EQ_PRESET_MAX_GAIN,
    _EQ_PRESET_MIN_BANDWIDTH,
    _EQ_PRESET_MIN_CENTER_FREQ,
    _EQ_PRESET_MIN_GAIN,
    _EQ_PRESETS,
    _MIC_EQ_PRESETS,
    Device,
    NoiseGateMode,
    SliderType,
)

# pylint: disable=missing-function-docstring


@pytest.fixture(name="device", scope="session")
def _device() -> Device:
    return Device()


def test_alert_volume(device: Device) -> None:
    saved_alert_volume = random.randrange(0, 100)
    device.set_alert_volume(saved_alert_volume)

    device.save_values()

    active_alert_volume = random.randrange(0, 100)
    device.set_alert_volume(active_alert_volume)

    assert device.get_alert_volume() == active_alert_volume
    assert device.get_alert_volume(saved=True) == saved_alert_volume


def test_noise_gate_mode(device: Device) -> None:
    saved_noise_gate_mode = random.choice(list(NoiseGateMode))
    device.set_noise_gate_mode(saved_noise_gate_mode)

    device.save_values()

    active_noise_gate_mode = random.choice(list(NoiseGateMode))
    device.set_noise_gate_mode(active_noise_gate_mode)

    assert device.get_noise_gate_mode() == active_noise_gate_mode
    assert device.get_noise_gate_mode(saved=True) == saved_noise_gate_mode


def test_mic_eq(device: Device) -> None:
    saved_mic_eq = random.choice(_MIC_EQ_PRESETS)
    device.set_mic_eq(saved_mic_eq)

    device.save_values()

    active_mic_eq = random.choice(_MIC_EQ_PRESETS)
    device.set_mic_eq(active_mic_eq)

    assert device.get_mic_eq() == active_mic_eq
    assert device.get_mic_eq(saved=True) == saved_mic_eq


def test_sliders(device: Device) -> None:
    saved_slider_values = {
        slider_type: random.randrange(0, 100) for slider_type in SliderType
    }
    for slider_type, slider_value in saved_slider_values.items():
        device.set_slider_value(slider_type, slider_value)

    device.save_values()

    active_slider_values = {
        slider_type: random.randrange(0, 100) for slider_type in SliderType
    }
    for slider_type, slider_value in active_slider_values.items():
        device.set_slider_value(slider_type, slider_value)

    for slider_type in SliderType:
        assert device.get_slider_value(slider_type) == active_slider_values[slider_type]
        assert (
            device.get_slider_value(slider_type, saved=True)
            == saved_slider_values[slider_type]
        )


def test_active_eq_preset(device: Device) -> None:
    eq_preset = random.choice(_EQ_PRESETS)
    device.set_active_eq_preset(eq_preset)

    time.sleep(1)  # takes about half a second to settle

    assert device.get_active_eq_preset() == eq_preset


def test_eq_preset_name(device: Device) -> None:
    preset_names = {
        preset: "".join(
            random.choice(string.printable) for _ in range(random.randrange(1, 51))
        )
        for preset in _EQ_PRESETS
    }
    for preset, name in preset_names.items():
        device.set_eq_preset_name(preset, name)
        assert device.get_eq_preset_name(preset) == name

    device.save_values()

    for preset, name in preset_names.items():
        assert device.get_eq_preset_name(preset, saved=True) == name


def test_get_battery_status(device: Device) -> None:
    battery_status = device.get_battery_status()
    assert isinstance(battery_status.is_charging, bool)
    assert 0 <= battery_status.charge_percent <= 100


def test_balance(device: Device) -> None:
    balance = random.randrange(0, 255)
    device.set_default_balance(balance)

    time.sleep(0.1)  # takes about 50ms to settle

    assert device.get_balance() == balance


def test_default_balance(device: Device) -> None:
    saved_default_balance = random.randrange(0, 255)
    device.set_default_balance(saved_default_balance)

    device.save_values()

    active_default_balance = random.randrange(0, 255)
    device.set_default_balance(active_default_balance)

    assert device.get_default_balance() == active_default_balance
    assert device.get_default_balance(saved=True) == saved_default_balance


def test_headset_status(device: Device) -> None:
    headset_status = device.get_headset_status()
    assert isinstance(headset_status.is_docked, bool)
    assert isinstance(headset_status.is_on, bool)


def test_eq_preset_gain(device: Device) -> None:
    preset_gain = {
        preset: [
            random.randrange(_EQ_PRESET_MIN_GAIN, _EQ_PRESET_MAX_GAIN + 1)
            for _ in range(5)
        ]
        for preset in _EQ_PRESETS
    }
    for preset, gain in preset_gain.items():
        device.set_eq_preset_gain(preset, gain)
        assert device.get_eq_preset_gain(preset).gain == gain

    device.save_values()

    for preset, gain in preset_gain.items():
        assert device.get_eq_preset_gain(preset).saved_gain == gain


def test_eq_preset_freq_and_bw(device: Device) -> None:
    preset_freq_and_bw = {
        preset: {
            band: (
                random.randrange(
                    _EQ_PRESET_MIN_CENTER_FREQ, _EQ_PRESET_MAX_CENTER_FREQ + 1
                ),
                0
                if band in {1, 5}
                else random.randrange(
                    _EQ_PRESET_MIN_BANDWIDTH, _EQ_PRESET_MAX_BANDWIDTH + 1
                ),
            )
            for band in _EQ_PRESET_BANDS
        }
        for preset in _EQ_PRESETS
    }
    for preset, bands in preset_freq_and_bw.items():
        for band, (center_freq, bandwidth) in bands.items():
            device.set_eq_preset_freq_and_bw(preset, band, center_freq, bandwidth)
            freq_and_bw = device.get_eq_preset_freq_and_bw(preset, band)
            assert freq_and_bw.center_freq == center_freq
            assert freq_and_bw.bandwidth == bandwidth

    device.save_values()

    for preset, bands in preset_freq_and_bw.items():
        for band, (center_freq, bandwidth) in bands.items():
            freq_and_bw = device.get_eq_preset_freq_and_bw(preset, band)
            assert freq_and_bw.saved_center_freq == center_freq
            assert freq_and_bw.saved_bandwidth == bandwidth
