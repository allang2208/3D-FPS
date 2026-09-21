"""Capture the current sword grips and overhead tracks for new sprint authoring."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).parent
folders = {
    'Standard': ('/Game/Weapons/AzureRunesword20260913', '/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny'),
    'LongGrip': ('/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations', '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'),
}

def unpack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return {'p': [p.x,p.y,p.z], 'q': [q.w,q.x,q.y,q.z], 's': [s.x,s.y,s.z]}

for variant, (folder, mesh_path) in folders.items():
    mesh = u.load_asset(mesh_path)
    component = u.SkeletalMeshComponent()
    component.set_skeletal_mesh_asset(mesh)
    names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    options = u.AnimPoseEvaluationOptions()
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    options.optional_skeletal_mesh = mesh
    data = {'variant': variant, 'folder': folder, 'mesh': mesh_path,
            'parents': {n: str(component.get_parent_bone(n)) for n in names}, 'clips': {}}
    for name in ('Idle', 'Overhead'):
        path = folder+'/A_RuneSword_'+name
        asset = u.load_asset(path)
        frames, seconds = u.AnimationLibrary.get_num_frames(asset), asset.get_play_length()
        rows = []
        for i in (range(frames+1) if name == 'Overhead' else (0,)):
            time = i*seconds/frames
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
            rows.append({'seconds': time, 'world': {n: unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
        data['clips'][name] = {'asset': path, 'seconds': seconds, 'intervals': frames, 'samples': rows}
    (P/(variant+'_inputs.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    u.log('MELEE_SPRINT_SOURCE '+variant+' '+str({n: d['seconds'] for n,d in data['clips'].items()}))
