"""Read current saved thrusts and joins through the existing UE bridge."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
status={'pie_active':level.is_in_play_in_editor(),'editor_started_by_task':False}
(OUT/'editor-state.json').write_text(json.dumps(status,indent=2))
result={}
for label in ('jason','kaitlin'):
    active=cfg if label=='jason' else cfg['body_variants'][label]
    mesh=u.load_asset(active['body_mesh'])
    names=json.loads((ROOT/'SourceAssets/KukriDualFree3D20261029'/(label+'-actions.json')).read_text())['names']
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    result[label]={'mesh':active['body_mesh'],'names':names,'clips':{},'previous_roles':{}}
    for role in ('Kukri.FullBody.Thrust','Kukri.FullBody.Dual.Thrust','Kukri.FullBody.Dual.Idle','Kukri.FullBody.Dual.Slash2'):
        path=active['clips'][role];clip=u.load_asset(path);length=clip.get_play_length()
        count=round(length*120)+1;frames=[]
        for k in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(k/120,length),opts);f=[]
            for name in names:
                v=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)
                f.append([v.translation.x,v.translation.y,v.translation.z,v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w,v.scale3d.x,v.scale3d.y,v.scale3d.z])
            frames.append(f)
        markers={str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
        result[label]['clips'][role]={'asset':path,'duration':length,'rate':120,'frames':frames,'markers':markers}
        result[label]['previous_roles'][role]=path
        print('THRUST_INPUT',label,role,len(frames),flush=True)
    (OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('THRUST_READ_COMPLETE',status,flush=True)
