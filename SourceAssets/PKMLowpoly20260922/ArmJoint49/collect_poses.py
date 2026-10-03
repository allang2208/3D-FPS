import json
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;OUT=HERE/'Inputs'
d=json.loads((OUT/'BarePalmV7.json').read_text())
mesh=u.load_asset(d['asset']);names=[n for n in d['bones'] if n.endswith('_l')]
manifest=json.loads((HERE.parent/'LeftArm48/track_manifest.json').read_text())
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
poses={}
for entry in manifest:
    anim=u.load_asset(entry['asset'])
    if not anim:raise RuntimeError(entry['asset'])
    count=anim.get_editor_property('data_model_interface').get_number_of_keys()
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.RAW
    rows=[]
    for i in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,anim.get_play_length()*i/max(1,count-1),opt)
        rows.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
    poses[anim.get_name()]={'asset':anim.get_path_name(),'duration':anim.get_play_length(),'frames':rows,
       'revision':u.EditorAssetLibrary.get_metadata_tag(anim,'PKMLeftArmRevision')}
(OUT/'poses.json').write_text(json.dumps(poses,separators=(',',':')),encoding='utf-8')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
state={'world_path':world.get_path_name() if world else None,'in_pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
(OUT/'editor_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('ARM_JOINT_POSES',len(poses),state)
