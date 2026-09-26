"""Tests for mvp_compliance.urls."""

import pytest
from django.urls import Resolver404, resolve, reverse


class TestVersionNumberConverter:
    """A version's address takes its number, and only a number."""

    @pytest.mark.parametrize("number", ["2026.1", "2026.12"])
    def test_a_number_resolves_to_the_version_address(self, number):
        match = resolve(f"/legal/privacy-policy/{number}/")

        assert match.view_name == "mvp_compliance:version"
        assert match.kwargs == {"slug": "privacy-policy", "number": number}

    @pytest.mark.parametrize("number", ["2026.1", "2026.12"])
    def test_a_number_reverses_to_its_address(self, number):
        address = reverse("mvp_compliance:version", args=["privacy-policy", number])

        assert address == f"/legal/privacy-policy/{number}/"

    @pytest.mark.parametrize("segment", ["2026", "26.1", "2026.x"])
    def test_anything_else_does_not_resolve_to_the_version_address(self, segment):
        with pytest.raises(Resolver404):
            resolve(f"/legal/privacy-policy/{segment}/")

    def test_versions_is_the_version_list_not_a_number(self):
        assert resolve("/legal/privacy-policy/versions/").url_name == "versions"
