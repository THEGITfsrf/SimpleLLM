from datetime import datetime
from zoneinfo import ZoneInfo

description = "Converts a datetime between timezones using ISO format."

args = {
    "from_timezone": {
        "type": "string",
        "description": "Source timezone (IANA or city name)"
    },
    "to_timezone": {
        "type": "string",
        "description": "Destination timezone (IANA or city name)"
    },
    "datetime_str": {
        "type": "string",
        "description": "ISO datetime string (NEVER 'now')"
    },
    "format_24h": {
        "type": "boolean",
        "description": "True for 24-hour format"
    }
}

required = ["from_timezone", "to_timezone", "datetime_str"]


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


def main(from_timezone, to_timezone, datetime_str, format_24h=True):
    try:
        # 🚫 HARD GUARD against your original bug
        if datetime_str.strip().lower() == "now":
            return {"error": "datetime_str cannot be 'now'. Use time_now tool instead."}

        src = ZoneInfo(_coerce_timezone(from_timezone))
        dst = ZoneInfo(_coerce_timezone(to_timezone))

        dt = datetime.fromisoformat(datetime_str.replace(" ", "T"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=src)
        else:
            dt = dt.astimezone(src)

        converted = dt.astimezone(dst)

        return {
            "from_timezone": str(src),
            "to_timezone": str(dst),
            "input_time": _fmt(dt, format_24h),
            "output_time": _fmt(converted, format_24h),
        }

    except Exception as e:
        return {"error": str(e)}