"""Bake melee support using M07's actual idle knee plane and joint rotations.

V30's upper-body rotations, timing and separate claw contact remain the source.
The idle leg is transported as one anatomical plane; the calf receives only
flexion about that plane's hinge. No global forward pole or tibial roll solve.
"""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Quaternion, Vector
sys.path.insert(0, str(Path(__file__).parent))
import author_support_hover_v30 as support
base = support.base

OUT = base.ROOT/'IdleLegSupportV32/Motion'
SOURCE = base.ROOT/'SupportHoverV30/Motion/support_hover_manifest_v30.json'
FPS = 60


def reference(idle, side):
    hip, knee, ankle = [idle[n+'_'+side].translation.copy() for n in ('thigh','calf','foot')]
    upper, lower = knee-hip, ankle-knee
    u, l = upper.normalized(), lower.normalized()
    axis = (ankle-hip).normalized()
    # Preserve the creature's idle bend sign. A human-forward pole would
    # move this rig's knee to the opposite side of the hip/ankle line.
    hinge = u.cross(l).normalized()
    pole = (upper-axis*upper.dot(axis)).normalized()
    return dict(upper_length=upper.length, lower_length=lower.length,
                u=u, axis=axis, hinge=hinge, pole=pole, flexion=u.angle(l),
                thigh_q=idle['thigh_'+side].to_quaternion(),
                calf_q=idle['calf_'+side].to_quaternion())


def solve(pose, idle, d, local, side):
    thigh, calf, foot, ball = [n+'_'+side for n in ('thigh','calf','foot','ball')]
    hip, ankle = pose[thigh].translation.copy(), pose[foot].translation.copy()
    axis = (ankle-hip).normalized()
    distance = (ankle-hip).length
    a, b = d['upper_length'], d['lower_length']
    # Shortest transport keeps the entire idle knee plane together instead
    # of finding a fresh pole/roll independently at each joint or frame.
    transport = d['axis'].rotation_difference(axis)
    pole, hinge = transport@d['pole'], transport@d['hinge']
    along = (a*a-b*b+distance*distance)/(2.*distance)
    offset = math.sqrt(max(0.,a*a-along*along))
    knee = hip+axis*along+pole*offset
    u, l = (knee-hip).normalized(), (ankle-knee).normalized()
    upper_before = transport@d['u']
    angle = math.atan2(hinge.dot(upper_before.cross(u)), upper_before.dot(u))
    whole_leg = Quaternion(hinge,angle)@transport
    flexion = math.atan2(hinge.dot(u.cross(l)), u.dot(l))
    thigh_q = whole_leg@d['thigh_q']
    calf_q = whole_leg@Quaternion(d['hinge'],flexion-d['flexion'])@d['calf_q']
    pose[thigh] = base.matrix(hip,thigh_q)
    # Use actual FK offsets: export intentionally removes non-root location
    # keys, so fixed-length translations must agree with the joint rotations.
    pose[calf] = base.matrix(pose[thigh]@local[calf].translation,calf_q)
    foot_q, ball_q = pose[foot].to_quaternion(),pose[ball].to_quaternion()
    pose[foot] = base.matrix(pose[calf]@local[foot].translation,foot_q)
    pose[ball] = base.matrix(pose[foot]@local[ball].translation,ball_q)
    return math.degrees(flexion)


def soft_positive(value, width=1.):
    if value <= 0.:
        return 0.
    if value >= width:
        return value-width*.5
    return value*value/(2.*width)


