#!/usr/bin/env bash
# Safely update a persistent SafeConnect HA installation from a Git checkout.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HA_CONTAINER="${HA_CONTAINER:-homeassistant}"
SOURCE="$ROOT/custom_components/safeconnect"
RESTART=false
case "${1:-}" in
    '') [[ $# -eq 0 ]] || exit 2 ;;
    --restart) [[ $# -eq 1 ]] || { echo 'Usage: bash update-on-dockeradm.sh [--restart]' >&2; exit 2; }; RESTART=true ;;
    *) echo 'Usage: bash update-on-dockeradm.sh [--restart]' >&2; exit 2 ;;
esac
command -v docker >/dev/null || { echo 'ERROR: Docker not installed on host.' >&2; exit 2; }
[[ -f "$SOURCE/manifest.json" && -f "$SOURCE/config_flow.py" ]] || { echo 'ERROR: Source incomplete.' >&2; exit 2; }
if command -v python3 >/dev/null; then
  python3 - "$SOURCE" <<'PY'
import ast
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
assert manifest["domain"] == "safeconnect" and manifest["config_flow"] is True
assert manifest["version"] == "0.2.0a0", "Unexpected source version"
for path in root.glob("*.py"):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
PY
fi
docker inspect --type container "$HA_CONTAINER" >/dev/null 2>&1 || { echo "ERROR: '$HA_CONTAINER' not found." >&2; exit 2; }
[[ "$(docker inspect -f '{{.State.Running}}' "$HA_CONTAINER")" == 'true' ]] || { echo 'ERROR: HA container not running.' >&2; exit 2; }
mount_type="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Type}}{{end}}{{end}}' "$HA_CONTAINER")"
[[ "$mount_type" == bind || "$mount_type" == volume ]] || { echo 'ERROR: /config must be a persistent volume/bind.' >&2; exit 2; }
TARGET=/config/custom_components/safeconnect
if docker exec "$HA_CONTAINER" test -e /config/custom_components/safeford; then
  echo 'ERROR: Legacy integration directory detected; run migrate-on-dockeradm.sh before updating.' >&2
  exit 3
fi
docker exec "$HA_CONTAINER" test -d "$TARGET" || { echo 'ERROR: SafeConnect not installed; use install-on-dockeradm.sh.' >&2; exit 3; }
if docker exec "$HA_CONTAINER" test -L "$TARGET"; then echo 'ERROR: Refusing to replace a symbolic link.' >&2; exit 3; fi
token="$(date -u +%Y%m%dT%H%M%SZ)-$$"
STAGE="/config/custom_components/.safeconnect-stage-$token"
BACKUP="/config/.safeconnect-backups/safeconnect-$token"
docker exec "$HA_CONTAINER" mkdir -p /config/.safeconnect-backups
if docker exec "$HA_CONTAINER" test -e "$STAGE"; then echo 'ERROR: Stage already exists.' >&2; exit 3; fi
cleanup() { docker exec "$HA_CONTAINER" rm -rf -- "$STAGE" >/dev/null 2>&1 || true; }
trap cleanup EXIT
echo 'Staging SafeConnect without modifying the current installation.'
docker cp "$SOURCE" "$HA_CONTAINER:$STAGE"
docker exec "$HA_CONTAINER" test -f "$STAGE/manifest.json"
docker exec "$HA_CONTAINER" test -f "$STAGE/config_flow.py"
docker exec "$HA_CONTAINER" /bin/sh -c '
set -eu
source_dir="$1"
target_dir="$2"
backup_dir="$3"
[ ! -L "$target_dir" ] || exit 11
[ -d "$source_dir" ] && [ -d "$target_dir" ] || exit 12
[ ! -e "$backup_dir" ] || exit 13
mv "$target_dir" "$backup_dir"
if ! mv "$source_dir" "$target_dir"; then
    mv "$backup_dir" "$target_dir"
    exit 14
fi
' safeconnect-upgrade "$STAGE" "$TARGET" "$BACKUP"
trap - EXIT
printf 'UPDATED: %s\nBACKUP: %s\n' "$TARGET" "$BACKUP"
if "$RESTART"; then
  echo 'Restarting Home Assistant as requested.'
  docker restart "$HA_CONTAINER" >/dev/null
  echo 'RESTART REQUESTED. Check Home Assistant logs and repeat SafeConnect setup.'
else
  echo 'Restart Home Assistant once to load the updated config flow.'
fi
