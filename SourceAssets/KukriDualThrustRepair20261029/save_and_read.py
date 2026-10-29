"""Save the two owned takes, then read compressed samples in the same UE batch."""
import json,runpy
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
checks=json.loads((OUT/'source-checks.json').read_text())
if checks['failures']:raise RuntimeError('Resolve source checks before saving')
runpy.run_path(str(OUT/'save_assets.py'),run_name='__main__')
receipt=json.loads((OUT/'assets-saved.json').read_text());result={}
for label,b in receipt['bodies'].items():
    source=json.loads((OUT/(label+'-actions.json')).read_text())
    mesh=u.load_asset(source['mesh']);opts=u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    result[label]={'mesh':source['mesh'],'clips':{}}
    for role,path in b['clips'].items():
        clip=u.load_asset(path);length=clip.get_play_length();frames=[]
        for k in range(round(length*120)+1):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(k/120,length),opts);f=[]
            for name in source['names']:
                v=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)
                f.append([v.translation.x,v.translation.y,v.translation.z,v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w,v.scale3d.x,v.scale3d.y,v.scale3d.z])
            frames.append(f)
        result[label]['clips'][role]={'asset':path,'duration':length,'skeleton_matches':clip.get_editor_property('skeleton')==mesh.skeleton,
            'markers':{str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)},'frames':frames}
    (OUT/'saved-poses.json').write_text(json.dumps(result,separators=(',',':')))
    print('THRUST_SAVED_READBACK',label,flush=True)
