"""Import the 27 left-recovery revisions using the accepted skeleton."""
from pathlib import Path
source=Path(__file__).parent.parent/'DanWesson715ReloadSplit20260914/import_assets.py'
exec(compile(source.read_text(encoding='utf-8').replace('DW715_SPLIT_','DW715_LEFT_RECOVERY_'),str(source),'exec'),globals())
