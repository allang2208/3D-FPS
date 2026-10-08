"""Read the installed garment's bone frames and collision sizes, without simulation."""
from pathlib import Path
import unreal as u,json
out=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/GarmentRepairV13');out.mkdir(exist_ok=True)
cdo=u.get_default_object(u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate').generated_class())
mesh=cdo.get_editor_property('visual_mesh')
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.incorporate_root_motion_into_pose=False
pose=u.AnimPoseExtensions.get_anim_pose_at_time(cdo.get_editor_property('idle_clip'),0,options)
report={'mesh':mesh.get_path_name(),'bones':{},'cloth':[]}
for name in ('root','body','body_front','body_rear','leg_L2_upper','leg_R4_upper','attack_tentacle_00'):
    transform=u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)
    report['bones'][name]={'transform':str(transform),'scale':str(transform.scale3d)}
(out/'collision-before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
u.SystemLibrary.execute_console_command(None,'BoundCongregate.DescribeGarments '+mesh.get_path_name()+' '+str(out/'garment-data-before.txt'))
print(json.dumps(report),flush=True)
