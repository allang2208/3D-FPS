"""Publish only native first-person sleeves and their local inertia style."""
import hashlib, importlib.util, json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/FPSoftSleeves20261020'
saved=json.loads((R/'saved_assets.json').read_text())
manifest=json.loads((R/'manifest.json').read_text())
if not saved.get('completed'):raise RuntimeError('Finish sleeve saves before publication')
for row in manifest['records']:
    if saved['saved']['FP/'+row['profile']]['author_sha256']!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():
        raise RuntimeError('Native sleeve source changed '+row['profile'])
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig')
cfg=json.loads(text);robe=cfg['items']['ue_blue_mage_robe']
if any(robe['rig_meshes'][k]!=v for k,v in manifest['routes'].items()):
    raise RuntimeError('Current sleeve routes changed; preserve concurrent outfit work')
spec=importlib.util.spec_from_file_location('soft_sleeve_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
for key in manifest['routes']:
    text=entries.replace(text,['items','ue_blue_mage_robe','rig_meshes',key],saved['saved']['FP/'+key]['asset'])
for key,value in [('secondary_motion','robe_shared_sway_v1'),('first_person_sleeve_revision','soft-sleeves-20261020')]:
    text=entries.replace(text,['items','ue_blue_mage_robe',key],value) if key in robe else entries.insert(text,['items','ue_blue_mage_robe'],key,value)
if path.read_bytes()!=raw:raise RuntimeError('Outfit catalog changed during publication; retry')
backup=R/'publication-before.json'
if not backup.exists():backup.write_bytes(raw)
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,profiles=len(manifest['routes']),
    revision='soft-sleeves-20261020',secondary_motion='robe_shared_sway_v1',
    body_and_skirt_unchanged=True,underlayers_unchanged=True,runtime_tested=False),indent=2),encoding='utf-8')
print('SOFT_ROBE_SLEEVES_PUBLISHED',len(manifest['routes']),flush=True)
