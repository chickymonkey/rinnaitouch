# Rinnai/Brivis Touch Wifi – Heater Only

![Pylint](https://github.com/chickymonkey/rinnaitouch/workflows/Pylint/badge.svg)

A Home Assistant custom integration for a **single-zone Rinnai/Brivis gas heater** controlled through an **N-BW2 Networker Bridge (WiFi)**.

This is a slimmed-down fork of [funtastix/rinnaitouch](https://github.com/funtastix/rinnaitouch). Cooling (add-on), evaporative cooling and zone support have been removed so that the integration only covers what a heater-only system needs. It also uses a patched copy of the `pyrinnaitouch` library that fixes control being lost after the integration has been running for a while.

If you have cooling, evaporative cooling or zones, use the [original integration](https://github.com/funtastix/rinnaitouch) instead.

## Authors

- **chickymonkey** – maintainer of this heater-only fork and of the patched [pyrinnaitouch fork](https://github.com/chickymonkey/pyrinnaitouch)
- **[funtastix](https://github.com/funtastix)** – original author of [rinnaitouch](https://github.com/funtastix/rinnaitouch) and [pyrinnaitouch](https://github.com/funtastix/pyrinnaitouch)

The original work was inspired by [MyTouch](https://github.com/christhehoff/MyTouch), [@C-Westin](https://github.com/C-Westin/rinnai_touch_climate) and [@jerryzou](https://github.com/jerryzou/rinnai_touch_climate). Thanks to all of them for the groundwork.

## What's different from the original

| Area | Change |
|---|---|
| Modes | Heating only. Cooling, evaporative cooling and all zone entities are removed. |
| Setup form | Asks only for host, name and an optional external temperature sensor. No zone questions. |
| Entities | Removed the cooling, evap, zone, heater mode, gas valve active and time setting entities. |
| Fan speed | Fan only speed is limited to 1–16, as the N-BW2 API specifies. |
| Dependency | Uses the patched [chickymonkey/pyrinnaitouch](https://github.com/chickymonkey/pyrinnaitouch) instead of `pyrinnaitouch==0.13.4b1` from PyPI. See [Dependency](#dependency). |

Existing heater entities keep the same unique IDs, so their history carries over if you switch from the original integration.

## Entities

| Platform | Entity | Purpose |
|---|---|---|
| Climate | *Name* | Off / Heat / Fan only, target temperature (8–30 °C), Auto (schedule) or Manual preset. In Fan only, the target value sets the fan speed (1–16). |
| Switch | On Off Switch | Turns the heater on or off. |
| Switch | Auto Switch | On = follow the schedule, off = manual. |
| Switch | Circulation Fan Switch | Runs the circulation fan while the heater is off. |
| Select | Preset Select | Auto or Manual (same as the Auto switch). |
| Button | Advance Button | Advances to, or cancels advancing to, the next schedule period. Available in Auto mode. |
| Binary sensor | Connected Sensor | Whether the TCP connection to the bridge is up. |
| Binary sensor | Preheating Sensor | The heater is pre-heating. |
| Binary sensor | Calling Heat Sensor | The system is calling for heat. |
| Binary sensor | Fan Active Sensor | The fan is running. |
| Sensor | Main Temperature Sensor | Measured temperature, when the controller reports one. |
| Sensor | Main Target Temperature Sensor | Current set point. |
| Sensor | Schedule Time Period Sensor | Current schedule period (Wake, Leave, Return, Pre-Sleep, Sleep). |
| Sensor | Advance Time Period Sensor | The period the schedule has been advanced to. |
| Sensor | Connection State | Raw connection state: `CONNECTED`, `CONNECTING`, `TIMEOUT`, `REFUSED`, `ERROR` or `IDLE`. |

There is also a `rinnaitouch.rinnai_set_time` service that sets the controller's clock, from Home Assistant's time or from a given date and time.

## How it works

The integration talks to the N-BW2 bridge over your local network, using the protocol in the [N-BW2 API manual](doc/NBW2API_Iss1.3.pdf). No cloud service is involved.

1. **Discovery.** The bridge broadcasts a UDP packet on port 50000 every second. The library waits for a broadcast from the configured IP address. If none arrives within 30 seconds, it connects directly.
2. **Connection.** The library opens a TCP connection to the bridge on port 27847, and the bridge replies with `*HELLO*`.
3. **Status.** The bridge then pushes its full status as JSON about once a second. Home Assistant doesn't poll; it updates the entities whenever a status arrives.
4. **Commands.** Each command is sent with a sequence number from 0 to 255. The bridge echoes that number in its next status, which confirms the command was received. The library sends one command at a time and waits up to 5 seconds for the echo.
5. **Keepalive.** If no command has been sent for 10 seconds, the library sends a small idle command. Without it, the bridge drops the client after its TCP timeout (5 minutes by default) and reboots.
6. **Recovery.** The library reconnects automatically if the bridge closes the connection, if nothing has been received for 30 seconds, or if garbled data arrives.

The bridge only supports one client at a time. If the Rinnai/Brivis phone app is connected at the same time as Home Assistant, expect dropouts.

## Dependency

This integration depends on the library [pyrinnaitouch](https://github.com/chickymonkey/pyrinnaitouch), installed from the `connection-fixes` branch of the fork and pinned to an exact commit. Home Assistant installs it automatically from the GitHub archive listed in [manifest.json](custom_components/rinnaitouch/manifest.json):

```
https://github.com/chickymonkey/pyrinnaitouch/archive/eb8f33dff9b1fb438d6ed437d08b832f1fbf5739.zip#pyrinnaitouch==0.13.4b1.post1
```

The fork is based on `pyrinnaitouch` 0.13.4b1 and is versioned `0.13.4b1.post1`, so Home Assistant replaces an already installed 0.13.4b1. It fixes the following:

- **Connection thread stopping silently.** An unexpected error, such as a byte that isn't valid UTF-8 arriving from the bridge, used to stop the background connection thread for good. Status then froze, commands were never sent and no reconnect was attempted, while the integration still showed as connected. The thread now logs the error and reconnects.
- **Data parsing.** Incoming data is parsed as raw bytes, and recovery from garbled data now works instead of always forcing a reconnect.
- **Replayed commands.** Commands queued while disconnected are discarded on reconnect instead of being sent in a burst minutes later.
- **Reconnect fallback.** The library now always falls back to a direct connection after 30 seconds, even if other traffic arrives on the broadcast port.
- **Sequence numbers.** They now wrap at 255, as the API specifies, and command confirmation stays correct across the wrap.
- **Smaller fixes.** Partial sends are retried straight away, a spurious "hello received more than once" error no longer appears on every reconnect, and a failing callback can no longer stop status updates.

## Installation

### HACS (recommended)

1. In HACS, open **⋮ → Custom repositories**, add `https://github.com/chickymonkey/rinnaitouch` and choose the **Integration** type.
2. Download **Rinnai Touch**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add Integration** and search for **Rinnai Touch**.
5. Enter:
   - **Hostname or IP** – the bridge's IP address. Give it a fixed IP or a DHCP reservation.
   - **Name** – for example `Rinnai Touch`.
   - **External temperature sensor** (optional) – the entity ID of a temperature sensor to show as the current temperature. Use this if your controller doesn't report one: the climate entity shows 0 °C when the controller reports none and no external sensor is set.

### Switching from the original integration

1. Remove the existing Rinnai Touch entry under **Settings → Devices & services**.
2. Install this fork through HACS as above and restart Home Assistant.
3. Add the integration again.
4. Delete any leftover zone or cooling entities that show as unavailable.

If the setup form still asks about zones, the old code is still installed, or your browser is showing a cached copy of the old form. Redownload the integration in HACS, restart Home Assistant and force-refresh the browser.

### Manual installation

Copy `custom_components/rinnaitouch` into the `custom_components` folder of your Home Assistant configuration directory, restart Home Assistant and add the integration as above.

## Troubleshooting

To enable debug logging, add this to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.rinnaitouch: debug
    pyrinnaitouch: debug
```

What to look for in the log:

| Log message | Meaning |
|---|---|
| `Sending idle command N` followed by `Received sequence number N` and `Command wait end` | Normal keepalive, about every 10 seconds. |
| `Unexpected error in connection thread, reconnecting` | An error the library recovered from. The traceback that follows shows the cause. |
| `Discarded N command(s) queued while disconnected` | The connection dropped and recovered, and commands sent during the outage were dropped. |
| `Resetting connection as no data received for at least 30 seconds` | The bridge went quiet. Check its WiFi signal, and whether another app is connected. |
| `No UDP broadcast received from … attempting TCP connection directly` | No broadcast was seen, so the library is connecting directly. This is normal if broadcasts don't reach Home Assistant (for example in a Docker container without host networking). |

The bridge's WIFI LED also helps. Solid orange means it lost your router for 3 minutes and is about to fall back to its own access point (see the [manual](doc/NBW2API_Iss1.3.pdf), section 2.5).

## License

MIT. See [LICENSE](LICENSE). Original copyright © 2022 funtastix.
