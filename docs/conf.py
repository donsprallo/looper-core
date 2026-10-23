"""Sphinx configuration for the looper documentation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "looper"
release = "0.1.0"

# No attribution in the footer: the build carries no author or copyright.
html_show_copyright = False

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
always_document_param_types = True

napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Let cross document links point at a heading, as the user guide does.
myst_heading_anchors = 3

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# The inspector and the C runtime are projects of their own and document
# themselves in builds of their own. These are the only places that say
# where those builds are published; the defaults assume all three are
# deployed side by side.
GUI_DOCS = os.environ.get("LOOPER_GUI_DOCS", "../looper-gui")
RUNTIME_DOCS = os.environ.get("LOOPER_RT_DOCS", "../looper-rt")
extlinks = {
    "gui": (f"{GUI_DOCS}/%s", "%s"),
    "rt": (f"{RUNTIME_DOCS}/%s", "%s"),
}
extlinks_detect_hardcoded_links = True

nitpicky = True
# Third party types appear in signatures but ship no object inventory to link to.
nitpick_ignore_regex = [
    ("py:class", r"looper\..*"),
    ("py:class", r"clang\..*"),
    ("py:class", r"elftools\..*"),
    ("py:class", r"pydantic\..*"),
    ("py:class", r"looper_control_pb2\..*"),
]

# jinja2 annotates with a forward reference its own documentation cannot resolve.
suppress_warnings = ["sphinx_autodoc_typehints.forward_reference"]

html_theme = "furo"
html_title = "looper"
exclude_patterns = ["_build"]
