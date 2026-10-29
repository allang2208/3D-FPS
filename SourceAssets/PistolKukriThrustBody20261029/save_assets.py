"""Save the two native offhand thrust takes; existing packages stay intact."""
import hashlib
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3'
lib=u.EditorAssetLibrary
receipt=dict(complete=False,bodies={},runtime_tested=False)
for label in ('jason','kaitlin'):
    raw=(OUT/(label+'-actions.json')).read_bytes();data=json.loads(raw);mesh=u.load_asset(data['mesh'])
    receipt['bodies'][label]=dict(mesh=data['mesh'],clips={},source_sha256=hashlib.sha256(raw).hexdigest())
    for role,c in data['clips'].items():
        folder=DEST+'/'+label.capitalize()+'/Animations/PistolKukriThrustV1'
        name='A_Pistol_KukriThrust';path=folder+'/'+name
        if lib.does_asset_exist(path):raise RuntimeError('Preserve existing candidate '+path)
        factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
        clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Initialize '+path)
        ctl=clip.get_editor_property('controller');ctl.open_bracket('Native offhand thrust and pistol clearance',False)
        try:
            ctl.set_frame_rate(u.FrameRate(c['rate_num'],c['rate_den']),False);ctl.set_number_of_frames(u.FrameNumber(len(c['frames'])-1),False)
            for i,bone in enumerate(data['names']):
                ctl.add_bone_curve(bone,False);keys=[f[i] for f in c['frames']]
                if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):raise RuntimeError('Track '+bone)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate '+path)
        finally:ctl.close_bracket(False)
        clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True);clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
        for key,value in dict(SourceAnimation=c['source'],Adaptation=c['adaptation'],
            AuthoringScript='SourceAssets/PistolKukriThrustBody20261029/author.py',SourceLicense='Existing project accepted FPS pose and native body/book carry; no new external source').items():lib.set_metadata_tag(clip,key,value)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not lib.save_loaded_asset(clip,False):raise RuntimeError('Save '+path)
        receipt['bodies'][label]['clips']['Pistol.KukriQuickCombat']=clip.get_path_name()
        (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2));print('PISTOL_KUKRI_THRUST_SAVED '+path,flush=True)
receipt['complete']=True
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
