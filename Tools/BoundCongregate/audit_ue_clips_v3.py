"""Read all seven actual UE compressed clips; no world or asset mutation."""
from pathlib import Path
import unreal as u, math, json
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3')
cdo=u.get_default_object(u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate').generated_class())
options=u.AnimPoseEvaluationOptions()
options.evaluation_type=u.AnimDataEvalType.COMPRESSED
options.incorporate_root_motion_into_pose=False
options.optional_skeletal_mesh=cdo.get_editor_property('visual_mesh')
report={}
for key in ('idle_clip','move_clip','turn_left_clip','turn_right_clip','bite_clip','hit_clip','death_clip'):
    clip=cdo.get_editor_property(key);duration=clip.get_play_length();samples=round(duration*60)
    frames=[];names=[]
    for i in range(samples+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/samples,options)
        if not names:names=u.AnimPoseExtensions.get_bone_names(pose)
        row=[]
        for name in names:
            t=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)
            p=t.translation;q=t.rotation
            row.append(([p.x,p.y,p.z],[q.x,q.y,q.z,q.w]))
        frames.append(row)
    bones={}
    for b,n in enumerate(names):
        steps=[];angles=[]
        for i in range(samples):
            p,q=frames[i][b];pp,qq=frames[i+1][b]
            steps.append(math.dist(p,pp));angles.append(math.degrees(2*math.acos(min(1,abs(sum(x*y for x,y in zip(q,qq)))))))
        first,last=frames[0][b],frames[-1][b]
        bones[str(n)]=dict(max_step_cm=max(steps),max_rotation_deg=max(angles),loop_cm=math.dist(first[0],last[0]),
            loop_degrees=math.degrees(2*math.acos(min(1,abs(sum(x*y for x,y in zip(first[1],last[1])))))))
    report[key]=dict(asset=clip.get_path_name(),duration=duration,bones=bones)
    print('COMPRESSED_CLIP_AUDITED',key,duration,len(names))
(OUT/('ue_compressed_after.json' if '/RigV3/' in cdo.get_editor_property('visual_mesh').get_path_name() else 'ue_compressed_before.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ALL_COMPRESSED_CLIPS_AUDITED')
