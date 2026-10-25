# SafeFord 0.1.0 — First installable build

A native Home Assistant integration for FordConnect Query, intended for a **2025 Ford Maverick** and other supported Ford vehicles. It reads vehicle data only, through Ford's consent-based OAuth2 data API. It NEVER sends vehicle wake, remote start/stop, lock, or unlock commands in 0.1.0.

## Implemented

- Ford Developer OAuth 2.0 connection through Home Assistant Application Credentials and Ford consent.
- Native Home Assistant sensor, binary sensor, and GPS device tracker entities; cached after restart.
- Fuel %, range, odometer, oil life, 12V battery, per-wheel tire PSI, ignition, speed, RPM, gear, door state, hood, tailgate, lock state, temperatures, GPS, and timestamps, **only where returned by Ford**.
- Fixed 15-minute minimum / 60-minute default cloud query spacing. No vehicle status-refresh requests or wake-ups.
- Persist request reservation **before** each HTTP call. 429 response causes >=1h cooldown, 401/403 permanently suspends automatic queries, temporary errors defer >=30m.
- Diagnostic counters with no VIN, GPS coordinates, Ford API payloads, OAuth secrets, or personal addresses.
- Location always last-known; cloud query frequency is not GPS frequency. No 10–30-second GPS guarantee from Ford.

## Not yet implemented

- Remote lock/unlock is **not available in this build**. Agreed default-on command controls require a separately verified and isolated FordPass command provider. FordConnect Query itself is officially read-only. A fake or nonworking lock entity is deliberately not created.
- Remote engine start/stop is intentionally absent. Future engine actions must never be exposed to HA scripts, services, automations, voice assistants, or webhook actions, and require a separately authenticated, manually confirmed interface with indoor/CO safety gating.
- True live location at 10–30 seconds needs independent GPS hardware or a companion app if Ford cloud reports less frequently.
- Ford consent, real vehicle responses, and Home Assistant runtime startup are **not verified** in this offline build environment.

## Before installing: register with Ford

1. Set up your vehicle in the **official FordPass app** with its modem activated.
2. Register a Ford Developer account at https://developer.ford.com/developer-na . Create a FordConnect Query app in the North America region, with appropriate owner-approved read scopes.
3. Enter `https://my.home-assistant.io/redirect/oauth` as Ford's OAuth redirect URI. Ford's current OAuth flow restricts state length, so SafeFord uses a Ford-specific short-state authorization adapter.
4. Keep the Ford client ID and secret private. They are entered in Home Assistant's Application Credentials dialog, not in YAML or the release package.
5. Ford app registration may take time to activate. Official API access or particular metrics are subject to Ford's authorization rules and vehicle capabilities.

Reference setup walkthrough: https://github.com/marq24/ha-fordconnect-query/blob/main/docs/REGISTER_APPLICATION.md . SafeFord is independently implemented; that project is referenced for the Ford registration details, not installed as a dependency.

## Install from GitHub

The source of truth is [gigabytegrove/ha-safeford](https://github.com/gigabytegrove/ha-safeford). For HACS, add `https://github.com/gigabytegrove/ha-safeford` as a custom **Integration** repository, install SafeFord, and restart Home Assistant. Because the repository is currently private, your HACS GitHub account must have access.

For a Docker host with Git access, clone the repository on the host (using an appropriately scoped GitHub credential for this private repo), then run:

```bash
cd ha-safeford
sudo bash install-on-dockeradm.sh --restart
```

The installer will refuse to overwrite an existing SafeFord directory. You can also use the packaged ZIP.

## Install — on dockeradm (Docker host, not HA container)

Transfer and unzip `SafeFord-0.1.0.zip` to a directory on dockeradm, then run from that directory:

```bash
unzip SafeFord-0.1.0.zip -d safeford-0.1.0
cd safeford-0.1.0
sudo bash install-on-dockeradm.sh --restart
```

Default Home Assistant container name is `homeassistant`. If yours differs: `sudo HA_CONTAINER=my-container bash install-on-dockeradm.sh --restart`. The installer **requires persistent /config Docker bind/volume**, avoids touching existing SafeFord installs, and does not restart HA unless `--restart` is used.

Home Assistant: **Settings → Devices & services → Add integration → SafeFord**. Register the Ford Application Credentials when prompted (client ID/secret from Ford), approve access to one vehicle in the browser, and complete the `my.home-assistant.io` callback. Ensure the HA instance URL on the intermediary page points to your actual reachable HA URL. SafeFord does not require HTTPS for the HA LAN URL if Ford's redirect is the HTTPS intermediary URL.

Configure query interval via integration **Configure**. Default is 60 minutes; no override below 15 minutes, because Ford does not publish a universal safe polling frequency for the integration. This is cloud cache polling, not a vehicle-wake command.

### Operational safety

- FordPass itself and any other third-party Ford integrations may make additional account requests not controlled by SafeFord. Disable the old polling integration while evaluating SafeFord.
- Ford lockouts are still possible; separate owner-authorized Ford accounts are recommended for unofficial methods, but cannot guarantee prevention.
- A door status or GPS location can be stale. Never use it as proof a door is currently secure or the vehicle is currently parked.
- Telemetry cache includes location inside HA's persistent `.storage`; keep host and backups secured.
- The present OAuth short-state callback adapter narrowly wraps HA's internal OAuth decoder for Ford callbacks; upstream HA refactors can break it. It never blindly disables verification of unrelated OAuth states.

## Development / verification

```bash
python3 -m compileall -q custom_components/safeford
python3 -m pytest -q tests
bash -n install-on-dockeradm.sh
```

The offline unit tests verify representative Ford payload parsing and rate-limit behavior. Real API integration requires testing with your own Ford developer authorization and Maverick.
