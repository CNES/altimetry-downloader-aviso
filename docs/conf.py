# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "Altimetry Downloader Aviso"
copyright = "2025, CLS/CNES"
author = "CLS/CNES"
release = "0.2.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # support Google/Numpy style docstrings
    "sphinx_autodoc_typehints",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_design",
]

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_last_updated_fmt = "%a, %d %B %Y %H:%M:%S"
html_logo = "_static/logo-aviso.jpeg"

html_theme_options = {
    "navigation_depth": 4,
}

html_css_files = [
    "css/custom.css",
]
