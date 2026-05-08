"""App configuration for wagtail_comments_report."""

from django.apps import AppConfig


class WagtailCommentsReportConfig(AppConfig):
    """Django AppConfig for the Wagtail Comments Report."""

    name = "wagtail_comments_report"
    label = "wagtail_comments_report"
    verbose_name = "Wagtail Comments Report"
    default_auto_field = "django.db.models.BigAutoField"
