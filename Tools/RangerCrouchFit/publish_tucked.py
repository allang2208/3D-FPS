"""Publish exactly one shirt/pants pairing; all ordinary meshes stay unchanged."""
import copy,hashlib,importlib.util,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021/TuckedPairV2';FILE=P/'Content/ColdSteelData/modular_outfits.json'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
spec=importlib.util.spec_from_file_location('tucked_scoped_json',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
inputs=read(R/'inputs.json');saved=read(R/'saved_assets.json');authored=read(R/'authored.json')
if not saved.get('completed'):raise RuntimeError('Finish saving both pair meshes')
for row in authored['records']:
    record=saved['saved']['ue_field_sweater/'+row['profile']]
    if hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()!=record['author_sha256']:raise RuntimeError('Unsaved tucked geometry '+row['profile'])
raw=FILE.read_bytes();text=raw.decode('utf-8-sig');cfg=json.loads(text);recipe=copy.deepcopy(cfg['items']['ue_field_sweater']);baseline=inputs['recipe']['ue_field_sweater']
for field in ('rig_meshes','owner_body_meshes'):
    if recipe[field]['Jason']!=baseline[field]['Jason']:raise RuntimeError('Current shirt base changed during repair')
for field in ('rig_meshes','shoe_fit_meshes'):
    if cfg['items']['ue_leather_pants'].get(field)!=inputs['recipe']['ue_leather_pants'].get(field):raise RuntimeError('Current trouser reference changed during repair')
paired=dict(rig_meshes={'Jason':saved['saved']['ue_field_sweater/Jason']['asset']},owner_body_meshes={'Jason':saved['saved']['ue_field_sweater/Owner_Jason']['asset']})
old=recipe.setdefault('pants_fit_meshes',{}).get('ue_leather_pants')
if old is not None and old!=paired:raise RuntimeError('Another leather trouser pairing already exists; retain it')
recipe['pants_fit_meshes']['ue_leather_pants']=paired;out=entries.replace(text,['items','ue_field_sweater'],recipe)
if FILE.read_bytes()!=raw:raise RuntimeError('Configuration changed during scoped publication')
before=R/'modular_outfits_before.json'
if not before.exists():before.write_bytes(raw)
FILE.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+out.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,item='ue_field_sweater',paired_pants='ue_leather_pants',pair=paired,default_meshes_unchanged=True,pants_assets_unchanged=True,owner_and_world=True,fp_arms_unchanged=True,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('RANGER_TUCKED_PAIR_PUBLISHED',json.dumps(paired),flush=True)
