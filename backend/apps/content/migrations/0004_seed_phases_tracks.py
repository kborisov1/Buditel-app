"""Starting phases and tracks from scope 3.1 and 3.2. Editable in the admin afterwards."""

from datetime import date

from django.db import migrations

PHASES = [
    ("Пробуждане", date(1762, 1, 1), date(1820, 12, 31)),
    ("Просвета и ранна култура", date(1820, 1, 1), date(1856, 12, 31)),
    ("Църковна борба", date(1840, 1, 1), date(1870, 12, 31)),
    ("Национално-освободително движение", date(1860, 1, 1), date(1876, 12, 31)),
    ("Освобождение", date(1877, 1, 1), date(1878, 12, 31)),
]

TRACKS = [
    ("Пробуждане", "opening"),
    ("Просвета и култура", "regular"),
    ("Църковна борба", "regular"),
    ("Освободителна борба", "regular"),
    ("Финал", "finale"),
]


def seed(apps, schema_editor):  # type: ignore[no-untyped-def]
    Phase = apps.get_model("content", "Phase")
    Track = apps.get_model("content", "Track")
    for name, start, end in PHASES:
        Phase.objects.get_or_create(name=name, defaults={"start_date": start, "end_date": end})
    for position, (name, kind) in enumerate(TRACKS, start=1):
        Track.objects.get_or_create(name=name, defaults={"kind": kind, "position": position})


class Migration(migrations.Migration):
    dependencies = [("content", "0003_phase_track_gaterequirement_trackentry")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
