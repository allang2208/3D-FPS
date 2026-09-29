"""User-requested read-only saved-asset check. Does not spawn actors or save assets."""
import json,math
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
bp=u.load_asset('/Game/Monsters/SpitterZombie/BP_SpitterZombie')
if bp is None:raise RuntimeError('Saved Spitter blueprint is missing')
cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh')
combat=cdo.get_editor_property('combat');knockdown=cdo.get_editor_property('knockdown')
report={'inspection':'saved assets and source wiring; no gameplay simulation',
        'blueprint':bp.get_path_name(),'native_class':cdo.get_class().get_path_name(),
        'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),
        'physics_asset':mesh.physics_asset.get_path_name() if mesh.physics_asset else None,
        'knockdown_enabled':knockdown.get_editor_property('enabled'),
        'toughness_threshold':combat.get_editor_property('toughness_threshold'),
        'break_seconds':combat.get_editor_property('toughness_break_seconds'),
        'tags':[str(t) for t in cdo.tags], 'reactions':{},'gameplay_tested':False}
sources={'Stagger':(combat,'hit_clip'),'Dizzy':(combat,'dizzy_clip'),
    'Hit_Knockback':(knockdown,'fall_clip'),'LayToIdle':(knockdown,'get_up_clip'),
    'ProneToIdle':(knockdown,'prone_get_up_clip'),'Death':(cdo,'death_clip')}
for role,(owner,prop) in sources.items():
    clip=owner.get_editor_property(prop)
    if not clip:
        report['reactions'][role]={'bound':False};continue
    opts=u.AnimPoseEvaluationOptions();opts.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
    opts.set_editor_property('optional_skeletal_mesh',mesh)
    bones=['Hips','Spine02','Spine01','Spine','neck','Head','LeftArm','RightArm','LeftLeg','RightLeg']
    samples={b:[] for b in bones}
    for i in range(13):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/12.,opts)
        for bone in bones:
            t=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL)
            samples[bone].append(([t.translation.x,t.translation.y,t.translation.z],
                                  [t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]))
    moving=[];max_angle=0.
    for bone,values in samples.items():
        p0,q0=values[0];angle=0.;distance=0.
        for p,q in values[1:]:
            dot=abs(sum(a*b for a,b in zip(q0,q)))
            angle=max(angle,math.degrees(2*math.acos(min(1.,dot))))
            distance=max(distance,math.sqrt(sum((a-b)**2 for a,b in zip(p0,p))))
        max_angle=max(max_angle,angle)
        if angle>.05 or distance>.01:moving.append(bone)
    report['reactions'][role]={'bound':True,'asset':clip.get_path_name(),
        'skeleton_matches':clip.get_editor_property('skeleton')==mesh.skeleton,'seconds':clip.get_play_length(),
        'keys':clip.get_editor_property('data_model_interface').get_number_of_keys(),
        'loop':clip.get_editor_property('loop'),'moving_bones_sampled':moving,
        'max_sampled_rotation_degrees':max_angle}
try:
    report['physics_bodies']=len(mesh.physics_asset.get_editor_property('skeletal_body_setups'))
    report['physics_constraints']=len(mesh.physics_asset.get_editor_property('constraint_setup'))
except Exception as exc:report['physics_detail_read']=str(exc)
(ROOT/'basic_reactions_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_BASIC_REACTIONS_INSPECTED '+json.dumps(report,ensure_ascii=False))
