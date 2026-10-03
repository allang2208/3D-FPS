"""Bake eight impact-away falls on M07's original rig; no runtime posing.

All variants retain the facing and joint lengths. The pelvis supplies the
fall axis, legs relinquish their support in sequence, and arms lag as intact
chains. The authored second half is also the shared physics-budget fallback.
"""
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
sys.path.insert(0, str(Path(__file__).parent))
import author_library_sweep_v27 as base

OUT = base.ROOT/'DirectionalDeathV29/Motion'
FPS, DURATION = 60, 2.8
UP, FORWARD = Vector((0, 0, 1)), Vector((0, -1, 0))


def curve(t, keys):
    """Monotone Hermite interpolation keeps speed through intermediate keys."""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    spans = [b[0]-a[0] for a, b in zip(keys, keys[1:])]
    slopes = [(b[1]-a[1])/h for a, b, h in zip(keys, keys[1:], spans)]
    tangent = [0.]
    for i in range(1, len(keys)-1):
        a, b = slopes[i-1], slopes[i]
        w1, w2 = 2*spans[i]+spans[i-1], spans[i]+2*spans[i-1]
        tangent.append((w1+w2)/(w1/a+w2/b) if a*b > 0 else 0.)
    tangent.append(0.)
    for i, ((start, a), (end, b)) in enumerate(zip(keys, keys[1:])):
        if t <= end:
            h, x = end-start, (t-start)/(end-start)
            return (2*x**3-3*x*x+1)*a+(x**3-2*x*x+x)*h*tangent[i]+(-2*x**3+3*x*x)*b+(x**3-x*x)*h*tangent[i+1]


def weight(t, start, end):
    return base.ease((t-start)/(end-start))


def floor_height(pose, skin):
    points, groups, inverses = skin
    z = np.zeros(len(points))
    for name, (indices, weights) in groups.items():
        transform = np.array(pose[name]@inverses[name], dtype=float)
        z[indices] += (points[indices]@transform[2])*weights
    return float(z.min())


