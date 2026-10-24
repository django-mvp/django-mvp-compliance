"""A module of kinds that cannot be imported."""

from django.core.exceptions import ImproperlyConfigured

raise ImproperlyConfigured("this module needs a setting the project lacks")
