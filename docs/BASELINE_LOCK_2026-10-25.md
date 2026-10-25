# SafeFord — Engineering Baseline Lock (2026-10-25)

**Status:** Paused at v0.1.1. Resume only on explicit instruction; no unattended work, alerts, or releases are scheduled.

**Public repository:** https://github.com/gigabytegrove/ha-safeford
**Locked code revision:** `a13c60db0c211801497d0f4ef267449e267eae43` (v0.1.1). This checkpoint commits documentation and sanitized fixtures only; it does not alter integration runtime code.

## Purpose and functional scope

SafeFord is a native, publicly distributable Home Assistant integration for consented connected Ford vehicles, prioritizing account protection over polling frequency. Requirements apply across supported vehicle models and must be capability-driven, not tailored to a specific owner or car.

Expose Ford-supplied location, fuel/range, ignition, activity, each tire's pressure, oil life, odometer, doors/hood/tailgate, lock state, and available additional telemetry. Missing or outdated data must never be fabricated or represented as current. Report actual vehicle sample time separately from Home Assistant receipt time. "Engine off" must not be assumed to mean "parked" without supporting evidence.

The desired 10–30-second location refresh is permitted **only when a source actually supplies new coordinates that often**. It must not become 10–30-second Ford cloud polling or automatic vehicle wake-ups. An independently authorized location provider is a possible future alternative.

## Account and API protections

- Prefer FordConnect Query for read-only telemetry and owner-authorized OAuth access.
- Default Ford cloud polling is 60 minutes, with a 15-minute configured floor in v0.1.1. Those values do not imply Ford guarantees their safety.
- Persist cached telemetry and per-account request budgets across restarts; no uncontrolled retries or unnecessary vehicle wake commands.
- Honor Ford rate limits, Retry-After, lockouts, and denied authorization. Avoid unsupported access or mechanisms designed to evade account restrictions.
- Separate optional remote commands from read-only telemetry and credential storage.

## Remote lock and unlock — future functionality

The agreed design has lock and unlock **enabled by default when the authorized command provider is implemented and verified**. v0.1.1 does not include them. Explicit Home Assistant automation commands may lock/unlock; no command is ever emitted automatically on setup, startup, reconnection, telemetry update, or vehicle refresh. Serialize commands per vehicle, prevent blind retries or replay, honor Ford throttling, and enforce configurable command separation of **10-second minimum, 15-second default**. Ford restrictions take priority over user-configured intervals.

## Remote engine start/stop — strict future safety boundary

Engine controls are **not implemented in v0.1.1**. Any future implementation must remain disabled by default, require separate per-vehicle opt-in, extensive explicit warnings about carbon monoxide and potentially fatal operation in enclosed spaces, and a fresh authenticated confirmation for **each** manual action. Do not expose engine controls through Home Assistant automation-accessible switches, buttons, services, actions, scripts, voice assistants, webhooks, or schedules. No automatic engine start/stop retries. GPS, an open garage door, or a software-only location inference cannot establish that an engine may be safely started.

## Current engineering status and blocker

- v0.1.1 includes a read-only OAuth integration, telemetry entities, defensive parser, request budgeting, cache, diagnostics, Docker installer and in-place updater.
- A missing OAuth config-flow domain declaration caused a startup error in v0.1.0 and was patched in v0.1.1.
- Ford Developer application registration displayed a maintenance message during setup on 2026-10-25. This observation is not a claim about current Ford service status. No issued application credentials or consented vehicle response have been used for end-to-end verification.
- Actual Home Assistant runtime authentication, supported Ford telemetry, and remote commands remain unverified.
- The eventual public distribution plan requires HACS-ready releases, multi-model capability detection, secure per-user authorization, and approval for any shared public OAuth application. Never ship a confidential client secret in public source.

## Public-repository privacy rule

Do **not** commit personal names, owner-specific vehicle models, identifiable locations, genuine or plausible personal VINs, plates, account identifiers, home/IP addresses, phone numbers, email addresses, credentials, tokens, private environment details, real logs, or unredacted diagnostics. Use clearly synthetic test data. Review issues and releases before publication. Do not infer an individual's personal location or vehicle from examples.

**Resume order:** Verify Ford registration availability and public-app eligibility; verify official OAuth and telemetry on a consented test vehicle; evaluate the remote lock/unlock interface and safety budget; finish release testing and HACS readiness. No changes should be undertaken automatically.
