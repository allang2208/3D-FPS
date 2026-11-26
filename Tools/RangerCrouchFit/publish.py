"""Publish only this shirt's world/owner bodies and three underlayer routes."""
import copy,hashlib,importlib.util,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021';FILE=P/'Content/ColdSteelData/modular_outfits.json'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
spec=importlib.util.spec_from_file_location('crouch_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
inputs=read(R/'inputs.json');saved=read(R/'saved_assets.json');authored=read(R/'authored.json')
if not (saved.get('completed') and authored.get('completed')):raise RuntimeError('Finish saving all five meshes first')
for row in authored['records']:
    key=row['item']+'/'+row['profile']
    if hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()!=saved['saved'][key]['author_sha256']:raise RuntimeError('Unsaved geometry '+key)
raw=FILE.read_bytes();text=raw.decode('utf-8-sig');cfg=json.loads(text);old=inputs['recipe']['ue_field_sweater'];current=cfg['items']['ue_field_sweater'];recipe=copy.deepcopy(current)
for field in ('rig_meshes','owner_body_meshes'):
    profile='Owner_Jason' if field=='owner_body_meshes' else 'Jason';path=saved['saved']['ue_field_sweater/'+profile]['asset']
    if current[field]['Jason'] not in (old[field]['Jason'],path):raise RuntimeError('Current shirt changed during repair')
    recipe[field]['Jason']=path
pants=inputs['recipe']['ue_leather_pants'];active=cfg['items']['ue_leather_pants']
for field in ('rig_meshes','shoe_fit_meshes'):
    if active.get(field)!=pants.get(field):raise RuntimeError('Pants routes changed during repair; retain current configuration')
routes={pants['rig_meshes']['Jason']:'LeatherPants'}
for item,row in pants['shoe_fit_meshes'].items():routes[row['Jason']]='LeatherPants_ShortBootsFit' if item=='ue_boots' else 'LeatherPants_HighBootsFit'
under=recipe.setdefault('underlayer_meshes',{})
for source,profile in routes.items():
    path=saved['saved']['ue_leather_pants/'+profile]['asset'];baseline=old.get('underlayer_meshes',{}).get(source)
    if source in under and under[source] not in (baseline,path):raise RuntimeError('Current underlayer changed during repair')
    under[source]=path
out=entries.replace(text,['items','ue_field_sweater'],recipe)
if FILE.read_bytes()!=raw:raise RuntimeError('Configuration changed during scoped publication; retry')
before=R/'modular_outfits_before.json'
if not before.exists():before.write_bytes(raw)
FILE.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+out.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,recipe=recipe,changed_item='ue_field_sweater',pants_standalone_unchanged=True,assets=saved['saved'],runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('RANGER_CROUCH_PUBLISHED two shirt bodies and three shirt-only underlayers',flush=True)
