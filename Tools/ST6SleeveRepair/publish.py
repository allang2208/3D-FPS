"""Replace ST6 first-person sleeves only after their saved family is complete."""
import json,hashlib,sys,copy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6SleeveRepair20261018';sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));from json_entries import replace
saved=json.loads((R/'saved_assets.json').read_text(encoding='utf-8'));before=json.loads((R/'before.json').read_text(encoding='utf-8'));rows=before['inventory']
if not saved.get('completed'):raise RuntimeError('Sleeve family not saved')
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');config=json.loads(text);recipe=copy.deepcopy(config['items']['ue_st6_sleeves'])
for row in rows:
    profile=row['profile'];result=saved['saved'][profile];sha=hashlib.sha256((R/'Authored'/(profile+'.json')).read_bytes()).hexdigest()
    if result['author_sha256']!=sha:raise RuntimeError('Unsaved sleeve source '+profile)
    if recipe['rig_meshes'][profile] not in (row['previous'],result['asset']):raise RuntimeError('ST6 profile changed during authoring: '+profile)
    recipe['rig_meshes'][profile]=result['asset'];recipe.get('base_material_overrides',{}).pop(profile,None)
recipe['covers']=[0,1,3];recipe['appearance_family']='ST6NativeSleeves20261018';updated=replace(text,['items','ue_st6_sleeves'],recipe)
if path.read_bytes()!=raw:raise RuntimeError('Configuration changed during scoped merge; retry')
backup=R/'Before/modular_outfits.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():backup.write_bytes(raw)
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,item='ue_st6_sleeves',profiles=[r['profile'] for r in rows],removed_native_cloth_underlayer=True,fp_covered_materials=[0,1,3],world_body_and_neck_preserved=True,runtime_tested=False),indent=2),encoding='utf-8');print('ST6_NATIVE_SLEEVES_PUBLISHED',len(rows),flush=True)
