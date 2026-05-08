"""Tests for the Wagtail Comments report view."""

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Comment

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client
    from wagtail.models import Page


def _make_comment(
    page: "Page",
    user: "User",
    text: str = "hello",
    contentpath: str = "title",
    *,
    resolved: bool = False,
) -> Comment:
    """Create a Comment, optionally pre-marked as resolved."""
    comment = Comment.objects.create(page=page, user=user, text=text, contentpath=contentpath)
    if resolved:
        comment.resolved_at = timezone.now()
        comment.resolved_by = user
        comment.save()
    return comment


@pytest.mark.django_db
def test_report_lists_all_comments_by_default_sorted_desc(
    admin_client: "Client", page: "Page", admin_user: "User"
) -> None:
    """The newest comment must appear before older ones in the table."""
    earlier = _make_comment(page, admin_user, text="commentEARLIER", contentpath="a")
    _make_comment(page, admin_user, text="commentLATER", contentpath="b")
    Comment.objects.filter(pk=earlier.pk).update(created_at=earlier.created_at.replace(year=2020))

    response = admin_client.get(reverse("wagtail_comments_report"))

    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    table = re.search(r'<table class="listing">.*?</table>', body, re.DOTALL)
    assert table is not None
    rows = table.group(0)
    assert "commentEARLIER" in rows
    assert "commentLATER" in rows
    assert rows.index("commentLATER") < rows.index("commentEARLIER")


@pytest.mark.django_db
def test_report_defaults_to_open_only(admin_client: "Client", page: "Page", admin_user: "User") -> None:
    """With no `status` query param, only open comments are listed."""
    _make_comment(page, admin_user, text="open-comment", contentpath="a")
    _make_comment(page, admin_user, text="resolved-comment", contentpath="b", resolved=True)

    response = admin_client.get(reverse("wagtail_comments_report"))

    body = response.content.decode()
    assert "open-comment" in body
    assert "resolved-comment" not in body


@pytest.mark.django_db
def test_report_status_filter_resolved(admin_client: "Client", page: "Page", admin_user: "User") -> None:
    """`?status=resolved` shows only resolved comments."""
    _make_comment(page, admin_user, text="open-comment", contentpath="a")
    _make_comment(page, admin_user, text="resolved-comment", contentpath="b", resolved=True)

    response = admin_client.get(reverse("wagtail_comments_report") + "?status=resolved")

    body = response.content.decode()
    assert "resolved-comment" in body
    assert "open-comment" not in body


@pytest.mark.django_db
def test_report_status_filter_all(admin_client: "Client", page: "Page", admin_user: "User") -> None:
    """`?status=all` shows comments regardless of resolution."""
    _make_comment(page, admin_user, text="open-comment", contentpath="a")
    _make_comment(page, admin_user, text="resolved-comment", contentpath="b", resolved=True)

    response = admin_client.get(reverse("wagtail_comments_report") + "?status=all")

    body = response.content.decode()
    assert "open-comment" in body
    assert "resolved-comment" in body


@pytest.mark.django_db
def test_report_filters_by_author(
    admin_client: "Client",
    page: "Page",
    admin_user: "User",
    other_user: "User",
) -> None:
    """`?user=<id>` restricts the listing to that author's comments."""
    _make_comment(page, admin_user, text="from-admin", contentpath="a")
    _make_comment(page, other_user, text="from-other", contentpath="b")

    response = admin_client.get(reverse("wagtail_comments_report") + f"?user={admin_user.pk}")

    body = response.content.decode()
    assert "from-admin" in body
    assert "from-other" not in body


@pytest.mark.django_db
def test_report_dedupes_comments_at_same_position(admin_client: "Client", page: "Page", admin_user: "User") -> None:
    """
    Collapse multiple rows at one `(page, user, contentpath)` to one entry.

    Wagtail can persist multiple Comment rows at the same position as a side
    effect of revision saves; the report should show one logical comment per
    position (the most recent row).
    """
    for _ in range(5):
        _make_comment(
            page,
            admin_user,
            text="dupe",
            contentpath="content.block-a",
        )
    _make_comment(
        page,
        admin_user,
        text="distinct",
        contentpath="content.block-b",
    )

    response = admin_client.get(reverse("wagtail_comments_report"))

    body = response.content.decode()
    assert body.count("dupe") == 1
    assert "distinct" in body


@pytest.mark.django_db
def test_report_requires_admin_login(client: "Client") -> None:
    """Anonymous users are redirected or forbidden from the report."""
    response = client.get(reverse("wagtail_comments_report"))
    assert response.status_code in (HTTPStatus.FOUND, HTTPStatus.FORBIDDEN)
