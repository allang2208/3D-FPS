"""Save the five authored combo/recovery roles for each native body."""
import json,hashlib
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3'
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
receipt_path=OUT/'assets-saved.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(complete=False,bodies={},runtime_tested=False)
receipt['complete']=False
for body in ('jason','kaitlin'):
    source_bytes=(OUT/(body+'-actions.json')).read_bytes()
    source_hash=hashlib.sha256(source_bytes).hexdigest()
    data=json.loads(source_bytes)
    mesh=u.load_asset(data['mesh'])
    factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
    saved=receipt['bodies'].setdefault(body,dict(mesh=mesh.get_path_name(),clips={}))
    hashes=saved.setdefault('source_hashes',{})
    folder=DEST+'/'+body.capitalize()+'/Animations'
    for label,c in data['clips'].items():
        role='Kukri.FullBody.'+label;name='A_KukriCombo_'+label;path=folder+'/'+name
        exists=lib.does_asset_exist(path)
        if role in saved['clips'] and hashes.get(role)==source_hash and exists:continue
        if exists and role not in saved['clips']:raise RuntimeError('Unreceipted package exists: '+path)
        clip=u.load_asset(path) if exists else assets.create_asset(name,folder,u.AnimSequence,factory)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Initialize failed '+path)
        ctl=clip.get_editor_property('controller');ctl.open_bracket('Kukri native combo '+label,False)
        try:
            ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
            ctl.set_number_of_frames(u.FrameNumber(len(c['frames'])-1),False)
            for j,bone in enumerate(data['names']):
                ctl.add_bone_curve(bone,False);keys=[f[j] for f in c['frames']]
                if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                    raise RuntimeError('Track creation failed '+bone)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate failed '+path)
        finally:ctl.close_bracket(False)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
        if exists:u.AnimationLibrary.remove_all_animation_sync_markers(clip)
        else:u.AnimationLibrary.add_animation_notify_track(clip,'KukriComboTiming')
        for marker,fraction in [('Contact',c['contact']),('Release',c['release']),('NativeSwordGrip',0.)]:
            u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'KukriComboTiming')
        for key,value in dict(SourceAnimation=c['source'],SourceRange=json.dumps(c['source_range']),Adaptation=c['adaptation'],
            AuthoringScript='SourceAssets/KukriThirdPerson20261024/ComboV3/author.py',SourceLicense='Quaternius UAL2 CC0; original authored thrust, no commercial asset').items():
            lib.set_metadata_tag(clip,key,value)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+path)
        if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
        saved['clips'][role]=clip.get_path_name()
        hashes[role]=source_hash
        receipt_path.write_text(json.dumps(receipt,indent=2))
        print('KUKRI_COMBO_SAVED '+body+' '+role,flush=True)
receipt['complete']=True;receipt_path.write_text(json.dumps(receipt,indent=2))
print('KUKRI_COMBO_SAVE_COMPLETE',flush=True)
