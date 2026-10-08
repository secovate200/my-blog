"""SmartBase Admin auto-discovery entry point for the blog application."""

# The admin definitions live in admin.py so Django's conventional discovery and
# SmartBase's sb_admin discovery both load the same, explicitly registered views.
from .admin import *  # noqa: F401,F403
