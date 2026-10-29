"""Save owned native dual combat sequences; run in the serialized UE bridge."""
import hashlib,json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
OWNER='SourceAssets/KukriDualFree3D20261029/SecondAttackV2/author.py'
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3'
lib=u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End active PIE before saving dual combat assets')
receipt=json.loads((OUT/'assets-saved.json').read_text()) if (OUT/'assets-saved.json').exists() else dict(complete=False,bodies={},runtime_tested=False)
receipt['complete']=False
for label in (BODY_LABEL,):
    raw=(OUT/(label+'-actions.json')).read_bytes();data=json.loads(raw);sha=hashlib.sha256(raw).hexdigest()
    mesh=u.load_asset(data['mesh']);factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
    folder=DEST+'/'+label.capitalize()+'/Animations/DualFree3DSecondV220261029'
    body=receipt['bodies'].setdefault(label,dict(mesh=mesh.get_path_name(),clips={},saved_roles=[],source_sha256=sha))
    if body['source_sha256']!=sha:raise RuntimeError('Author bytes changed after asset creation')
    for role,c in data['clips'].items():
        name='A_Kukri_'+role.replace('.','_')+'_Free3DSecondV2';path=folder+'/'+name
        if lib.does_asset_exist(path):
            clip=u.load_asset(path)
            if body['clips'].get('Kukri.FullBody.'+role)!=clip.get_path_name() or lib.get_metadata_tag(clip,'AuthoringScript')!=OWNER:
                raise RuntimeError('Package is not owned by this author: '+path)
        else:
            clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
            lib.set_metadata_tag(clip,'AuthoringScript',OWNER)
            body['clips']['Kukri.FullBody.'+role]=clip.get_path_name()
            (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
        clip.set_retarget_source_asset(mesh);clip.update_retarget_source_asset_data()
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Initialize failed '+path)
        ctl=clip.get_editor_property('controller');tracks={str(n).casefold() for n in u.AnimationLibrary.get_animation_track_names(clip)}
        ctl.open_bracket('Free3D source dual combat / '+role,False)
        try:
            ctl.set_frame_rate(u.FrameRate(c['rate_num'],c['rate_den']),False)
            ctl.set_number_of_frames(u.FrameNumber(len(c['frames'])-1),False)
            for i,bone in enumerate(data['names']):
                if bone.casefold() not in tracks:ctl.add_bone_curve(bone,False)
                keys=[f[i] for f in c['frames']]
                if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):raise RuntimeError('Track failed '+bone)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate failed '+path)
        finally:ctl.close_bracket(False)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
        if 'DualKukriTiming' not in {str(n) for n in u.AnimationLibrary.get_animation_notify_track_names(clip)}:
            u.AnimationLibrary.add_animation_notify_track(clip,'DualKukriTiming')
        markers={str(m.marker_name) for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
        times={'Contact':c['contact']*clip.get_play_length(),'Release':c['release']*clip.get_play_length(),'NativeSwordGrip':0.,'KukriDualAuthorClock':0.}
        if c.get('offhand_contact'):times.update(OffhandContact=c['offhand_contact'][0],OffhandRelease=c['offhand_contact'][1])
        for marker,time in times.items():
            if marker not in markers:u.AnimationLibrary.add_animation_sync_marker(clip,marker,time,'DualKukriTiming')
        for key,value in dict(SourceAnimation=c['source'],Adaptation=c['adaptation'],AuthoringScript=OWNER,
            SourceLicense='Free3D.jp commercially usable humanoid animation per source page; original source in SourceAssets/DualBladeSourceSearch20261029').items():lib.set_metadata_tag(clip,key,value)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
        if role not in body['saved_roles']:body['saved_roles'].append(role)
        (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
        print('DUAL_FREE3D_SECOND_V2_SAVED',label,role,flush=True)
receipt['complete']=all(len(receipt['bodies'].get(label,{}).get('saved_roles',[]))==1 for label in ('jason','kaitlin'))
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
print('DUAL_FREE3D_SECOND_V2_SAVE_COMPLETE',receipt['complete'],flush=True)
