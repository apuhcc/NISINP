# Generated by Django 4.2 on 2024-07-17 09:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "incidents",
            "0004_alter_impact_options_alter_impacttranslation_options_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="LogReportRead",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Timestamp"
                    ),
                ),
                (
                    "user_full_name",
                    models.CharField(max_length=250, verbose_name="User full name"),
                ),
                (
                    "action",
                    models.CharField(max_length=10, verbose_name="Action performed"),
                ),
                (
                    "incident",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="incidents.incident",
                        verbose_name="Incident report answered",
                    ),
                ),
                (
                    "incident_report",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="incidents.incidentworkflow",
                        verbose_name="Incident report answered",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
        ),
    ]
