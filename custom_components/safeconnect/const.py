"""Constants for SafeConnect. No engine control capabilities are defined."""
from typing import Final

DOMAIN: Final = "safeconnect"
NAME: Final = "SafeConnect"
CONF_VIN: Final = "vin"
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_POLL_MINUTES: Final = "poll_minutes"
DEFAULT_POLL_MINUTES: Final = 60
MIN_POLL_MINUTES: Final = 15
MAX_POLL_MINUTES: Final = 1440
FORD_API_BASE: Final = "https://api.vehicle.ford.com"
FORD_AUTHORIZE_URL: Final = FORD_API_BASE + "/fcon-public/v1/auth/init"
FORD_TOKEN_URL: Final = (
    FORD_API_BASE
    + "/dah2vb2cprod.onmicrosoft.com/oauth2/v2.0/token?p=B2C_1A_FCON_AUTHORIZE"
)
FORD_QUERY_BASE: Final = FORD_API_BASE + "/fcon-query/v1"
GARAGE_URL: Final = FORD_QUERY_BASE + "/garage"
TELEMETRY_URL: Final = FORD_QUERY_BASE + "/telemetry"

# No remote command URLs or tokens are used in this release.
