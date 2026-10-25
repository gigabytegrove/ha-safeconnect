#!/usr/bin/env bash
# Migrate installed integration package to the SafeConnect HA domain without editing HA internals.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HA_CONTAINER="${HA_CONTAINER:-homeassistant}"
SOURCE="$ROOT/custom_components/safeconnect"
[[ $# -eq 0 || ( $# -eq 1 && "${1:-}" == "--restart" ) ]] || { echo 'Usage: bash migrate-on-dockeradm.sh [--restart]' >&2; exit 2; }
command -v docker >/dev/null || { echo 'ERROR: Docker command missing.' >&2; exit 2; }
[[ -f "$SOURCE/manifest.json" ]] || { echo 'ERROR: SafeConnect source missing.' >&2; exit 2; }
docker inspect --type container "$HA_CONTAINER" >/dev/null || { echo "ERROR: Home Assistant container '$HA_CONTAINER' not found." >&2; exit 2; }
[[ "$(docker inspect -f '{{.State.Running}}' "$HA_CONTAINER")" == 'true' ]] || { echo 'ERROR: HA container not running.' >&2; exit 2; }
mounted="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Type}}{{end}}{{end}}' "$HA_CONTAINER")"
[[ "$mounted" == "bind" || "$mounted" == "volume" ]] || { echo 'ERROR: HA /config must be persistent.' >&2; exit 2; }
OLD=/config/custom_components/safeford
NEW=/config/custom_components/safeconnect
docker exec "$HA_CONTAINER" test -d "$OLD" || { echo 'ERROR: Legacy directory is absent. Use installer for a fresh deployment.' >&2; exit 3; }
if docker exec "$HA_CONTAINER" test -e "$NEW"; then
  echo 'ERROR: New integration directory already exists. Refusing to overwrite it.' >&2
  exit 3
fi
if docker exec "$HA_CONTAINER" test -L "$OLD"; then echo 'ERROR: Legacy directory is a symbolic link.' >&2; exit 3; fi
# HA's .storage/core.config_entries is private internal state. Only read it and refuse
# migration while any old-domain entry exists. Do not rewrite it from outside HA.
docker exec -i "$HA_CONTAINER" python3 - <<'PY'
import json
from pathlib import Path
p = Path("/config/.storage/core.config_entries")
if p.exists():
    try:
        entries = json.loads(p.read_text()).get("data",{}).get("entries",[])
    except (OSError, ValueError, AttributeError) as ex:
        raise SystemExit("ERROR: Could not inspect config entries safely.") from ex
    if any(isinstance(e, dict) and e.get("domain") == "safeford" for e in entries):
        raise SystemExit("ERROR: Remove legacy integration through HA Devices & services first. Credentials are NOT migrated automatically.")
PY
token="$(date -u +%Y%m%dT%H%M%SZ)-$$"
STAGE="/config/custom_components/.safeconnect-stage-$token"
BACKUP="/config/.safeconnect-backups/legacy-$token"
docker exec "$HA_CONTAINER" mkdir -p /config/.safeconnect-backups
docker cp "$SOURCE" "$HA_CONTAINER:$STAGE"
docker exec "$HA_CONTAINER" test -f "$STAGE/manifest.json"
docker exec "$HA_CONTAINER" /bin/sh -c '
set -eu
old="$1"; stage="$2"; dest="$3"; backup="$4"
[ -d "$old" ] && [ -d "$stage" ] && [ ! -e "$dest" ] && [ ! -e "$backup" ]
mv "$old" "$backup"
if ! mv "$stage" "$dest"; then
    mv "$backup" "$old"
    exit 14
fi
' safeconnect-migrate "$OLD" "$STAGE" "$NEW" "$BACKUP"
echo "MIGRATED: $NEW"
echo "BACKUP: $BACKUP"
echo 'No Home Assistant OAuth credentials or cache were copied or edited.'
if [[ "${1:-}" == "--restart" ]]; then
    docker restart "$HA_CONTAINER" >/dev/null
    echo 'Home Assistant restart requested.'
else
    echo 'Restart Home Assistant before adding SafeConnect.'
fi
