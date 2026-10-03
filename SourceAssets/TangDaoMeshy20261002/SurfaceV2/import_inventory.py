"""Publish the rule-aligned TangDao inventory PNG, including actual reimport."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent.parent /
                  'InventoryIconRules20261002/import_icon.py'), run_name='__main__')
