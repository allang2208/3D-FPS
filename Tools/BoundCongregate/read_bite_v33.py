"""User-requested bite timing/range diagnosis; read compressed pose and defaults."""
from pathlib import Path
import unreal as u, json, math
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/BiteV33');OUT.mkdir(exist_ok=True)
cdo=u.get_default_object(u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate').generated_class())
mesh=cdo.get_editor_property('visual_mesh');clip=cdo.get_editor_property('bite_clip')
result=dict(mesh=mesh.get_path_name(),clip=clip.get_path_name(),duration=clip.get_play_length(),
    tuning={k:float(cdo.get_editor_property(k)) for k in ('mesh_yaw','bite_trigger_range','bite_reach','bite_contact_seconds','bite_damage','bite_cooldown')},samples=[])
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.COMPRESSED
options.incorporate_root_motion_into_pose=False;options.optional_skeletal_mesh=mesh
yaw=math.radians(result['tuning']['mesh_yaw'])
for t in (0.,.3,.42,.48,.50,.52,.54,.56,.58,.60,.62,.65,.70,.79):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
    row=dict(time=t)
    for bone in ('body','maw','jaw_L','jaw_R'):
        p=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD).translation
        row[bone]=[math.cos(yaw)*p.x-math.sin(yaw)*p.y,math.sin(yaw)*p.x+math.cos(yaw)*p.y,p.z]
    result['samples'].append(row)
(OUT/'before-pose.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('M88_BITE_DIAGNOSIS '+json.dumps(result),flush=True)
