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
* [X] get/set microphone EQ preset
* [X] get/set side tone volume
* [X] get/set noise gate mode
* [X] get/set alert volume
* [X] get/set active EQ preset
* [X] get/set EQ preset parameters
* [X] get/set game/voice balance
* [X] save configuration values
* [X] get charging status and battery level
* [X] get headset status
* [X] get EQ preset name
* [ ] update firmware

## Example

Retrieve the current battery charge:

    from eh_fifty import Device

    with Device() as device:
        battery_status = device.get_battery_status()
        print(f"Battery: {battery_status.charge_percent}%")

## Resource Management

The `Device` class supports context management for automatic cleanup:

    with Device() as device:
        # use device...
    # kernel driver automatically reattached

For long-running applications, you can also manage the lifecycle manually:

    device = Device()
    try:
        while True:
            status = device.get_headset_status()
            # ...
    finally:
        device.close()

## Non-root access

Create a udev rule to allow non-root users to access the USB device:

    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="9886", ATTR{idProduct}=="002c", MODE:="0666"' | \
        sudo tee /etc/udev/rules.d/50-astro-a50.rules

Re-plug your base station to apply the new rule.

## Protocol Documentation

### Requests

The first byte of a request is `0x02`.

The second byte of a request is a request type (see below).

An optional request payload may follow, prefixed by the length of the payload
in bytes, not including this byte.

### Responses

The first byte of a response is `0x02`.

The second byte of a response may be either:

* `0x00` for "no response"
* `0x01` for "error"
* `0x02` for "success"

Unless the second byte represents "no response", the third byte of a response
is the remaining length of the response measured in bytes, not including this
byte.

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
0x63 | set EQ preset gain
0x64 | set noise gate mode
...  |
0x67 | set active EQ preset
0x68 | get value of specified slider
0x69 | get EQ preset gain
0x6A | get noise gate mode
...  |
0x6C | get active EQ preset
0x6D | set EQ preset name
0x6E | get EQ preset name
0x6F | set EQ preset frequency and bandwidth
0x70 | get EQ preset frequency and bandwidth
0x71 | set microphone EQ preset
0x72 | get balance
0x73 | set default balance
0x74 | set auto shutoff timeout (ineffective)
0x75 | set brightness (ineffective)
0x76 | set alert volume
0x77 | get default balance
0x78 | get auto shutoff timeout
0x79 | get brightness
0x7A | get alert volume
0x7B | get microphone EQ preset
0x7C | get battery status
...  |
0x83 | unknown (returns "slave timeout" error)
...  |
0xDA | unknown
...  |
0xD6 | unknown
