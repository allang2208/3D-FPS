"""Merge only repaired FP mesh routes after all intended assets are saved."""
import copy,hashlib,json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
from json_entries import replace
inventory=json.loads((R/'inventory.json').read_text());receipt=json.loads((R/'saved_assets.json').read_text())
if not receipt.get('completed'):raise RuntimeError('Garment save batch incomplete')
expected={row['item']+'/'+row['profile'] for row in inventory['rows'] if row['item'] in ('ue_field_sweater','ue_chainmail_shirt') or row['profile'] in ('SVD','Super90')}
if set(receipt['saved'])!=expected:raise RuntimeError('Saved receipt does not yet cover the 48 intended mesh routes')
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');config=json.loads(text)
changes={};profiles={}
for row in inventory['rows']:
    key=row['item']+'/'+row['profile']
    if key not in receipt['saved']:continue
    saved=receipt['saved'][key];source=R/'Authored'/row['item']/(row['profile']+'.json')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=saved['author_sha256']:raise RuntimeError('Unsaved authoring input '+key)
    recipe=changes.setdefault(row['item'],copy.deepcopy(config['items'][row['item']]))
    current=recipe['rig_meshes'][row['profile']]
    if current not in (row['asset'],saved['asset']):raise RuntimeError('Another edit changed this garment route '+key)
    recipe['rig_meshes'][row['profile']]=saved['asset'];profiles.setdefault(row['item'],[]).append(row['profile'])
for item,recipe in changes.items():text=replace(text,['items',item],recipe)
if path.read_bytes()!=raw:raise RuntimeError('Concurrent configuration edit; retry scoped merge')
backup=R/'Before/modular_outfits.json'
if not backup.exists():backup.write_bytes(raw)
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,profiles=profiles,saved_meshes=len(receipt['saved']),runtime_tested=False,materials_and_motion_preserved=True),indent=2),encoding='utf-8')
print('GARMENT_SLEEVES_PUBLISHED',len(receipt['saved']),flush=True)
