from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_valid_time_zone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True
