"""Render the explicitly requested current model, never the older review mesh."""
import json,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');B=P/'SourceAssets/RangerLeatherPants20261021'
latest=json.loads((B/'latest_revision.json').read_text(encoding='utf-8-sig'))
runpy.run_path(str(P/'Tools/RangerLeatherPants/render_review.py'),run_name='__main__',init_globals={'ROOT_OVERRIDE':latest['root'],'PREVIEW_ONLY':True})
