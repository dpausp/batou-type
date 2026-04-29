"""Sphinx configuration for batou-type documentation."""

import os
import sys

# Add project source to path so autoapi can resolve imports
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------

project = "batou-type"
copyright = "2024, batou-type contributors"  # noqa: A001
author = "batou-type contributors"

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "autoapi.extension",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx.ext.graphviz",
]

source_suffix = {".md": "markdown", ".rst": "restructuredtext"}

# -- MyST configuration ------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

myst_heading_anchors = 3

# -- autoapi configuration ---------------------------------------------------

autoapi_type = "python"
autoapi_dirs = ["../src/batou_type"]
autoapi_file_patterns = ["*.py"]
autoapi_generate_api_docs = True
autoapi_add_toctree_entry = True

autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]

autoapi_keep_files = True


def autoapi_skip_member(
    _app, _what: str, name: str, _obj, skip: bool, _options
) -> bool:
    """Skip private members, test classes, and vendor package from API docs."""
    # Skip private members (underscore prefix)
    if name.startswith("_"):
        return True
    # Skip test classes
    if "Test" in name:
        return True
    # Skip the vendor/ package — vendored stubs should not appear in API docs
    module_path = getattr(_obj, "__module__", "") if _obj else ""
    obj_qualname = getattr(_obj, "__qualname__", "") if _obj else ""
    if "vendor" in module_path or "batou_type.vendor" in obj_qualname:
        return True
    return skip


def setup(app):
    """Register autoapi skip member and missing-reference callbacks."""
    app.connect("autoapi-skip-member", autoapi_skip_member)
    app.connect("missing-reference", _resolve_inherited_refs)


# -- Type hints configuration ------------------------------------------------

autodoc_typehints = "description"

# -- Reference resolution for inherited docstrings ---------------------------

# autoapi inherits docstrings from parent classes (e.g., pytest.Item.runtest).
# These may contain :ref: cross-references to labels that only exist in pytest's docs.
# Resolve the specific reference from the inherited runtest() docstring to pytest docs.
_PYTEST_REF_OVERRIDES = {
    "non-python tests": "https://docs.pytest.org/en/stable/example/nonpython.html",
}


def _resolve_inherited_refs(_app, _env, node, contnode):
    """Resolve :ref: cross-references inherited from parent class docstrings."""
    if node.get("refdomain") == "std" and node.get("reftype") == "ref":
        uri = _PYTEST_REF_OVERRIDES.get(node.get("reftarget", ""))
        if uri:
            from docutils.nodes import reference

            ref = reference("", "", internal=False, refuri=uri)
            ref += contnode
            return ref
    return None


# -- sphinx-copybutton configuration -----------------------------------------

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | "
copybutton_prompt_is_regexp = True

# -- Graphviz configuration --------------------------------------------------

graphviz_output_format = "svg"

# -- HTML output configuration ------------------------------------------------

html_theme = "furo"
html_title = "batou-type Documentation"
