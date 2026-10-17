"""Install only M870 quick melee and its four existing foregrip variants."""
import gzip, hashlib, json, shutil
from pathlib import Path
import unreal as u

O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary
D=json.loads((O/'animation_patch.json').read_text(encoding='utf-8'))
with gzip.open(O/'inputs.json.gz','rt',encoding='utf-8') as f:INPUT=json.load(f)['weapons']['m870']
receipt=dict(completed=False,saved=[],revision=D['revision'],runtime_tested=False,visual_accepted=False)
def record():(O/'save_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def physical(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name());record()

record()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    receipt['deferred_reason']='PIE active; no animation assets were changed';record()
    raise RuntimeError(receipt['deferred_reason'])
paths=[D['melee_path']]+[spec['path'] for spec in D['profiles'].values()]
targets={path.split('.')[0] for path in paths}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Preserve unsaved target assets: '+str(targets.intersection(dirty)))
for path in paths:
    src=physical(path)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=INPUT['source_sha256'][path]:
        raise RuntimeError('Authoring target changed after input capture; preserve '+path)
    dst=O/'Before'/src.relative_to(P);dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(src,dst)

clip=load(D['melee_path']);controller=clip.get_editor_property('controller')
controller.open_bracket('M870 native elbow hinge R3',False)
try:
    controller.set_frame_rate(u.FrameRate(D['fps'],1),False)
    controller.set_number_of_frames(u.FrameNumber(D['frames']),False)
    for track in D['base_tracks']:
        if track['bone'] not in D['write_bones']:continue
        keys=[track['values'][i:i+10] for i in range(0,len(track['values']),10)]
        if len(keys)==1:keys*=D['frames']+1
        args=(track['bone'],[u.Vector(*v[:3]) for v in keys],[u.Quat(*v[3:7]) for v in keys],[u.Vector(*v[7:]) for v in keys],False)
        if not controller.set_bone_track_keys(*args):
            controller.add_bone_curve(track['bone'],False)
            if not controller.set_bone_track_keys(*args):raise RuntimeError('Cannot write '+track['bone'])
finally:controller.close_bracket(False)
curve=D['ownership_curve']
if u.AnimationLibrary.does_curve_exist(clip,curve['name'],u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,curve['name'])
u.AnimationLibrary.add_curve(clip,curve['name'])
u.AnimationLibrary.add_float_curve_keys(clip,curve['name'],curve['times'],curve['values'])
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Cannot finalize M870 quick melee')
E.set_metadata_tag(clip,'M870QuickMeleeSource',D['revision'])
E.set_metadata_tag(clip,'M870QuickMeleeAuthoringScript',str(O/'author_elbow.py'))
source_file=O/'A_M870_QuickMelee_Elbow_R3.fbx'
import_data=clip.get_editor_property('asset_import_data')
import_data.scripted_add_filename(str(source_file),0,'M870 Quick Melee Elbow R3')
import_data.set_editor_property('use_default_sample_rate',False)
import_data.set_editor_property('custom_sample_rate',D['fps'])
save(clip)

for family,spec in D['profiles'].items():
    asset=load(spec['path']);source=INPUT['profiles'][family]
    payload=dict(family=source['family'],clips=[]);retained={};found=False
    for old in source['clips']:
        if old['base']==D['melee_path']:
            payload['clips'].append(spec['clip']);found=True
        else:
            payload['clips'].append({k:old[k] for k in ('base','duration','tracks')})
            if old['retained']:retained[old['base']]=old['retained']
    if not found:raise RuntimeError('Missing melee profile slot '+family)
    if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Cannot write profile '+family)
    if retained:
        rows=list(asset.get_editor_property('clips'))
        for i,row in enumerate(rows):
            path=row.get_editor_property('base').get_path_name()
            if path in retained:row.set_editor_property('retained',load(retained[path]));rows[i]=row
        asset.set_editor_property('clips',rows)
    E.set_metadata_tag(asset,'M870QuickMeleeSource',D['revision']+'; quick_melee entry only')
    save(asset)
receipt.update(completed=True,source_duration=D['duration'],contact_seconds=1/6,
               mesh_assets_modified=False,other_action_entries_modified=False)
record();print('M870_ELBOW_R3_SAVED',len(receipt['saved']),'assets; no gameplay test')
