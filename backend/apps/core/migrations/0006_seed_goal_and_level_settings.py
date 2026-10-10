from django.db import migrations

DEFAULTS = {
    "daily_goal_xp": 40,
    "goal_overflow_percentage": 80,
    "level_base_xp": 100,
    "level_step_xp": 25,
}


def seed(apps, schema_editor):  # type: ignore[no-untyped-def]
    AppSetting = apps.get_model("core", "AppSetting")
    for key, value in DEFAULTS.items():
        AppSetting.objects.get_or_create(key=key, defaults={"value": value})


class Migration(migrations.Migration):
    dependencies = [("core", "0005_alter_appsetting_key")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
