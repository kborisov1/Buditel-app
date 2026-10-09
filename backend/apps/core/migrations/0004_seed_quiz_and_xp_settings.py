from django.db import migrations

DEFAULTS = {
    "quiz_pass_percentage": 80,
    "quiz_missed_weight": 3,
    "xp_quiz_first_pass": 50,
    "xp_quiz_retake": 5,
    "xp_review_correct": 2,
    "xp_check_correct": 3,
    "xp_daily_login": 5,
    "xp_daily_goal_bonus": 10,
}


def seed(apps, schema_editor):  # type: ignore[no-untyped-def]
    AppSetting = apps.get_model("core", "AppSetting")
    for key, value in DEFAULTS.items():
        AppSetting.objects.get_or_create(key=key, defaults={"value": value})


class Migration(migrations.Migration):
    dependencies = [("core", "0003_alter_appsetting_key")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
