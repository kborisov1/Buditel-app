from django.db import migrations

DEFAULTS = {"xp_challenge_correct": 2, "xp_challenge_bonus": 10}


def seed(apps, schema_editor):  # type: ignore[no-untyped-def]
    AppSetting = apps.get_model("core", "AppSetting")
    for key, value in DEFAULTS.items():
        AppSetting.objects.get_or_create(key=key, defaults={"value": value})


class Migration(migrations.Migration):
    dependencies = [("core", "0007_alter_appsetting_key")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
