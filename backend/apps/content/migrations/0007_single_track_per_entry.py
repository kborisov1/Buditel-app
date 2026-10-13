from typing import Any

from django.db import migrations, models


def keep_first_track(apps: Any, schema_editor: Any) -> None:
    """An event keeps the membership in the lowest-position track; the others are dropped."""
    TrackEntry = apps.get_model("content", "TrackEntry")
    seen = set()
    for row in TrackEntry.objects.order_by("track__position", "track_id", "id"):
        if row.entry_id in seen:
            row.delete()
        seen.add(row.entry_id)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_track_order_by_date"),
    ]

    operations = [
        migrations.RunPython(keep_first_track, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="trackentry", name="unique_track_entry"),
        migrations.AddConstraint(
            model_name="trackentry",
            constraint=models.UniqueConstraint(fields=("entry",), name="unique_entry_single_track"),
        ),
    ]
