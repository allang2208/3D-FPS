"""Background CPU cloth comparison requested for the October 8 regression."""
import unreal as u
import csv
from pathlib import Path
u.SystemLibrary.execute_console_command(None, 'Editor.AsyncSkinnedAssetCompilation 0')
u.SystemLibrary.execute_console_command(None, 'BoundCongregate.ProfileCloth')
report=Path('D:/FPS3D/FPSGAME/Saved/Profiling/BoundCongregate/SK_BoundCongregate_FullWhipV10-cloth.csv')
rows=list(csv.DictReader(report.read_text(encoding='utf-8-sig').splitlines()))
if len(rows)!=4 or any(int(r['cloths'])!=4 or int(r['dynamic'])<=0 for r in rows):
    raise RuntimeError('No valid four-garment simulation measurement')
