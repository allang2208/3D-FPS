"""Publish only the completed V5 helmet appearance; preserve item gameplay data."""
import json,shutil,importlib.util,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SteelArmet20261019';O=R/'ReferenceMatchV5';D=P/'Content/ColdSteelData';KEY='ue_steel_armet'
spec=importlib.util.spec_from_file_location('armet_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((O/'saved_assets.json').read_text())
if not saved.get('completed') or saved.get('source_revision')!='ReferenceMatchV5':raise RuntimeError('V5 packages must be saved before publication')
if saved.get('visor_sha256')!=hashlib.sha256((O/'Textures/T_SteelArmet_Visor.png').read_bytes()).hexdigest():raise RuntimeError('Saved visor does not match the final Blender output; reimport before publication')
paths=[D/'items.json',D/'player_body.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
item=dict(catalog[KEY]);item.update(world_mesh=saved['pickup'],ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=0,ue_icon='Icons/SteelArmet20261019/'+KEY+'.png')
recipe=dict(config['head_equipment'][KEY]);recipe.update(static_mesh=saved['mesh'],fits=saved['fits'],first_person_overlay=saved['visor_texture'])
out=[entries.replace(texts[0],[KEY],item),entries.replace(texts[1],['head_equipment',KEY],recipe)]
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; retry from current files')
for path,before,text in zip(paths,raw,out):
    backup=O/(path.stem+'-before.json')
    if not backup.exists():backup.write_bytes(before)
    if path.name == 'player_body.json':
        entries.commit_player_body(path,before,text,owned_paths=[('head_equipment',KEY)],producer=__file__)
    else:
        path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
folder=D/'Icons/SteelArmet20261019';folder.mkdir(parents=True,exist_ok=True)
for dest in (folder/(KEY+'.png'),D/'Icons'/(KEY+'.png')):shutil.copy2(O/(KEY+'.png'),dest)
receipt=dict(completed=True,source_revision='ReferenceMatchV5',item=item,recipe=recipe,world_routing='shared replicated head equipment identity; all weapons',owner_routing='existing owner-only overlay layer 15',runtime_tested=False)
(O/'published.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('saved_assets.json','published.json'):shutil.copy2(O/name,R/name)
authored=json.loads((O/'authored.json').read_text());authored.update(imported=True,published=True)
(O/'authored.json').write_text(json.dumps(authored,indent=2))
status=json.loads((R/'status.json').read_text())
status.update(model_revision=authored['geometry_revision'],finish_revision=authored['finish_revision'],editable=authored['editable'],fbx=authored['fbx'],triangles=authored['triangles'],parts=authored['parts'],renders=[str(p.relative_to(P)) for p in sorted((O/'Renders').glob('*.png'))],engine_assets_saved=True,catalog_published=True,runtime_tested=False,blocked_by=None,save_receipt='ReferenceMatchV5/saved_assets.json',cpp_changed=False)
for target in (O/'status.json',R/'status.json'):target.write_text(json.dumps(status,indent=2))
print('REFERENCE_ARMET_V5_PUBLISHED',flush=True)
