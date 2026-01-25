# -*- coding: utf-8 -*-
import os
import sys

import tlcpack_sphinx_addon

# -- General configuration ------------------------------------------------

sys.path.insert(0, os.path.abspath("../python"))
sys.path.insert(0, os.path.abspath("../"))
autodoc_mock_imports = ["torch"]

# General information about the project.
project = "sphere-aae"
author = "Astro Agent Edge (AAE) Contributors"
copyright = "2023-2025, %s" % author

# Version information.

version = "0.1.0"
release = "0.1.0"

extensions = [
    "sphinx_tabs.tabs",
    "sphinx_toolbox.collapse",
    "sphinxcontrib.httpdomain",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_reredirects",
]

redirects = {"get_started/try_out": "../index.html#getting-started"}

source_suffix = [".rst"]

language = "en"

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# A list of ignored prefixes for module index sorting.
# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

# The theme is set by the make target
import sphinx_rtd_theme

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

templates_path = []

html_static_path = []

footer_copyright = "© 2023-2025 Astro Agent Edge (AAE)"
footer_note = " "

html_logo = "_static/img/sphere-aae-logo-with-text-landscape.svg"

html_theme_options = {
    "logo_only": True,
}

header_links = [
    ("ドキュメント", "https://quantaril.cloud/"),
    ("フォーラム", "https://forum.i-s.dev/landing#/"),
    ("X", "https://x.com/K_chachamaru"),
    ("GitHub", "https://github.com/sphere-aae/sphere-aae"),
]

header_dropdown = {
    "name": "公式リソース",
    "items": [
        ("ドキュメント", "https://quantaril.cloud/"),
        ("フォーラム", "https://forum.i-s.dev/landing#/"),
        ("X", "https://x.com/K_chachamaru"),
    ],
}

html_context = {
    "footer_copyright": footer_copyright,
    "footer_note": footer_note,
    "header_links": header_links,
    "header_dropdown": header_dropdown,
    "display_github": True,
    "github_user": "sphere-aae",
    "github_repo": "sphere-aae",
    "github_version": "main/docs/",
    "theme_vcs_pageview_mode": "edit",
    # "header_logo": "/path/to/logo",
    # "header_logo_link": "",
    # "version_selecter": "",
}


# add additional overrides
templates_path += [tlcpack_sphinx_addon.get_templates_path()]
html_static_path += [tlcpack_sphinx_addon.get_static_path()]
