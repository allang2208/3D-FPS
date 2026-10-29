"""Save six native whirlwind sequences in existing cooked directories."""
import hashlib
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3'
lib=u.EditorAssetLibrary
previous=json.loads((OUT/'assets-saved.json').read_text()) if (OUT/'assets-saved.json').exists() else {}
receipt=previous or dict(complete=False,bodies={},runtime_tested=False)
receipt['complete']=False
for label in (BODY_LABEL,):
    source_bytes=(OUT/(label+'-actions.json')).read_bytes()
    data=json.loads(source_bytes)
    mesh=u.load_asset(data['mesh'])
    factory=u.AnimSequenceFactory()
    factory.target_skeleton=mesh.skeleton
    factory.preview_skeletal_mesh=mesh
    folder=DEST+'/'+label.capitalize()+'/Animations/WhirlwindWindmillV10'
    receipt['bodies'][label]=dict(mesh=mesh.get_path_name(),clips={},source_sha256=hashlib.sha256(source_bytes).hexdigest())
    for role,c in data['clips'].items():
        name='A_Kukri_'+role.replace('.','_')+'_WindmillMaster'
        path=folder+'/'+name
        existing=lib.does_asset_exist(path)
        if existing:
            expected=previous.get('bodies',{}).get(label,{}).get('clips',{}).get('Kukri.FullBody.'+role)
            clip=u.load_asset(path)
            if expected!=clip.get_path_name() or lib.get_metadata_tag(clip,'AuthoringScript')!='SourceAssets/KukriWindmillMaster20261026/author.py':
                raise RuntimeError('Existing package is not owned by this candidate: '+path)
        else:
            clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
        clip.set_retarget_source_asset(mesh)
        clip.update_retarget_source_asset_data()
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
            raise RuntimeError('Initialize failed '+path)
        ctl=clip.get_editor_property('controller')
        ctl.open_bracket('Continuous master timeline / supported palm '+role,False)
        try:
            ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
            ctl.set_number_of_frames(u.FrameNumber(len(c['frames'])-1),False)
            for i,bone in enumerate(data['names']):
                if not existing:ctl.add_bone_curve(bone,False)
                keys=[f[i] for f in c['frames']]
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
        u.AnimationLibrary.add_animation_notify_track(clip,'KukriWhirlwindTiming')
        for marker,fraction in [('Contact',c['contact']),('Release',c['release']),('NativeSwordGrip',0.)]:
            u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'KukriWhirlwindTiming')
        for key,value in dict(SourceAnimation=c['source'],Adaptation=c['adaptation'],
            AuthoringScript='SourceAssets/KukriWindmillMaster20261026/author.py',
            SourceLicense='Original authored curves on existing project bodies; Mabinogi footage used only as visual reference, no extracted game animation data').items():
            lib.set_metadata_tag(clip,key,value)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not lib.save_loaded_asset(clip,False):
            raise RuntimeError('Finalize/save failed '+path)
        receipt['bodies'][label]['clips']['Kukri.FullBody.'+role]=clip.get_path_name()
        (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
        print('KUKRI_WINDMILL_MASTER_SAVED '+clip.get_path_name(),flush=True)
receipt['complete']=all(len(receipt['bodies'].get(label,{}).get('clips',{}))==3 for label in ('jason','kaitlin'))
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
print('KUKRI_WINDMILL_MASTER_SAVE_COMPLETE',flush=True)
