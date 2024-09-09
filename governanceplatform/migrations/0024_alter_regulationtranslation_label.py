# Generated by Django 5.1 on 2024-09-09 09:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0023_alter_service_acronym"),
    ]

    operations = [
        migrations.AlterField(
            model_name="regulationtranslation",
            name="label",
            field=models.CharField(
                default="[MISSING_TRANSLATION]", max_length=255, verbose_name="Label"
            ),
            preserve_default=False,
        ),
    ]