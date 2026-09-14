"""Reimport the enhanced motion at the 27 currently referenced reload paths."""
from pathlib import Path
source=Path(__file__).parent.parent/'DanWesson715ReloadSplit20260914/import_assets.py'
# __file__ remains this directory, so the importer reads this turn's FBX files.
exec(compile(source.read_text(encoding='utf-8').replace('DW715_SPLIT_','DW715_MOTION_'),str(source),'exec'),globals())