def pose_at(source, idle, refs, local):
    pose = {n:m.copy() for n,m in source.items()}
    idle_root, old_root = idle['pelvis'].translation,source['pelvis'].translation
    displacement = old_root-idle_root
    # The library torso still winds up and strikes with its original angles.
    # A planted long-legged stance needs much less root translation than the
    # donor's stepping attack; retain its timing with a small weight transfer.
    root = idle_root+Vector((.30*displacement.x,.30*displacement.y,.20*displacement.z))
    delta = root-old_root
    legs = {'foot_l','foot_r','ball_l','ball_r'}
    for n,m in pose.items():
        if n not in legs:
            m.translation += delta
    # Keep both planted ankles reachable with flexion reserve. This is a
    # continuous authoring correction, not a runtime IK pass or foot clamp.
    drop = 0.
    for side in ('l','r'):
        d = refs[side]
        a,b = d['upper_length'],d['lower_length']
        reach2 = a*a+b*b+2*a*b*math.cos(math.radians(28.))
        hip,ankle = pose['thigh_'+side].translation,pose['foot_'+side].translation
        horizontal2 = (hip.x-ankle.x)**2+(hip.y-ankle.y)**2
        limit = ankle.z+math.sqrt(max(1.,reach2-horizontal2))
        drop += soft_positive(hip.z-limit+1.-drop)
    if drop:
        for n,m in pose.items():
            if n not in legs:
                m.translation.z -= drop
    flexion = {s:solve(pose,idle,refs[s],local,s) for s in ('l','r')}
    return pose,dict(knee_flexion_degrees=flexion,pelvis_support_drop_cm=drop)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=source['source'])
    rig = base.v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive))
    hidden = {o.name:o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for n in hidden:
        bpy.data.objects[n].hide_viewport = True
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local = {p.name:rest[p.parent.name].inverted()@rest[p.name] if p.parent else rest[p.name].copy() for p in ordered}
    idle = base.v17.cache_action(rig,bpy.data.actions['A_M07_Idle_PalmArmV20'],1,ordered)[0]
    refs = {s:reference(idle,s) for s in ('l','r')}
    cached = {r:base.v17.cache_action(rig,bpy.data.actions[source['clips'][r]['action']],
              source['clips'][r]['frames'],ordered) for r in ('SweepLeft','SweepRight')}
    scene = bpy.context.scene
    scene.render.fps,scene.render.fps_base = FPS,1.
    scene.unit_settings.system,scene.unit_settings.scale_length = 'METRIC',.01
    manifest = dict(revision='IdleLegSupportV32',fps=FPS,source=str(OUT/'M07_IdleLegSupport_V32.blend'),
        source_manifest=str(SOURCE),idle_reference_action='A_M07_Idle_PalmArmV20',
        idle_reference_asset='/Game/Monsters/BlindSupplicantM07/AnimationsPalmArmV20/A_M07_Idle',
        idle_knee_flexion_degrees={s:math.degrees(refs[s]['flexion']) for s in refs},
        pelvis_translation_scale=dict(horizontal=.30,vertical=.20),clips={},
        policy='Idle knee bend sign and plane retained; one whole-leg transport and one calf hinge; source upper rotations and claw goals retained',
        melee_contact_seconds=.60,melee_duration_seconds=2.,geometry_modified=False,
        weights_modified=False,native_code_modified=False,new_runtime_ik=False,
        source_saved=False,animation_fbx_exported=False,ue_imported=False,ue_saved=False,
        tested=False,runtime_tested=False,rendered=False,user_review_pending=True)
    actions = {}
    for role,frames in cached.items():
        action = bpy.data.actions.new('A_M07_'+role+'_IdleLegSupportV32')
        action.use_fake_user = True
        base.motion.activate(rig,action)
        previous,records = {},[]
        for i,src in enumerate(frames):
            pose,info = pose_at(src,idle,refs,local)
            scene.frame_set(i+1)
            base.running.insert_frame(rig,pose,rest,ordered,i+1,previous)
            records.append(info)
        scene.frame_set(0)
        for bone in ordered:
            bone.matrix_basis = Matrix.Identity(4)
            for prop in ('location','rotation_quaternion','scale'):
                bone.keyframe_insert(data_path=prop,frame=0,group=bone.name)
        for curve in base.running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        base.v15.export(rig,action,fbx,len(frames))
        actions[role] = action
        manifest['clips'][role] = dict(file=str(fbx),action=action.name,frames=len(frames),
            duration_seconds=(len(frames)-1)/FPS,production_curves=records,
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsIdleLegSupportV32/A_M07_'+role)
        print('M07_V32_IDLE_LEG_EXPORTED '+role,flush=True)
    for n,value in hidden.items():
        bpy.data.objects[n].hide_viewport = value
    base.motion.activate(rig,actions['SweepLeft'])
    scene.frame_start,scene.frame_end = 1,len(cached['SweepLeft'])
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'],compress=True)
    manifest.update(source_saved=True,animation_fbx_exported=True)
    (OUT/'idle_leg_support_manifest_v32.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('M07_V32_IDLE_LEG_SOURCE_SAVED '+str(OUT),flush=True)


if __name__ == '__main__':
    main()
