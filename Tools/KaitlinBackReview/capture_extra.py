"""Inspect the two distinct paired backs not represented by base garment views."""
import json,gc,hashlib,struct
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/KaitlinBackReview20261117'
previous=json.loads((R/'captured.json').read_text())
covered={a['back_geometry_sha256'] for a in previous['assets'] if 'back_view' in a}
assets=[]
for row in previous['assets']:
 if row['back_geometry_sha256'] in covered:continue
 covered.add(row['back_geometry_sha256'])
 row['base']=True
 row['routes'][0]['item']+='_tactical_pair'
 assets.append(row)
script=(P/'Tools/KaitlinBackReview/capture.py').read_text()
block=script[script.index('G=u.GeometryScript'):script.index("(R/'captured.json')")]
exec(compile(block,'<paired-back read>','exec'))
(R/'captured_extra.json').write_text(json.dumps(report,indent=2))
print('KAITLIN_PAIRED_BACK_CAPTURED',len(assets),flush=True)
