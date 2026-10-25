# Changelog

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
