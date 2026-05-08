"""Shared pytest fixtures for the wagtail_comments_report test suite."""

from typing import TYPE_CHECKING

import pytest
from wagtail.models import Page, Site

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client


@pytest.fixture
def root_page(db: None) -> Page:  # noqa: ARG001
    """Create a Wagtail root Page and associate it with the default Site."""
    if Page.objects.filter(depth=1).exists():
        return Page.objects.get(depth=1)
    root = Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.update_or_create(
        is_default_site=True,
        defaults={"root_page": root, "hostname": "localhost"},
    )
    return root


@pytest.fixture
def page(root_page: Page) -> Page:
    """Create a plain Wagtail Page that comments can attach to."""
    page = Page(title="Test Page", slug="test-page", live=True)
    root_page.add_child(instance=page)
    return page


@pytest.fixture
def admin_user(db: None, django_user_model: "User") -> "User":  # noqa: ARG001
    """Create a superuser for hitting the Wagtail admin."""
    return django_user_model.objects.create_user(
        username="admin",
        password="x",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def other_user(db: None, django_user_model: "User") -> "User":  # noqa: ARG001
    """Create a second staff user used to test the author filter."""
    return django_user_model.objects.create_user(
        username="other",
        password="x",
        is_staff=True,
    )


@pytest.fixture
def admin_client(client: "Client", admin_user: "User") -> "Client":
    """Return a Django test client logged in as `admin_user`."""
    client.force_login(admin_user)
    return client
