#!/usr/bin/env bash
# Run on the Docker HOST, never inside the Home Assistant container.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HA_CONTAINER="${HA_CONTAINER:-homeassistant}"
SOURCE="$ROOT/custom_components/safeconnect"
RESTART=false
if [[ "${1:-}" == "--restart" ]]; then RESTART=true
elif [[ $# -ne 0 ]]; then echo 'Usage: bash install-on-dockeradm.sh [--restart]' >&2; exit 2; fi

command -v docker >/dev/null || { echo 'ERROR: Docker CLI not found on this host.' >&2; exit 2; }
[[ -f "$SOURCE/manifest.json" ]] || { echo 'ERROR: SafeConnect files missing. Unzip complete release first.' >&2; exit 2; }
docker inspect --type container "$HA_CONTAINER" >/dev/null 2>&1 || {
    echo "ERROR: '$HA_CONTAINER' container not found. Set HA_CONTAINER=actual_name." >&2
    exit 2
}
[[ "$(docker inspect -f '{{.State.Running}}' "$HA_CONTAINER")" == "true" ]] || {
    echo 'ERROR: Home Assistant container is not currently running.' >&2; exit 2;
}
CONFIG_MOUNT="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Type}}{{end}}{{end}}' "$HA_CONTAINER")"
[[ -n "$CONFIG_MOUNT" ]] || {
    echo 'ERROR: /config is not a Docker mount; refusing ephemeral installation.' >&2; exit 2;
}
docker exec "$HA_CONTAINER" test -d /config || { echo 'ERROR: /config missing.' >&2; exit 2; }
docker exec "$HA_CONTAINER" mkdir -p /config/custom_components
if docker exec "$HA_CONTAINER" test -e /config/custom_components/safeford; then
    echo 'ERROR: Legacy integration directory detected. Use migrate-on-dockeradm.sh instead.' >&2
    exit 3
fi
if docker exec "$HA_CONTAINER" test -e /config/custom_components/safeconnect; then
    echo 'ERROR: Existing SafeConnect installation found. Refusing to overwrite it automatically.' >&2
    echo 'Back up and remove/replace the old integration explicitly after review.' >&2
    exit 3
fi

echo "Installing SafeConnect 0.2.0 alpha.5 into '$HA_CONTAINER' (/config is $CONFIG_MOUNT-mounted)."
docker cp "$SOURCE" "$HA_CONTAINER:/config/custom_components/safeconnect"
docker exec "$HA_CONTAINER" test -f /config/custom_components/safeconnect/manifest.json
printf 'INSTALLED: /config/custom_components/safeconnect\n'
if $RESTART; then
    echo 'Restarting the Home Assistant container (--restart explicitly requested).'
    docker restart "$HA_CONTAINER" >/dev/null
    echo 'Restart command completed. Check Home Assistant startup logs and integrations UI.'
else
    echo 'Home Assistant was NOT restarted. Restart it from Settings > System or run with --restart.'
fi
