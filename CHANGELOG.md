# Changelog

## 0.1.0 — 2026-10-25

NEW: Independent FordConnect read-only API client, single-vehicle OAuth setup, HA entities, defensive parser, API rate-budget persistence, diagnostics, Docker-host installer and offline tests.

SECURITY: No remote engine/lock command paths; credentials managed by HA; no Ford raw payloads in diagnostics; 401/403 suspension; 429 cooldown; GPS is labeled last-known.

KNOWN LIMITATIONS: Real Ford OAuth and Home Assistant runtime were not available for integration verification. Lock/unlock and high-frequency GPS are not yet implemented.
