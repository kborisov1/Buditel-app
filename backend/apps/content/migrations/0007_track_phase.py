"""Link each track to the phase band drawn behind its timeline lane (scope 3.2, 7.2)."""

import django.db.models.deletion
from django.db import migrations, models

# Track name -> phase name for the starting data of migration 0004.
PAIRS = {
    "Пробуждане": "Пробуждане",
    "Просвета и култура": "Просвета и ранна култура",
    "Църковна борба": "Църковна борба",
    "Освободителна борба": "Национално-освободително движение",
    "Финал": "Освобождение",
}


def link(apps, schema_editor):  # type: ignore[no-untyped-def]
    Phase = apps.get_model("content", "Phase")
    Track = apps.get_model("content", "Track")
    for track_name, phase_name in PAIRS.items():
        phase = Phase.objects.filter(name=phase_name).first()
        if phase is not None:
            Track.objects.filter(name=track_name, phase__isnull=True).update(phase=phase)


class Migration(migrations.Migration):
    dependencies = [("content", "0006_track_order_by_date")]

    operations = [
        migrations.AddField(
            model_name="track",
            name="phase",
            field=models.ForeignKey(
                blank=True,
                help_text="The phase band drawn behind this track's lane on the timeline.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracks",
                to="content.phase",
            ),
        ),
        migrations.RunPython(link, migrations.RunPython.noop),
    ]
