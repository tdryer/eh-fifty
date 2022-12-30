# eh-fifty

eh-fifty is a Python library for configuring the [Astro A50 wireless headset
and base station (generation 4)][astro-a50].

**Use at your own risk.** eh-fifty was developed using reverse engineering. If
you get into trouble, re-plug your base station and reset your headset by
holding down the "game" and "Dolby" buttons together for 15 seconds.

eh-fifty has only been tested on Linux, although it may work on other platforms
supported by [PyUSB][pyusb].

[astro-a50]: https://www.astrogaming.com/en-ca/products/headsets/a50-gen-4.html
[pyusb]: https://github.com/pyusb/pyusb

## Features

* [X] get/set microphone level
* [X] get/set side tone volume
* [X] get/set noise gate mode
* [X] get/set alert volume
* [X] get/set active EQ preset
* [X] get/set game/voice balance
* [X] save configuration values
* [X] get charging status and battery level
* [X] get headset status
* [X] get EQ preset name
* [ ] modify EQ presets
* [ ] update firmware
* [ ] get/set volume (may not be possible)
* [ ] get/set Dolby status (may not be possible)

## Example

Retrieve the current battery change:

    from eh_fifty import Device
    device = Device()
    charge_status = device.get_charge_status()
    print(f"Battery: {charge_status.charge_percent}%")

## Non-root access

Create a udev rule to allow non-root users to access the USB device:

    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="9886", ATTR{idProduct}=="002c", MODE="0666"' | \
        sudo tee /etc/udev/rules.d/50-astro-a50.rules

Re-plug your base station to apply the new rule.

## Protocol Documentation

### Requests

The first byte of a request is `0x02`.

The second byte of a request is a request type (see below).

A variable number of request arguments may follow.

### Responses

The first byte of a response is `0x02`.

The second byte of a response is `0x02` for "success" or `0x01` for "error".

The third byte of a response is the remaining length of the response measured
in bytes, not including this byte.

### Saved Values

Sending request type `0x61` will save the active configuration. Saved values
can be queried separately from active values. This can be used by applications
to implement an operation to revert to a saved configuration. Changes to the
active configuration effect immediately; saving changes is not required.

### Request Types

Type | Description
-----|----------------------------------------------------------------------
0x03 | unknown
...  |
0x54 | returns headset power and dock status
0x55 | unknown
...  |
0x61 | save active values
0x62 | set value of specified slider
...  |
0x64 | set noise gate mode
...  |
0x67 | set active EQ preset
0x68 | get value of specified slider
0x69 | unknown (related to EQ presets?)
0x6A | get noise gate mode
...  |
0x6C | get active EQ preset
...  |
0x6E | get specified EQ preset name
...  |
0x70 | unknown (related to EQ presets?)
...  |
0x72 | get game/chat balance (duplicate)
0x73 | set game/chat balance
...  |
0x76 | set alert volume
0x77 | get game/chat balance
...  |
0x7A | get alert volume
...  |
0x7C | get battery change level and charging status
...  |
0x83 | unknown (returns "slave timeout" error)
...  |
0xDA | unknown
...  |
0xD6 | unknown
