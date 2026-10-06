"""Register owner-only torso sections without changing world/hand equipment rigs."""
import importlib.util,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/OwnerBodyShared20261005';D=P/'Content/ColdSteelData'
spec=importlib.util.spec_from_file_location('shared_body_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_shirts.json').read_text());paths=[D/'player_body.json',D/'modular_outfits.json']
# The original receipt retains the rig/source contract only. Whole-face assets
# are retired; continuous shoulders are required, never an optional fallback.
shoulders=P/'SourceAssets/SleeveSpikeRepair20261006/saved_shoulders.json'
continuous=json.loads(shoulders.read_text(encoding='utf-8'))
if set(continuous)!=set(saved['shirts']):raise RuntimeError('All owner shirts require continuous shoulder assets')
for definition,shirt in continuous.items():
    if saved['shirts'][definition]['source']!=shirt['source']:
        raise RuntimeError('Continuous shoulder source differs; rebase owner authoring first: '+definition)
    saved['shirts'][definition]=shirt
raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];body,outfit=[json.loads(t) for t in texts]
profile=body['body_mesh'];rig=saved['rig']
if profile!=saved['world_profile']:raise RuntimeError('World body changed while making owner shirts; retain assets and rebase first')
for definition,shirt in saved['shirts'].items():
    if outfit['items'][definition]['rig_meshes'].get(rig)!=shirt['source']:raise RuntimeError('World shirt changed during owner section authoring: '+definition)
hidden=[0,1,2,5,6]
settings=dict(mode='shared_world_pose',camera_forward_cm=56.,camera_crouch_forward_cm=62.,look_down_forward_cm=12.,look_down_drop_cm=0.,torso_front_clearance_cm=40.)
# Rebuilding clothing must not reset camera tuning or discard new settings.
settings.update(body.get('first_person_body',{}))
settings['mode']='shared_world_pose'
def set_entry(text,path,key,value):
    try:entries.span(text,path+[key])
    except KeyError:return entries.insert(text,path,key,value)
    return entries.replace(text,path+[key],value)
btext=set_entry(texts[0],[],'first_person_body',settings)
# Keep these compatibility pointers meaningful for older authoring readers.
btext=set_entry(btext,[],'first_person_lower_body_mesh',profile)
btext=set_entry(btext,[],'first_person_hidden_materials',hidden)
otext=set_entry(texts[1],['profiles',profile],'owner_body_hidden_materials',hidden)
for definition,shirt in saved['shirts'].items():
    recipe=outfit['items'][definition]
    meshes=dict(recipe.get('owner_body_meshes',{}));meshes[rig]=shirt['mesh']
    slots=dict(recipe.get('owner_body_hidden_materials',{}));slots[rig]=shirt['hidden_materials']
    otext=set_entry(otext,['items',definition],'owner_body_meshes',meshes)
    otext=set_entry(otext,['items',definition],'owner_body_hidden_materials',slots)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Shared configuration changed during publication; no writes made')
for path,before,result in zip(paths,raw,[btext,otext]):
    (R/('before-publish-'+path.name)).write_bytes(before)
    path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+result.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(body_mesh=profile,owner_settings=settings,hidden_base_materials=hidden,shirts=saved['shirts'],world_pose_authority=True,hand_rigs_changed=False,world_rigs_changed=False,runtime_tested=False),indent=2),encoding='utf-8')
print('OWNER_SHARED_BODY_PUBLISHED',flush=True)
