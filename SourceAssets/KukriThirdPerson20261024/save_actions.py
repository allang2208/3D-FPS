"""Create and save this task's independent full-body animation packages."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/KukriThirdPerson20261024')
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024/Animations'
data=json.loads((OUT/'adapted-actions.json').read_text());mesh=u.load_asset(data['mesh'])
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
receipt=dict(complete=False,clips={},sources={},runtime_tested=False)
if (OUT/'assets-saved.json').exists():receipt=json.loads((OUT/'assets-saved.json').read_text());receipt['complete']=False
for label,c in data['clips'].items():
    role='Kukri.FullBody.'+label;name='A_KukriBody_'+label.replace('.','_');path=DEST+'/'+name
    if role in receipt['clips'] and lib.does_asset_exist(path):continue
    if lib.does_asset_exist(path):raise RuntimeError('Unreceipted package already exists: '+path)
    clip=assets.create_asset(name,DEST,u.AnimSequence,factory)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation initialization failed '+name)
    ctl=clip.get_editor_property('controller');ctl.open_bracket('Local Kukri body donor '+label,False)
    try:
        ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
        ctl.set_number_of_frames(u.FrameNumber(len(c['frames'])-1),False)
        for j,bone in enumerate(data['names']):
            ctl.add_bone_curve(bone,False);keys=[f[j] for f in c['frames']]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):raise RuntimeError('Bone authoring failed: '+bone)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate failed '+name)
    finally:ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.add_animation_notify_track(clip,'KukriTiming')
    for marker,fraction in [('Contact',c['contact']),('Release',c['release'])]:
        u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'KukriTiming')
    for key,value in dict(SourceAnimation=c['source'],SourceGroup=c['source_group'],SourceRange=json.dumps(c['source_range']),
        Adaptation=c['adaptation'],AuthoringScript='SourceAssets/KukriThirdPerson20261024/author_actions.py').items():lib.set_metadata_tag(clip,key,value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+name)
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+name)
    receipt['clips'][role]=clip.get_path_name();receipt['sources'][label]=dict(asset=c['source'],range=c['source_range'],adaptation=c['adaptation'])
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
    print('KUKRI_BODY_SAVED '+role,flush=True)
receipt['complete']=True
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
print('KUKRI_BODY_SAVE_COMPLETE',flush=True)
