"""Save only third-person dual-heavy repairs and combo clips (user correction).

First-person Arms changes were withdrawn; do not publish the archived candidate.
"""
import json, runpy, shutil
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
DEST='/Game/Weapons/TacticalHatchet20261101/DualChopRepair20261106'
roles=['DualCharge','DualRelease','Combo3']
targets=[]
for label in ('Jason','Kaitlin'):
    src=json.loads((P/(label+'-source.json')).read_text())
    targets.extend([src['clips'][r]['path'].split('.')[0] for r in roles[:2]])
    targets.append(DEST+'/'+label+'/A_HatchetDualCombo3')
dirty={a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(targets):raise RuntimeError('Unsaved target animation: '+str(dirty.intersection(targets)))
for path in targets:
    disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if disk.exists():
        backup=P/'Before'/(path.removeprefix('/Game/')+'.uasset')
        if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
receipt={}
for label in ('Jason','Kaitlin'):
    data=json.loads((P/(label+'-moves.json')).read_text());source=json.loads((P/(label+'-source.json')).read_text())
    mesh=u.load_asset(data['mesh']);factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
    receipt[label]={}
    for role,frames in data['clips'].items():
        path=DEST+'/'+label+'/A_HatchetDualCombo3' if role=='Combo3' else source['clips'][role]['path'].split('.')[0]
        folder,name=path.rsplit('/',1)
        clip=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
        if not clip:raise RuntimeError(path)
        clip.set_retarget_source_asset(mesh);clip.update_retarget_source_asset_data()
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError(path)
        # Set the compression rate before closing the populated bracket: 2.05 s
        # has 123 frames at 60 Hz, but a half-frame remainder at the default 30 Hz.
        clip.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(data['fps'],1))
        controller=clip.get_editor_property('controller');tracks={str(x).casefold() for x in u.AnimationLibrary.get_animation_track_names(clip)}
        controller.open_bracket('Dual hatchet chop and anatomical elbow roll',False)
        try:
            controller.set_frame_rate(u.FrameRate(data['fps'],1),False)
            controller.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
            for i,bone in enumerate(data['names']):
                if bone.casefold() not in tracks:controller.add_bone_curve(bone,False)
                keys=[frame[i] for frame in frames]
                if not controller.set_bone_track_keys(bone,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):raise RuntimeError(bone)
        finally:controller.close_bracket(False)
        clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        if role=='Combo3':
            if 'ComboContacts' not in {str(t) for t in u.AnimationLibrary.get_animation_notify_track_names(clip)}:u.AnimationLibrary.add_animation_notify_track(clip,'ComboContacts')
            for marker,time in [('ContactIn',.54),('Impact',.60),('ContactOut',.72)]:
                u.AnimationLibrary.remove_animation_sync_markers_by_name(clip,marker)
                u.AnimationLibrary.add_animation_sync_marker(clip,marker,time,'ComboContacts')
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
        receipt[label][role]=dict(asset=clip.get_path_name(),length=clip.get_play_length(),frames=len(frames))
    (P/'saved-assets.json').write_text(json.dumps(receipt,indent=2),'utf8')
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'))
key='Kukri.Hatchet.DualChop'
candidate['clips'][key]=receipt['Jason']['Combo3']['asset']
candidate['body_variants']['kaitlin']['clips'][key]=receipt['Kaitlin']['Combo3']['asset']
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
config_receipt=commit(path,before,candidate,owned_paths=[('clips',key),('body_variants','kaitlin','clips',key)],producer=__file__)
(P/'config-receipt.json').write_text(json.dumps(config_receipt,indent=2,default=str),'utf8')
u.log('HATCHET_DUAL_ASSETS_SAVED count=6 third_person_only')
