"""Test interaction with device.

WARNING: Running these tests will randomize your device's configuration.
"""

import random
import string
import time

import pytest

from eh_fifty import _EQ_PRESETS, Device, NoiseGateMode, SliderType

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


def test_get_eq_preset_name(device: Device) -> None:
    for preset in _EQ_PRESETS:
        name = device.get_eq_preset_name(preset)
        assert len(name) > 0
        assert all(c in string.ascii_letters for c in name)


def test_get_charge_status(device: Device) -> None:
    charge_status = device.get_charge_status()
    assert isinstance(charge_status.is_charging, bool)
    assert 0 <= charge_status.charge_percent <= 100


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