def fall_pose(idle, local, ordered, direction, t):
    axis = UP.cross(direction).normalized()
    degrees = curve(t, [(0, 0), (.18, 2), (.45, 7), (.8, 18), (1.2, 38),
                        (1.55, 66), (1.88, 83), (2.1, 88), (2.36, 86), (2.8, 86)])
    tilt = base.v15.rot(axis, degrees)
    travel = curve(t, [(0, 0), (.18, 1.5), (.45, 7), (.8, 24), (1.2, 54),
                       (1.68, 95), (2.1, 128), (2.4, 132), (2.8, 132)])
    p = idle['pelvis'].translation+direction*travel
    height = idle['pelvis'].translation.z
    p.z = curve(t, [(0, height), (.4, height-5), (.8, height-20), (1.2, height-48),
                    (1.68, 76), (2.05, 45), (2.3, 40), (2.8, 40)])
    recoil = weight(t, .02, .3)*(1-weight(t, .65, 1.4))
    release = weight(t, .25, .9)
    settle = weight(t, 1.25, 2.3)
    target = {}
    for bone in ordered:
        n, parent = bone.name, bone.parent.name if bone.parent else None
        matrix = target[parent]@local[n] if parent else local[n].copy()
        position, q = matrix.translation, matrix.to_quaternion()
        if n == 'pelvis':
            position, q = p, tilt@idle[n].to_quaternion()
        elif n.startswith('spine_'):
            # Recoil is spread through the spine; no single lumbar hinge.
            q = base.v15.rot(axis, 1.4*recoil-.8*settle)@q
        elif n.startswith(('neck_', 'head')):
            q = base.v15.rot(axis, -1.8*recoil+1.2*settle)@q
        elif n.startswith('upperarm_'):
            side = n[-1]
            sign = 1 if side == 'l' else -1
            torso = target['spine_05'].to_quaternion()@idle['spine_05'].to_quaternion().inverted()
            opening = (10*release+3*recoil)*(1-.35*settle)
            lag = -degrees*.18*weight(t, .1, .8)*(1-weight(t, 1.1, 2.1))
            q = base.v15.rot(axis, lag)@base.v15.rot(torso@FORWARD, sign*opening)@q
        elif n.startswith('lowerarm_'):
            side = n[-1]
            a, b, c = (idle[name+'_'+side].translation for name in ('upperarm', 'lowerarm', 'hand'))
            hinge = (b-a).cross(c-b).normalized()
            arm = target['upperarm_'+side].to_quaternion()@idle['upperarm_'+side].to_quaternion().inverted()
            q = base.v15.rot(arm@hinge, 12*recoil+5*release*(1-settle))@q
        elif n.startswith('hand_'):
            q = base.v15.rot(axis, -4*recoil+3*settle)@q
        base.v15.put(target, n, position, q)
    pelvis_delta = target['pelvis'].to_quaternion()@idle['pelvis'].to_quaternion().inverted()
    for side in ('l', 'r'):
        free = weight(t, .64 if side == 'l' else .75, 1.86 if side == 'l' else 1.98)
        foot, calf, thigh, ball = (name+'_'+side for name in ('foot', 'calf', 'thigh', 'ball'))
        initial = idle[foot].translation
        lying = p+tilt@(initial-idle['pelvis'].translation)
        goal = initial.lerp(lying, free)
        goal.z = max(initial.z, goal.z)+5*math.sin(math.pi*free)
        hip = target[thigh].translation
        # The knee pole follows the pelvis's anatomical forward direction.
        knee, ankle, upper, lower = base.v15.leg_solution(idle, hip, goal,
            pelvis_delta, side, knee_floor=20.)
        base.v15.put(target, thigh, hip, upper@idle[thigh].to_quaternion())
        base.v15.put(target, calf, knee, lower@idle[calf].to_quaternion())
        foot_tilt = base.v15.rot(axis, degrees*.28*free)
        base.v15.put(target, foot, ankle, foot_tilt@idle[foot].to_quaternion())
        base.v15.put(target, ball, target[foot]@local[ball].translation,
                    foot_tilt@idle[ball].to_quaternion())
    return target


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(base.SOURCE))
    rig = base.v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p:len(p.bone.parent_recursive))
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    idle = base.v17.cache_action(rig, bpy.data.actions['A_M07_Idle_PalmArmV20'], 1, ordered)[0]
    local = {b.name:idle[b.parent.name].inverted()@idle[b.name] if b.parent else idle[b.name].copy() for b in ordered}
    points, groups, _ = base.v15.body_support_source(rig)
    skin = points, groups, {n:m.inverted() for n,m in rest.items()}
    floor = floor_height(idle, skin)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    hidden = {o.name:o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    manifest = dict(revision='DirectionalDeathV29',source=str(OUT/'M07_DirectionalDeath_V29.blend'),
        skeleton='/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        authoring_basis='Blender -Y forward, Z up; runtime selects measured imported pelvis travel',
        source_idle=str(base.SOURCE),fps=FPS,duration_seconds=DURATION,handoff_fraction=.6,
        handoff_seconds=DURATION*.6,clips={},root_motion=False,
        policy='Impact-away eight-sector fall; preserve facing; anatomical FK arm lag and fixed-length leg support; shared death physics and animated fallback',
        floor_policy='Offline visible-body support; excludes gill cloth; no runtime foot lock or posing',
        idle_support_floor_cm=floor,geometry_modified=False,weights_modified=False,new_runtime_ik=False,
        source_saved=False,animation_fbx_exported=False,ue_imported=False,ue_saved=False,
        tested=False,runtime_tested=False,rendered=False,user_review_pending=True)
    actions = {}
    count = round(DURATION*FPS)+1
    for sector in range(8):
        radians = math.radians(45*sector)
        direction = Vector((math.sin(radians), math.cos(radians), 0))
        role = 'DeathAway'+str(sector*45).zfill(3)
        action = bpy.data.actions.new('A_M07_'+role+'_DirectionalDeathV29')
        action.use_fake_user = True
        base.motion.activate(rig, action)
        previous, offsets = {}, []
        for i in range(count):
            scene.frame_set(i+1)
            pose = fall_pose(idle, local, ordered, direction, i/FPS)
            # Ground the falling body, not a pair of permanently planted feet.
            # Once supine/sideways, torso/limb thickness establishes the support.
            lift = max(0., floor-floor_height(pose, skin))
            for m in pose.values():
                m.translation.z += lift
            offsets.append(lift)
            base.running.insert_frame(rig, pose, rest, ordered, i+1, previous)
        scene.frame_set(0)
        for bone in ordered:
            bone.matrix_basis = Matrix.Identity(4)
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(data_path=prop, frame=0, group=bone.name)
        for fcurve in base.running.curves(action):
            for key in fcurve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        base.v15.export(rig, action, fbx, count)
        actions[role] = action
        manifest['clips'][role] = dict(file=str(fbx),action=action.name,frames=count,
            duration_seconds=DURATION,blender_fall_direction=list(direction),baked_body_support_cm=offsets,
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsDirectionalDeathV29/A_M07_'+role)
        print('M07_V29_DEATH_EXPORTED '+role, flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    base.motion.activate(rig, actions['DeathAway000'])
    scene.frame_start, scene.frame_end = 1, count
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True,animation_fbx_exported=True)
    (OUT/'directional_death_manifest_v29.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('M07_V29_DIRECTIONAL_DEATH_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
