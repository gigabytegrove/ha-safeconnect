# SafeConnect — Home Assistant integration (v0.2.0 alpha.3)

A native Home Assistant integration for FordConnect Query, intended for supported connected Ford vehicles. It reads vehicle data only, through Ford's consent-based OAuth2 data API. It NEVER sends vehicle wake, remote start/stop, lock, or unlock commands in 0.2.0 alpha.

## SafeConnect official Postman reference and field validation

The owner-supplied FordConnect 2.0 Postman collection describes OAuth token exchange with `POST` and read-only `GET /fcon-query/v1/telemetry` and `GET /fcon-query/v1/garage`. A telemetry `GET` is **not** a command to wake or refresh the vehicle.

After the next normal rate-limited telemetry request, the local Home Assistant Diagnostics download contains `telemetry_schema`: a tightly allowlisted summary of door/lock/hood status records and their actual vehicle timestamps, plus metric field names. It never records raw JSON, VIN, GPS coordinates, account tokens, correlation identifiers, or opaque response metadata.

To investigate a specific vehicle, use that vehicle's own HA installation for diagnostics. **Do not commit real vehicle captures or tokens to this public repo**.

## Cloud polling reliability

SafeConnect checks the LOCAL persisted API request budget every minute, which sends **no Ford API request** until the budget permits one. This prevents HA restarts and cached-state replays from pushing an eligible cloud GET another hour into the future. Cloud pacing remains 60 minutes by default (minimum 15 minutes configurable), with a longer backoff on rate limits and errors. A GET cannot force a vehicle wake or guarantee a recent vehicle report.

Diagnostics distinguishes `local_budget_check_minutes`, `poll_minutes` (the cloud API budget), and `cloud_query_permitted_now`.

## Security telemetry freshness

Door-open, hood, tailgate and door-lock entities are shown as **unavailable** whenever their individual Ford metric's report timestamp is more than 60 minutes old, is invalid, or was never supplied. Older cached data uses the vehicle-wide report timestamp as a conservative fallback. A recent cloud query is **not evidence of current vehicle state**. The integration's one-minute local timer expires these readings without contacting Ford. Each security entity has `security_sample_time` and `security_state_fresh` attributes.

This is a read-only official FordConnect Query integration. It cannot request a vehicle wake or claim real-time WebSocket behavior using this API. Do not use a stale lock sensor as proof that a vehicle is secured. Updated data arrives only when Ford's official query endpoint supplies it.

## Current field-test status

The official cloud authorization and one telemetry read have been verified in a Home Assistant installation. A local cache held non-empty values for supported fields, while the entity interface appeared empty. The alpha.1 change rebroadcasts locally restored data after entity setup, without making extra Ford API requests. Live UI confirmation is still required.

For a previous `safeconnect` installation, pull this repository and run `update-on-dockeradm.sh --restart`; do not register another Ford application or reauthorize just for an update.

**HACS note:** If HACS reports a 404 for an archive URL containing a short Git commit under `archive/refs/heads/`, that is a HACS archive-reference issue, separate from the telemetry cache. Use the reviewed Docker-host updater until HACS release behavior has been verified.

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
3. Enter `https://my.home-assistant.io/redirect/oauth` as Ford's OAuth redirect URI. Ford's current OAuth flow restricts state length, so SafeConnect uses a Ford-specific short-state authorization adapter.
4. Keep the Ford client ID and secret private. They are entered in Home Assistant's Application Credentials dialog, not in YAML or the release package.
5. Ford app registration may take time to activate. Official API access or particular metrics are subject to Ford's authorization rules and vehicle capabilities.

Reference setup walkthrough: https://github.com/marq24/ha-fordconnect-query/blob/main/docs/REGISTER_APPLICATION.md . SafeConnect is independently implemented; that project is referenced for the Ford registration details, not installed as a dependency.

## Existing installation: integration identity migration

