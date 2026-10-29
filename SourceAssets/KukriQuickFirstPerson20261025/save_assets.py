"""Save both native uppercuts under the existing cooked animation folders."""
import hashlib
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
DEST = '/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3'
lib = u.EditorAssetLibrary
receipt = dict(complete=False,bodies={},runtime_tested=False)
for label in ('jason','kaitlin'):
    source_bytes = (OUT/(label+'-actions.json')).read_bytes()
    data = json.loads(source_bytes)
    mesh = u.load_asset(data['mesh'])
    factory = u.AnimSequenceFactory()
    factory.target_skeleton = mesh.skeleton
    factory.preview_skeletal_mesh = mesh
    folder = DEST+'/'+label.capitalize()+'/Animations/QuickFirstPersonV3'
    name = 'A_Kukri_Pommel_FirstPersonArms'
    path = folder+'/'+name
    if lib.does_asset_exist(path):
        raise RuntimeError('Candidate already exists; preserve saved asset: '+path)
    clip = u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Initialize failed '+path)
    c = data['clips']['Pommel']
    ctl = clip.get_editor_property('controller')
    ctl.open_bracket('Kukri first-person two-arm pommel transfer',False)
    try:
        ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
        ctl.set_number_of_frames(u.FrameNumber(len(c['frames'])-1),False)
        for i,bone in enumerate(data['names']):
            ctl.add_bone_curve(bone,False)
            keys = [f[i] for f in c['frames']]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                raise RuntimeError('Track failed '+bone)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
            raise RuntimeError('Populate failed '+path)
    finally:
        ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.add_animation_notify_track(clip,'KukriQuickTiming')
    for marker,fraction in [('Contact',c['contact']),('Release',c['release']),('NativeSwordGrip',0.)]:
        u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'KukriQuickTiming')
    for key,value in dict(SourceAnimation=c['source'],Adaptation=c['adaptation'],
        AuthoringScript='SourceAssets/KukriQuickFirstPerson20261025/author.py',
        SourceLicense='Existing project Kukri first-person animation; no new external motion source').items():
        lib.set_metadata_tag(clip,key,value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not lib.save_loaded_asset(clip,False):
        raise RuntimeError('Finalize/save failed '+path)
    receipt['bodies'][label] = dict(mesh=mesh.get_path_name(),clips={'Kukri.FullBody.Pommel':clip.get_path_name()},
        source_sha256=hashlib.sha256(source_bytes).hexdigest())
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
    print('KUKRI_FIRST_PERSON_QUICK_SAVED '+clip.get_path_name(),flush=True)
receipt['complete'] = True
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
print('KUKRI_FIRST_PERSON_QUICK_SAVE_COMPLETE',flush=True)
