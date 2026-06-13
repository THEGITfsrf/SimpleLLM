from datetime import datetime, timezone
from zoneinfo import ZoneInfo

description = "Gets the current time for a given timezone."

args = {
    "timezone_name": {
        "type": "string",
        "description": "IANA timezone or city name (e.g. America/Denver, Denver)"
    },
    "format_24h": {
        "type": "boolean",
        "description": "True for 24-hour format, False for 12-hour format"
    }
}

required = ["timezone_name"]


CITY_TO_TZ = {
    "denver": "America/Denver",
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "phoenix": "America/Phoenix",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
    "utc": "UTC",
}


def _coerce_timezone(value):
    if not value:
        return "UTC"
    return CITY_TO_TZ.get(value.strip().lower(), value)


def _fmt(dt, format_24h):
    return dt.strftime(
        "%Y-%m-%d %H:%M:%S %Z%z"
        if format_24h
        else "%Y-%m-%d %I:%M:%S %p %Z%z"
    )


def main(timezone_name="UTC", format_24h=True):
    try:
        tz_name = _coerce_timezone(timezone_name)
        tz = ZoneInfo(tz_name)

        now = datetime.now(tz)

        return {
            "timezone": tz_name,
            "time": _fmt(now, format_24h),
            "utc_time": _fmt(datetime.now(timezone.utc), True),
        }

    except Exception as e:
        return {"error": str(e)}