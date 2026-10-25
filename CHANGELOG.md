# Changelog

## 0.2.0-alpha.5 — 2026-10-25

GPS: Expose GPS latitude and longitude as standalone numerical Home Assistant sensors, plus a locally refreshed GPS sample-age sensor (minutes). Keep the existing last-known GPS device tracker and GPS report timestamp sensor.

GPS RELIABILITY: Select the most recent valid Ford position record when multiple records are supplied, and do not replace a newer GPS fix with an older or undated cloud response. GPS freshness refers to the position's report timestamp, never the HTTP request time.

DIAGNOSTICS: Show whether coordinates exist and their position report age without exporting coordinates. Tracker attributes indicate stale GPS after five minutes; they do NOT imply live tracking. No vehicle wake/force-refresh is introduced.

TESTS: Synthetic coordinates only, no identifying vehicle data in commits. Add GPS freshness, monotonic cache, parsing, entity-surface and privacy regression tests.


## 0.2.0-alpha.4 — 2026-10-25

PERFORMANCE: Replace the arbitrary hourly Ford telemetry GET default and 15-minute minimum with a real cloud query every minute by default. Owner-configurable interval is now 1–1440 minutes. The local timer already runs each minute, while a persisted request budget ensures real cloud requests stay at or above the selected cadence across restarts.

SAFETY: Continue obeying explicit slower owner preferences, prior persisted cooldown deadlines, Ford 429 Retry-After (at least one-hour backoff), auth denial and transient failure backoff. No 10-second cloud polling, vehicle wake, or false guarantees about per-door sampling freshness.

TESTS: Add one-minute persistent request-budget and slower owner interval tests; update metadata and install verification.


## 0.2.0-alpha.3 — 2026-10-25

FIX: Run a lightweight local request-budget check every minute so Home Assistant reloads/cache republishing no longer delay eligible Ford cloud queries by a full new update interval. This does NOT reduce the Ford API request interval; durable 60-minute default cooldown, 15-minute configurable minimum, and backoff still apply.

DIAGNOSTICS: Correct version string and report whether the existing cloud request budget currently permits a request. Preserve sanitized telemetry-schema capture.


## 0.2.0-alpha.2 — 2026-10-25

DIAGNOSTICS: Capture a narrow, privacy-filtered schema and security-status/timestamp sample from each already-scheduled FordConnect telemetry response. Enables real-world testing against the vehicle without saving or distributing raw customer API responses.

FIX: Older Ford vehicle snapshots no longer present doors/hood/tailgate or lock state as current. After 60 minutes from the vehicle metric's report time, these entities become unavailable, rather than presenting old Open or Unlocked values without warning.

FIX: Extract per-door, hood, and lock sample timestamps when supplied, and prefer newer door reports when duplicate records exist. Historical caches use the vehicle-wide report timestamp when no metric timestamp exists.

SAFETY: One-minute local freshness checks do not make Ford network requests, reset cloud request cooldowns, or send vehicle commands. Expose sample-time attributes without leaking VIN, location or authentication.

LIMITATION: This does not make Ford's official Query API live. Whether FordPass mobile presents newer backend state via a different channel needs separate verification.


## 0.2.0-alpha.1 — 2026-10-25

FIX: Explicitly republish previously cached telemetry to the newly subscribed Home Assistant entities after their platforms finish setup. This local state synchronization does not contact Ford or reset account lockout protections.

DIAGNOSTICS: Log the count of restored telemetry fields (not their values, VINs or GPS) at debug level. No credentials, telemetry values or personally identifiable information are written to source.

LIMITATION: The exact cause of blank GUI states is not yet verified against a running Home Assistant instance. This is a safe cache-state synchronization correction, not a claim that every displayed entity has been fixed.


## 0.2.0-alpha — 2026-10-25

BREAKING CHANGE: The Home Assistant integration name is now SafeConnect and domain is `safeconnect` (previously a different domain). Moving from the old domain requires an explicit HA integration migration, not simply a GitHub rename.

SECURITY: No user secrets or personal vehicle details in source; each HA instance uses its own owner-authorized OAuth credentials, and no central service receives authentication or telemetry. Confidential developer app secrets are never bundled.

MIGRATION: New `migrate-on-dockeradm.sh` stages and backs up the old integration files, and blocks if Home Assistant retains an active config entry for the old domain; it does not edit Home Assistant storage behind HA's back.


## 0.1.1 — 2026-10-25

FIX: OAuth config flow now declares the required `DOMAIN` class attribute; Home Assistant's OAuth flow handler rejected the prior class with TypeError, consistent with the 500 config-flow error.

NEW: Stage-and-backup updater for existing Docker installations, preserving Home Assistant config entries, credentials and cache. Add a config-flow contract regression test and upgrade tests.

VERIFICATION: Offline tests; no live Ford account or actual Home Assistant container was accessible.


## 0.1.0 — 2026-10-25

NEW: Independent FordConnect read-only API client, single-vehicle OAuth setup, HA entities, defensive parser, API rate-budget persistence, diagnostics, Docker-host installer and offline tests.

SECURITY: No remote engine/lock command paths; credentials managed by HA; no Ford raw payloads in diagnostics; 401/403 suspension; 429 cooldown; GPS is labeled last-known.

KNOWN LIMITATIONS: Real Ford OAuth and Home Assistant runtime were not available for integration verification. Lock/unlock and high-frequency GPS are not yet implemented.
