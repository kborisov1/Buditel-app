from django.db import migrations


def seed(apps, schema_editor):  # type: ignore[no-untyped-def]
    AppSetting = apps.get_model("core", "AppSetting")
    AppSetting.objects.get_or_create(key="finale_percentage", defaults={"value": 80})


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
