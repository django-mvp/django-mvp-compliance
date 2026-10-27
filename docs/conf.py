"""Sphinx settings for the documentation, which the demo project serves as its pages."""

project = "django-mvp-compliance"
extensions = ["mvp_sphinx.navigation", "myst_parser"]
source_suffix = {".md": "markdown"}
myst_heading_anchors = 4
# Pages about working on the package itself rather than using it. They are read
# in the repository and stay out of the built pages.
exclude_patterns = [
    "_build",
    "ROADMAP.md",
    "adr",
    "agents",
    "brainstorm.md",
    "contributing",
]
