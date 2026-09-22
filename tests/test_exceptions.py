"""Tests for mvp_compliance.exceptions."""

from django.core.exceptions import ValidationError

from mvp_compliance.exceptions import (
    PublishedVersionError,
    PublishError,
    RecordedAcceptanceError,
    RecordError,
)


class TestExceptions:
    """Neither exception is a ValidationError (D9)."""

    def test_publish_error_is_not_a_validation_error(self):
        assert not issubclass(PublishError, ValidationError)

    def test_published_version_error_is_not_a_validation_error(self):
        assert not issubclass(PublishedVersionError, ValidationError)

    def test_publish_error_has_a_docstring_naming_its_requirement(self):
        assert PublishError.__doc__

    def test_published_version_error_has_a_docstring_naming_its_requirement(self):
        assert PublishedVersionError.__doc__

    def test_record_error_is_not_a_validation_error(self):
        assert not issubclass(RecordError, ValidationError)

    def test_recorded_acceptance_error_is_not_a_validation_error(self):
        assert not issubclass(RecordedAcceptanceError, ValidationError)

    def test_record_error_has_a_docstring_naming_its_requirement(self):
        assert RecordError.__doc__

    def test_recorded_acceptance_error_has_a_docstring_naming_its_requirement(self):
        assert RecordedAcceptanceError.__doc__