**The integration domain has changed to `safeconnect`.** Simply renaming the GitHub repository does not rename the existing Home Assistant integration. To keep one clean installation, remove the old integration entry through Home Assistant **Settings → Devices & services** (if configured). Then run `bash migrate-on-dockeradm.sh --restart` on the Docker host from this Git checkout. This script backs up the previous Python integration directory before installing the new one, and refuses to rewrite Home Assistant's internal configuration entries automatically. OAuth application credentials may need to be entered again for the new domain. Any previously acquired Ford consent is not transferred to the new integration automatically.

For a first-time installation with no prior integration directory, use `install-on-dockeradm.sh` instead.

## Install from GitHub

The source of truth is [gigabytegrove/ha-safeconnect](https://github.com/gigabytegrove/ha-safeconnect). **Public repository:** SafeConnect's source is publicly available on GitHub. Inclusion in the default HACS catalogue has not been submitted or verified. The included `hacs.json` supports future distribution; it does not establish HACS approval.

For a Docker host with Git access, clone the repository on the host (using an appropriately scoped GitHub credential for this private repo), then run:

```bash
cd ha-safeconnect
sudo bash install-on-dockeradm.sh --restart
```

The installer will refuse to overwrite an existing SafeConnect directory. You can also use the packaged ZIP.

## Upgrade an existing SafeConnect installation

From the existing Git checkout on your Docker host, update the repository and run the **updater** (not the first-time installer):

```bash
cd ha-safeconnect
git pull --ff-only
sudo bash update-on-dockeradm.sh --restart
```

The updater requires the already-installed /config/custom_components/safeconnect directory and a persistent /config mount. It stages the replacement, saves the previous files under /config/.safeconnect-backups/, then swaps the directories. It preserves HA config entries, OAuth credentials and telemetry cache. It never issues vehicle commands. The HA container restarts only if --restart was explicitly supplied.

## Install — on dockeradm (Docker host, not HA container)

Transfer and unzip `SafeConnect-0.2.0-alpha.zip` to a directory on dockeradm, then run from that directory:

```bash
unzip SafeConnect-0.2.0-alpha.zip -d safeconnect-0.2.0-alpha
cd safeconnect-0.2.0-alpha
sudo bash install-on-dockeradm.sh --restart
```

Default Home Assistant container name is `homeassistant`. If yours differs: `sudo HA_CONTAINER=my-container bash install-on-dockeradm.sh --restart`. The installer **requires persistent /config Docker bind/volume**, refuses existing SafeConnect installs (use update-on-dockeradm.sh instead), and does not restart HA unless `--restart` is used.

Home Assistant: **Settings → Devices & services → Add integration → SafeConnect**. Register the Ford Application Credentials when prompted (client ID/secret from Ford), approve access to one vehicle in the browser, and complete the `my.home-assistant.io` callback. Ensure the HA instance URL on the intermediary page points to your actual reachable HA URL. SafeConnect does not require HTTPS for the HA LAN URL if Ford's redirect is the HTTPS intermediary URL.

Configure query interval via integration **Configure**. Default is 60 minutes; no override below 15 minutes, because Ford does not publish a universal safe polling frequency for the integration. This is cloud cache polling, not a vehicle-wake command.

### Operational safety

- FordPass itself and any other third-party Ford integrations may make additional account requests not controlled by SafeConnect. Disable the old polling integration while evaluating SafeConnect.
- Ford lockouts are still possible; separate owner-authorized Ford accounts are recommended for unofficial methods, but cannot guarantee prevention.
- A door status or GPS location can be stale. Never use it as proof a door is currently secure or the vehicle is currently parked.
- Telemetry cache includes location inside HA's persistent `.storage`; keep host and backups secured.
- The present OAuth short-state callback adapter narrowly wraps HA's internal OAuth decoder for Ford callbacks; upstream HA refactors can break it. It never blindly disables verification of unrelated OAuth states.

## Development / verification

```bash
python3 -m compileall -q custom_components/safeconnect
python3 -m pytest -q tests
bash -n install-on-dockeradm.sh
bash -n update-on-dockeradm.sh
bash -n migrate-on-dockeradm.sh
```

The offline unit tests verify representative Ford payload parsing and rate-limit behavior. Real API integration requires testing with your own Ford developer authorization and a compatible test vehicle.
