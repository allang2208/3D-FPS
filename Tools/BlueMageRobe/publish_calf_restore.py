"""Promote only the saved calf-restoration package family."""
import json,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');F=P/'SourceAssets/BlueMageRobe20261018/LegFit20261019'
file=F/'CalfRestore/saved_assets.json';saved=json.loads(file.read_text())
if not saved.get('completed'):raise RuntimeError('Calf restoration assets have not finished saving')
(F/'saved_assets.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
runpy.run_path(str(P/'Tools/BlueMageRobe/publish_legfit.py'),run_name='__main__')
(F/'CalfRestore/published.json').write_bytes((F/'published.json').read_bytes())
print('BLUE_ROBE_CALF_RESTORATION_PUBLISHED')
