"""Make the pickup and inventory view from the final nape-contoured helmet."""
from pathlib import Path
import hashlib
import json
import runpy

r=Path(__file__).resolve().parents[2]/'SourceAssets/ModernTacticalSet20261113/HelmetNapeR3'
inputs=[r/'Models/TS01_Helmet_Jason_GAME.blend',r/'Authored/helmet_Jason_world.json']
before={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
runpy.run_path(str(Path(__file__).with_name('helmet_contour_artwork.py')),
               init_globals={'HELMET_REVISION': 'HelmetNapeR3'})
after={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
if before!=after:
    raise RuntimeError('Helmet master changed while making its inventory views')
receipt=r/'artwork.json'
data=json.loads(receipt.read_bytes())
data['source_sha256']=before
receipt.write_text(json.dumps(data,indent=2),encoding='utf-8')
