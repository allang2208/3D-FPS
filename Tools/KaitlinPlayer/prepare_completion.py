"""Freeze the current source recipes; preserve earlier work and unrelated routes."""
from pathlib import Path
import hashlib,json
P=Path('D:/FPS3D/FPSGAME'); W=P/'SourceAssets/KaitlinCompletion20261024'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
write=lambda p,d:p.write_text(json.dumps(d,indent=2),encoding='utf-8')
W.mkdir(exist_ok=True); F=W/'Furniture';F.mkdir(exist_ok=True)
body=read(P/'Content/ColdSteelData/player_body.json');modular=read(P/'Content/ColdSteelData/modular_outfits.json')
def sha(path):return hashlib.sha256((P/'Content'/(path[6:].split('.')[0]+'.uasset')).read_bytes()).hexdigest()
if not (F/'source_catalog.json').exists():
    before=read(P/'SourceAssets/KaitlinFurniture20261024/source_catalog.json')
    previous=read(P/'SourceAssets/KaitlinFurniture20261024/saved_assets.json')
    clips={k:v for k,v in body['clips'].items() if k.startswith('Rest.')}
    catalog={'body_mesh':body['body_mesh'],'target_mesh':body['body_variants']['kaitlin']['body_mesh'],
             'clips':clips,'source_sha256':{k:sha(v) for k,v in clips.items()},
             'female_before':dict(body['body_variants']['kaitlin']['clips']), 'stale_roles':before['stale_roles']}
    write(F/'source_catalog.json',catalog)
    saved={k:v for k,v in previous.items() if v['source']==clips[k] and v['source_sha256']==catalog['source_sha256'][k]}
    write(F/'saved_assets.json',saved)
if not (W/'body_before.json').exists():write(W/'body_before.json',body);write(W/'modular_before.json',modular)
print('COMPLETION_PREPARED',len(read(F/'saved_assets.json')),'unchanged furniture saves reused')
