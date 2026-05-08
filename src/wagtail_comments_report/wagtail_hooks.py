"""Wagtail hooks: report menu item and admin URLs for the Comments report."""

from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from wagtail_comments_report.views import CommentsReportView


@hooks.register("register_reports_menu_item")
def register_comments_report() -> MenuItem:
    """Add a "Comments" entry under the Reports menu."""
    return MenuItem(
        _("Comments"),
        reverse("wagtail_comments_report"),
        icon_name="comment",
        order=750,
    )


@hooks.register("register_admin_urls")
def register_comments_report_urls() -> list[URLPattern]:
    """
    Register the index and partial-results URLs for the report.

    The `results_only` URL returns just the results-table fragment;
    Wagtail's admin JS calls it when the user changes a filter so the
    listing updates without a full page reload.
    """
    return [
        path(
            "reports/comments/",
            CommentsReportView.as_view(),
            name="wagtail_comments_report",
        ),
        path(
            "reports/comments/results/",
            CommentsReportView.as_view(results_only=True),
            name="wagtail_comments_report_results",
        ),
    ]
