"""View, filterset, and helpers for the Wagtail Comments report."""

from typing import TYPE_CHECKING, Any, ClassVar

import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from wagtail.admin.filters import DateRangePickerWidget, WagtailFilterSet
from wagtail.admin.views.reports.base import ReportView
from wagtail.models import Comment, Page

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


COMMENT_STATUS_OPEN = "open"
COMMENT_STATUS_RESOLVED = "resolved"
COMMENT_STATUS_ALL = "all"
COMMENT_STATUS_CHOICES = [
    (COMMENT_STATUS_OPEN, _("Open")),
    (COMMENT_STATUS_RESOLVED, _("Resolved")),
    (COMMENT_STATUS_ALL, _("All")),
]


def _get_comment_authors(request: "HttpRequest") -> "QuerySet":  # noqa: ARG001
    """
    Return users who have authored at least one comment.

    The `request` argument is required by django-filter's `queryset`
    callable signature, even though we don't use it.
    """
    user_model = get_user_model()
    return (
        user_model.objects.filter(wagtail_admin_comments__isnull=False).order_by(user_model.USERNAME_FIELD).distinct()
    )


def _get_commented_pages(request: "HttpRequest") -> "QuerySet":  # noqa: ARG001
    """
    Return pages that have at least one comment.

    The `request` argument is required by django-filter's `queryset`
    callable signature, even though we don't use it.
    """
    return Page.objects.filter(wagtail_admin_comments__isnull=False).order_by("title").distinct()


class CommentsReportFilterSet(WagtailFilterSet):
    """Author, page, date range, and tri-state Status filters."""

    user = django_filters.ModelChoiceFilter(
        field_name="user",
        label=_("Author"),
        queryset=_get_comment_authors,
    )
    page = django_filters.ModelChoiceFilter(
        field_name="page",
        label=_("Page"),
        queryset=_get_commented_pages,
    )
    created_at = django_filters.DateFromToRangeFilter(label=_("Date"), widget=DateRangePickerWidget)
    status = django_filters.ChoiceFilter(
        label=_("Status"),
        choices=COMMENT_STATUS_CHOICES,
        method="filter_status",
        empty_label=None,
    )

    def filter_status(
        self,
        queryset: "QuerySet",
        name: str,  # noqa: ARG002
        value: str,
    ) -> "QuerySet":
        """Map the tri-state Status choice onto a `resolved_at` filter."""
        if value == COMMENT_STATUS_OPEN:
            return queryset.filter(resolved_at__isnull=True)
        if value == COMMENT_STATUS_RESOLVED:
            return queryset.exclude(resolved_at__isnull=True)
        return queryset

    class Meta:
        """Filterset configuration."""

        model = Comment
        fields: ClassVar[list[str]] = ["user", "page", "created_at", "status"]


class CommentsReportView(ReportView):
    """
    Wagtail admin report listing every page comment in one place.

    Filters by author, page, date range, and a tri-state Status (Open /
    Resolved / All) that defaults to Open. Multiple Comment rows that
    Wagtail can stash at the same (page, user, contentpath) — a side
    effect of revision saves — are collapsed to the most recent row per
    position so the report shows one entry per logical comment.
    """

    results_template_name = "wagtail_comments_report/comments_report_results.html"
    page_title = _("Comments")
    header_icon = "comment"
    filterset_class = CommentsReportFilterSet
    index_url_name = "wagtail_comments_report"
    index_results_url_name = "wagtail_comments_report_results"

    export_headings: ClassVar[dict[str, Any]] = {
        "page": _("Page"),
        "user": _("Author"),
        "text": _("Comment"),
        "created_at": _("Date"),
        "resolved_at": _("Resolved at"),
    }
    list_export: ClassVar[list[str]] = [
        "page",
        "user",
        "text",
        "created_at",
        "resolved_at",
    ]

    def get_filterset_kwargs(self) -> dict[str, Any]:
        """
        Inject `status=open` when the URL has no value, so the report
        opens on unresolved comments by default.
        """  # noqa: D205
        kwargs = super().get_filterset_kwargs()
        data = kwargs.get("data")
        if data is not None and "status" not in data:
            mutable = data.copy()
            mutable["status"] = COMMENT_STATUS_OPEN
            kwargs["data"] = mutable
        return kwargs

    def get_queryset(self) -> "QuerySet":
        """
        Return one row per (page, user, contentpath) — the most recent.

        Wagtail can persist several Comment rows at the same position as a
        side effect of revision saves; we collapse them via `Max("id")`
        aggregation (cross-DB-portable, unlike Postgres-only `DISTINCT ON`).
        """
        latest_per_position_ids = (
            Comment.objects.values("page_id", "user_id", "contentpath")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )
        self.queryset = (
            Comment.objects.filter(id__in=latest_per_position_ids)
            .select_related("page", "user", "resolved_by")
            .order_by("-created_at")
        )
        return super().get_queryset()
