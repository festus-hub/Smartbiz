from django.db import migrations


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
