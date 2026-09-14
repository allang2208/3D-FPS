"""Import the 27 natural reloads at their own unlocked asset paths."""
from pathlib import Path
source=Path(__file__).parent.parent/'DanWesson715ReloadSplit20260914/import_assets.py'
exec(compile(source.read_text(encoding='utf-8').replace('DW715_SPLIT_','DW715_NATURAL_'),str(source),'exec'),globals())
