"""Levels and titles (scope 6.2, architecture 6.5)."""

from dataclasses import dataclass
from math import isqrt

from apps.core.app_settings import get_setting

# Lowest level of each title. Keys are translated in the frontend (scope 1).
TITLES = [
    (1, "peasant"),
    (3, "student"),
    (6, "teacher"),
    (9, "reading_room_activist"),
    (12, "haidut"),
    (15, "komita"),
    (18, "voivode"),
    (21, "apostle"),
]


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    total_xp: int
    xp_into_level: int
    xp_for_next_level: int


def xp_to_reach(level: int, base: int, step: int) -> int:
    """Total XP at which `level` starts: an arithmetic series of per-level costs."""
    m = level - 1
    return m * base + step * m * (m - 1) // 2


def level_for(total_xp: int, base: int, step: int) -> int:
    """Closed form: the largest m with step*m(m-1)/2 + base*m <= xp, plus one."""
    if step == 0:
        m = total_xp // base
    else:
        b = 2 * base - step
        m = max(0, (isqrt(b * b + 8 * step * total_xp) - b) // (2 * step))
    # isqrt rounding can be off by one either way.
    while xp_to_reach(m + 2, base, step) <= total_xp:
        m += 1
    while m > 0 and xp_to_reach(m + 1, base, step) > total_xp:
        m -= 1
    return m + 1


def title_for(level: int) -> str:
    return [key for start, key in TITLES if level >= start][-1]


def level_info(total_xp: int) -> LevelInfo:
    base, step = get_setting("level_base_xp"), get_setting("level_step_xp")
    level = level_for(total_xp, base, step)
    start = xp_to_reach(level, base, step)
    return LevelInfo(
        level=level,
        title=title_for(level),
        total_xp=total_xp,
        xp_into_level=total_xp - start,
        xp_for_next_level=xp_to_reach(level + 1, base, step) - start,
    )
