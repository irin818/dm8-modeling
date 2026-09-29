"""Workspace discovery and read-only file inventory."""
from .paths import WorkspacePaths
from .inventory import scan_data_inventory, write_inventory
