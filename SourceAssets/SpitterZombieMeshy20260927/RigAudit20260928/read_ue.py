"""Read-only targeted animation/asset/current-world evidence; no spawn or save."""
import unreal as u
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bp=u.load_asset('/Game/Monsters/SpitterZombie/BP_SpitterZombie')
cdo=u.get_default_object(bp.generated_class()); mesh=cdo.get_editor_property('visual_mesh')
clips=cdo.get_editor_property('movement_clips')
speeds=list(cdo.get_editor_property('movement_reference_speeds'))
def path(a):return a.get_path_name() if a else None
def v(a):return [a.x,a.y,a.z]
def quat(a):return [a.x,a.y,a.z,a.w]
report=dict(blueprint=path(bp),mesh=path(mesh),skeleton=path(mesh.skeleton),
    animations=[path(a) for a in clips],speeds_cm_s=speeds,
    walk_speed_cm_s=cdo.get_editor_property('walk_speed'),attack=path(cdo.get_editor_property('attack_clip')),
    read_only=True,runtime=[],poses={})
try:cdo.get_editor_property('selected_movement_clip'); report['spawn_fixed_native_loaded']=True
except Exception:report['spawn_fixed_native_loaded']=False
names=['SpitterRoot','Hips','Spine02','Spine01','Spine','neck','Head','LeftShoulder','LeftArm',
 'LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand',
 'LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase']
for clip in clips:
    entry=dict(length=clip.get_play_length(),root_motion=clip.get_editor_property('enable_root_motion'),
        root_lock=clip.get_editor_property('force_root_lock'),loop=clip.get_editor_property('loop'),modes={})
    for label,mode in [('SOURCE',u.AnimDataEvalType.SOURCE),('COMPRESSED',u.AnimDataEvalType.COMPRESSED)]:
        opts=u.AnimPoseEvaluationOptions();opts.set_editor_property('evaluation_type',mode)
        opts.set_editor_property('optional_skeletal_mesh',mesh)
        frames=[]
        for i in range(17):
            t=clip.get_play_length()*i/16
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
            row={}
            for n in names:
                local=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)
                world=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
                row[n]=dict(local_q=quat(local.rotation),local_scale=v(local.scale3d),
                            local_pos_cm=v(local.translation),component_pos_cm=v(world.translation))
            frames.append(dict(t=t,bones=row))
        entry['modes'][label]=frames
    report['poses'][clip.get_name()]=entry
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=sub.get_game_world()
report['game_world']=path(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.SpitterZombie.static_class())[:12]:
        sk=actor.get_editor_property('mesh'); anim=sk.get_anim_instance()
        row=dict(actor=path(actor),state=str(actor.get_editor_property('state')),
            velocity_cm_s=v(actor.get_velocity()),selected_index=actor.get_editor_property('selected_movement_index'),
            walk_speed=actor.get_editor_property('walk_speed'),mesh_relative_scale=v(sk.get_editor_property('relative_scale3d')),
            anim_class=path(anim.get_class()) if anim else None)
        if anim:
            try:row['active_clip']=path(anim.get_editor_property('active_clip'))
            except Exception:pass
        report['runtime'].append(row)
(ROOT/'ue_read.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_RIG_AUDIT_READ '+json.dumps({k:v for k,v in report.items() if k!='poses'},ensure_ascii=False))
