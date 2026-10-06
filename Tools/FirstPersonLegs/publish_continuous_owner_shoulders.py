"""Publish saved owner-shoulder meshes; leave camera and weapon arm rigs intact."""
import importlib.util,json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SleeveSpikeRepair20261006'
path=P/'Content/ColdSteelData/modular_outfits.json'
spec=importlib.util.spec_from_file_location('shoulder_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_shoulders.json').read_text(encoding='utf-8'))
items=['ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt']
if set(saved)!=set(items):raise RuntimeError('All three shoulder assets must be saved before publication')
before=path.read_bytes();text=before.decode('utf-8-sig');configuration=json.loads(text)
previous={}
for item in items:
    mesh=saved[item];recipe=configuration['items'][item]
    if recipe['rig_meshes']['Jason']!=mesh['source']:raise RuntimeError('World shirt changed during authoring: '+item)
    package=P/'Content'/(mesh['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if not package.is_file():raise RuntimeError('Saved mesh package missing: '+str(package))
    previous[item]={key:recipe.get(key,{}) for key in ['owner_body_meshes','owner_body_hidden_materials']}
    for key,value in [('owner_body_meshes',mesh['mesh']),('owner_body_hidden_materials',mesh['hidden_materials'])]:
        updated=dict(recipe.get(key,{}));updated['Jason']=value
        try:entries.span(text,['items',item,key])
        except KeyError:text=entries.insert(text,['items',item],key,updated)
        else:text=entries.replace(text,['items',item,key],updated)
if path.read_bytes()!=before:raise RuntimeError('Outfit configuration changed during publication; no write made')
backup=R/'before-shoulder-publish-modular_outfits.json'
if not backup.exists():backup.write_bytes(before)
path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published_shoulders.json').write_text(json.dumps(dict(shirts=saved,previous=previous,camera_changed=False,
    weapon_rigs_changed=False,world_rigs_changed=False,runtime_tested=False),indent=2),encoding='utf-8')
print('CONTINUOUS_OWNER_SHOULDERS_PUBLISHED',flush=True)
