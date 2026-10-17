"""Read actual saved assets/retarget settings without starting gameplay."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'V18CoupledLocomotion';(P/'Records').mkdir(parents=True,exist_ok=True);(P/'Motion').mkdir(exist_ok=True)
bp=u.load_asset('/Game/Monsters/NightWarden/BP_NightWarden');cdo=u.get_default_object(bp.generated_class())
component=cdo.get_editor_property('mesh');mesh=component.get_skeletal_mesh_asset();clip=cdo.get_editor_property('walk_clip')
bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
def pack(t):return {'p':[t.translation.x,t.translation.y,t.translation.z],'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
report={'active_mesh':mesh.get_path_name(),'active_walk':clip.get_path_name(),'anim_class':component.get_editor_property('anim_class').get_path_name(),
    'mesh_relative_transform':str(component.get_relative_transform()),'actor_scale':list(cdo.get_actor_scale3d().to_tuple()),
    'source_walk_speed':cdo.get_editor_property('source_walk_speed'),'walk_speed':cdo.get_editor_property('walk_speed'),
    'rate_scale':clip.get_editor_property('rate_scale'),'enable_root_motion':clip.get_editor_property('enable_root_motion'),
    'duration':clip.get_play_length(),'bone_count':len(bones),'game_started':False}
for label,eval_type in [('raw',u.AnimDataEvalType.RAW),('compressed',u.AnimDataEvalType.COMPRESSED)]:
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=eval_type;options.optional_skeletal_mesh=mesh
    frames=[]
    for i in range(round(clip.get_play_length()*60)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,clip.get_play_length()),options)
        frames.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones})
    (P/('Motion/installed_'+label+'.json')).write_text(json.dumps({'clip':clip.get_path_name(),'fps':60,'frames':frames}),encoding='utf-8')
rt=u.load_asset('/Game/Monsters/NightWarden/V07WaistStride/RampageBipedV17/Rig/RTG_NW17_RampageBiped')
ctl=u.IKRetargeterController.get_controller(rt);report['retarget_ops']=[]
for i in range(ctl.get_num_retarget_ops()):
    op=ctl.get_op_controller(i)
    report['retarget_ops'].append({'type':op.get_class().get_name(),'settings':str(op.get_settings()) if hasattr(op,'get_settings') else None})
report['plant_curves']={name:[list(values) for values in u.AnimationLibrary.get_float_keys(clip,name)] for name in ['NW_Plant_L','NW_Plant_R']}
report['bone_compression_settings']=clip.get_editor_property('bone_compression_settings').get_path_name()
report['allow_frame_stripping']=clip.get_editor_property('allow_frame_stripping')
report['platform_target_frame_rate']=str(clip.get_editor_property('platform_target_frame_rate').get_editor_property('default'))
report['pie']=False
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():report['pie']=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
(P/'Records/installed_snapshot.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NW18_INSTALLED_STATE '+json.dumps({k:v for k,v in report.items() if k not in ['retarget_ops','plant_curves']}))
