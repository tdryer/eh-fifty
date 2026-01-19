#!/usr/bin/env python3
"""Comprehensive test of eh_fifty library with verbose output."""

from eh_fifty import (
    Device,
    NoiseGateMode,
    SliderType,
)


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)


def test(name: str, func, *args, **kwargs):
    """Run a test and print result."""
    try:
        result = func(*args, **kwargs)
        print(f"  [PASS] {name}: {result}")
        return result
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        return None


def main():
    section("CONTEXT MANAGER TEST")
    print("Opening device with context manager...")

    with Device() as device:
        print(f"  Device opened successfully")
        print(f"  Singleton ref_count: {Device._ref_count}")

        # -- Status --
        section("DEVICE STATUS")
        battery = test("get_battery_status", device.get_battery_status)
        if battery:
            print(f"       -> charge_percent: {battery.charge_percent}%")
            print(f"       -> is_charging: {battery.is_charging}")

        headset = test("get_headset_status", device.get_headset_status)
        if headset:
            print(f"       -> is_on: {headset.is_on}")
            print(f"       -> is_docked: {headset.is_docked}")

        # -- EQ Presets --
        section("EQ PRESETS")
        active_preset = test("get_active_eq_preset", device.get_active_eq_preset)

        for preset in [1, 2, 3]:
            name = test(f"get_eq_preset_name(preset={preset})",
                       device.get_eq_preset_name, preset)
            gain = test(f"get_eq_preset_gain(preset={preset})",
                       device.get_eq_preset_gain, preset)
            if gain:
                print(f"       -> gain: {gain.gain}")
                print(f"       -> saved_gain: {gain.saved_gain}")

            for band in [1, 2, 3, 4, 5]:
                freq_bw = test(f"get_eq_preset_freq_and_bw(preset={preset}, band={band})",
                              device.get_eq_preset_freq_and_bw, preset, band)
                if freq_bw:
                    print(f"       -> center_freq: {freq_bw.center_freq}, bandwidth: {freq_bw.bandwidth}")

        # -- Balance --
        section("BALANCE")
        test("get_balance", device.get_balance)
        test("get_default_balance", device.get_default_balance)
        test("get_default_balance(saved=True)", device.get_default_balance, saved=True)

        # -- Audio Settings --
        section("AUDIO SETTINGS")
        test("get_alert_volume", device.get_alert_volume)
        test("get_alert_volume(saved=True)", device.get_alert_volume, saved=True)
        test("get_noise_gate_mode", device.get_noise_gate_mode)
        test("get_noise_gate_mode(saved=True)", device.get_noise_gate_mode, saved=True)
        test("get_mic_eq", device.get_mic_eq)
        test("get_mic_eq(saved=True)", device.get_mic_eq, saved=True)

        # -- Sliders --
        section("SLIDERS")
        for slider_type in SliderType:
            val = test(f"get_slider_value({slider_type.name})",
                      device.get_slider_value, slider_type)
            saved_val = test(f"get_slider_value({slider_type.name}, saved=True)",
                            device.get_slider_value, slider_type, saved=True)

        # -- Singleton Test --
        section("SINGLETON BEHAVIOR")
        print(f"  Current ref_count: {Device._ref_count}")
        dev2 = Device()
        print(f"  After Device(): ref_count = {Device._ref_count}")
        print(f"  Same instance: {device is dev2}")
        dev2.close()
        print(f"  After dev2.close(): ref_count = {Device._ref_count}")

    section("CONTEXT MANAGER EXIT")
    print(f"  ref_count after exit: {Device._ref_count}")
    print(f"  device._dev is None: {device._dev is None}")

    section("RE-OPEN AFTER CLOSE")
    with Device() as device:
        battery = test("get_battery_status", device.get_battery_status)
        if battery:
            print(f"       -> charge_percent: {battery.charge_percent}%")

    print()
    print("=" * 60)
    print(" ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
