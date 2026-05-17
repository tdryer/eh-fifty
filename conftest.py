"""Shared pytest fixtures.

The `_backup_and_restore` fixture snapshots the device's configuration before
the test session and restores it afterward, so running `pytest` does not
clobber the user's saved settings.

Both *saved* and *active* values are captured where the protocol exposes them.
Restoration order is:
    1. Set every settable value to its *saved* snapshot, then `save_values()`
       to persist the previous saved state.
    2. Set every settable value to its *active* snapshot, leaving the device
       in the same active state it was in before the test session (without
       overwriting the saved state we just restored).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

import pytest

from eh_fifty import (
    _EQ_PRESET_BANDS,
    _EQ_PRESETS,
    Device,
    EQPresetFreqAndBW,
    EQPresetGain,
    NoiseGateMode,
    SliderType,
)


@dataclass
class _Snapshot:  # pylint: disable=too-many-instance-attributes
    alert_volume: tuple[int, int]
    noise_gate_mode: tuple[NoiseGateMode, NoiseGateMode]
    mic_eq: tuple[int, int]
    sliders: dict[SliderType, tuple[int, int]]
    active_eq_preset: int
    default_balance: tuple[int, int]
    eq_preset_name: dict[int, tuple[str, str]]
    eq_preset_gain: dict[int, EQPresetGain]
    eq_preset_freq_and_bw: dict[tuple[int, int], EQPresetFreqAndBW]


def _capture(device: Device) -> _Snapshot:
    return _Snapshot(
        alert_volume=(
            device.get_alert_volume(saved=True),
            device.get_alert_volume(),
        ),
        noise_gate_mode=(
            device.get_noise_gate_mode(saved=True),
            device.get_noise_gate_mode(),
        ),
        mic_eq=(device.get_mic_eq(saved=True), device.get_mic_eq()),
        sliders={
            s: (device.get_slider_value(s, saved=True), device.get_slider_value(s))
            for s in SliderType
        },
        active_eq_preset=device.get_active_eq_preset(),
        default_balance=(
            device.get_default_balance(saved=True),
            device.get_default_balance(),
        ),
        eq_preset_name={
            p: (
                device.get_eq_preset_name(p, saved=True),
                device.get_eq_preset_name(p),
            )
            for p in _EQ_PRESETS
        },
        eq_preset_gain={p: device.get_eq_preset_gain(p) for p in _EQ_PRESETS},
        eq_preset_freq_and_bw={
            (p, b): device.get_eq_preset_freq_and_bw(p, b)
            for p in _EQ_PRESETS
            for b in _EQ_PRESET_BANDS
        },
    )


def _apply_saved(device: Device, snap: _Snapshot) -> None:
    """Set every value to its saved snapshot. Caller must `save_values()` after."""
    device.set_alert_volume(snap.alert_volume[0])
    device.set_noise_gate_mode(snap.noise_gate_mode[0])
    device.set_mic_eq(snap.mic_eq[0])
    for s, (saved, _active) in snap.sliders.items():
        device.set_slider_value(s, saved)
    device.set_default_balance(snap.default_balance[0])
    for p, (saved_name, _active_name) in snap.eq_preset_name.items():
        device.set_eq_preset_name(p, saved_name)
    for p, gain in snap.eq_preset_gain.items():
        device.set_eq_preset_gain(p, gain.saved_gain)
    for (p, b), fb in snap.eq_preset_freq_and_bw.items():
        device.set_eq_preset_freq_and_bw(p, b, fb.saved_center_freq, fb.saved_bandwidth)


def _apply_active(device: Device, snap: _Snapshot) -> None:
    """Overlay active values on top of the saved state already persisted."""
    device.set_alert_volume(snap.alert_volume[1])
    device.set_noise_gate_mode(snap.noise_gate_mode[1])
    device.set_mic_eq(snap.mic_eq[1])
    for s, (_saved, active) in snap.sliders.items():
        device.set_slider_value(s, active)
    device.set_default_balance(snap.default_balance[1])
    device.set_active_eq_preset(snap.active_eq_preset)
    for p, (_saved_name, active_name) in snap.eq_preset_name.items():
        device.set_eq_preset_name(p, active_name)
    for p, gain in snap.eq_preset_gain.items():
        device.set_eq_preset_gain(p, gain.gain)
    for (p, b), fb in snap.eq_preset_freq_and_bw.items():
        device.set_eq_preset_freq_and_bw(p, b, fb.center_freq, fb.bandwidth)


@pytest.fixture(name="device", scope="session")
def _device() -> Generator[Device, None, None]:
    with Device() as device:
        yield device


@pytest.fixture(scope="session", autouse=True)
def _backup_and_restore(device: Device) -> Generator[None, None, None]:
    snapshot = _capture(device)
    yield
    _apply_saved(device, snapshot)
    device.save_values()
    _apply_active(device, snapshot)
