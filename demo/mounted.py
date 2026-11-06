"""The demo's pages: the package's documentation, served by django-mvp-sphinx."""

from mvp_sphinx.mounted import DocumentationApp

from demo.settings import BASE_DIR

docs = DocumentationApp(
    build_dir=BASE_DIR / "docs" / "_build" / "json",
    source_dir=BASE_DIR / "docs",
    name="Documentation",
)
