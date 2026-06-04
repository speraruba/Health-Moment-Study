from datetime import date as date_class, datetime, timedelta, timezone, time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import session

CENTRAL_TIMEZONE_NAME = "America/Chicago"


def central_timezone():
    try:
        return ZoneInfo(CENTRAL_TIMEZONE_NAME)
    except ZoneInfoNotFoundError:
        return timezone.utc


def current_utc_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


def normalize_unix_timestamp(value):
    """Normalize webhook time input to unix timestamp (seconds)."""
    if value is None:
        return current_utc_timestamp()

    if isinstance(value, (int, float)):
        ts = float(value)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return current_utc_timestamp()

        try:
            ts = float(raw)
        except ValueError:
            iso_raw = raw.replace('Z', '+00:00')
            try:
                dt = datetime.fromisoformat(iso_raw)
            except ValueError:
                return current_utc_timestamp()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.astimezone(timezone.utc).timestamp())
    else:
        return current_utc_timestamp()

    if ts > 1_000_000_000_000:
        ts = ts / 1000
    return int(ts)


def resolve_dashboard_timezone():
    session['dashboard_timezone'] = CENTRAL_TIMEZONE_NAME
    return central_timezone()


def local_day_bounds_to_utc_timestamps(local_date, user_tz):
    local_start = datetime.combine(local_date, time.min, tzinfo=user_tz)
    local_end = local_start + timedelta(days=1)
    utc_start_ts = int(local_start.astimezone(timezone.utc).timestamp())
    utc_end_ts = int(local_end.astimezone(timezone.utc).timestamp())
    return utc_start_ts, utc_end_ts


def central_datetime_string(utc_timestamp):
    utc_dt = datetime.fromtimestamp(utc_timestamp, timezone.utc)
    central_dt = utc_dt.astimezone(central_timezone())
    return central_dt.strftime("%Y-%m-%d %H:%M:%S")


def central_date_string(utc_timestamp):
    utc_timestamp = normalize_calendar_date_timestamp(utc_timestamp)
    if utc_timestamp is None:
        return ''
    utc_dt = datetime.fromtimestamp(utc_timestamp, timezone.utc)
    central_dt = utc_dt.astimezone(central_timezone())
    return central_dt.strftime("%Y-%m-%d")


def central_date_to_utc_timestamp(date_value):
    central_start = datetime.combine(date_value, time.min, tzinfo=central_timezone())
    return int(central_start.astimezone(timezone.utc).timestamp())


def normalize_calendar_date_timestamp(value):
    """Normalize stored calendar start date values to a UTC unix timestamp."""
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return central_date_to_utc_timestamp(value.date())
        return central_date_to_utc_timestamp(value.astimezone(central_timezone()).date())

    if isinstance(value, date_class):
        return central_date_to_utc_timestamp(value)

    if isinstance(value, Decimal):
        value = float(value)

    if isinstance(value, (int, float)):
        raw_int = int(value)
        raw_digits = str(raw_int)
        if len(raw_digits) == 8:
            try:
                return central_date_to_utc_timestamp(datetime.strptime(raw_digits, "%Y%m%d").date())
            except ValueError:
                pass

        ts = float(value)
        if ts > 1_000_000_000_000:
            ts = ts / 1000
        return int(ts)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        date_part = raw[:10]
        try:
            return central_date_to_utc_timestamp(datetime.strptime(date_part, "%Y-%m-%d").date())
        except ValueError:
            pass

        if raw.isdigit() and len(raw) == 8:
            try:
                return central_date_to_utc_timestamp(datetime.strptime(raw, "%Y%m%d").date())
            except ValueError:
                pass

        try:
            return normalize_calendar_date_timestamp(float(raw))
        except ValueError:
            pass

        try:
            parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return None

        return normalize_calendar_date_timestamp(parsed)

    return None


def central_today():
    return datetime.now(timezone.utc).astimezone(central_timezone()).date()
