"""Refine accepted melee leg support and bake a complete floating cast.

Read the saved V27/V28 actions without rebuilding their upper-body source.
All contact, leg hinge and hover work is offline on the original M07 rig.
"""
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).parent))
import author_library_sweep_v27 as base

OUT = base.ROOT/'SupportHoverV30/Motion'
FPS = 60
FWD, UP, RIGHT = Vector((0,-1,0)), Vector((0,0,1)), Vector((1,0,0))


def ease(t, start, end):
    return base.ease((t-start)/(end-start))


def pulse(t, start, peak, finish):
    return ease(t,start,peak)*(1-ease(t,peak,finish))


def sole_inputs(rig, rest, side):
    obj = bpy.data.objects['M07_OriginalBody_Display']
    names = {g.index:g.name for g in obj.vertex_groups if g.name in rest}
    feet = {'foot_'+side,'ball_'+side}
    to_rig = rig.matrix_world.inverted()@obj.matrix_world
    coords, weights = [], []
    for vertex in obj.data.vertices:
        row = {names[g.group]:g.weight for g in vertex.groups if g.group in names}
        if sum(w for n,w in row.items() if n in feet) < .5:
            continue
        point = to_rig@vertex.co
        coords.append((*point,1.))
        total = sum(row.values())
        weights.append({n:w/total for n,w in row.items()})
    points = np.asarray(coords)
    return {n:(points@np.array(rest[n].inverted()).T)*np.array([r.get(n,0.) for r in weights])[:,None]
            for n in set().union(*(r.keys() for r in weights))}


def shift(pose, z):
    for m in pose.values():
        m.translation.z += z


def fit_contact_legs(pose, goals, floor, skin, rest, local, hinges):
    """One anatomical knee hinge, with separate soles and reachable pelvis."""
    total_drop = 0.
    for _ in range(3):
        for side in ('l','r'):
            foot, ball = 'foot_'+side, 'ball_'+side
            p, q, ball_q, clearance = goals[side]
            pose[foot] = base.matrix(p,q)
            pose[ball] = base.matrix(pose[foot]@local[ball].translation,ball_q)
            p.z += floor+clearance-base.support_height(pose,skin[side])
            pose[foot].translation = p
            pose[ball].translation = pose[foot]@local[ball].translation
        # Keep both ankles reachable before solving. A stretched, clamped leg
        # would otherwise pull a supposedly planted foot back off the floor.
        drop = 0.
        for side in ('l','r'):
            hip = pose['thigh_'+side].translation
            ankle = goals[side][0]
            d = hinges[side]
            l1,l2 = d['upper_length'],d['lower_length']
            reach = math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(12)))
            horizontal = (hip.x-ankle.x)**2+(hip.y-ankle.y)**2
            drop = max(drop,hip.z-ankle.z-math.sqrt(max(1.,reach*reach-horizontal)))
        if drop > 0:
            shift(pose,-drop)
            total_drop += drop
        for side in ('l','r'):
            p,q,ball_q,_ = goals[side]
            pose['foot_'+side] = base.matrix(p,q)
            pose['ball_'+side] = base.matrix(pose['foot_'+side]@local['ball_'+side].translation,ball_q)
            pose.update(base.v17.solve_chain(rest,local,hinges,pose,side,0.,True))
    return total_drop


def melee_pose(source, idle, rest, local, hinges, skin, floor, t, attack_side):
    pose = {n:m.copy() for n,m in source.items()}
    lead = 'l' if attack_side == 'r' else 'r'
    stride = ease(t,.12,.42)*(1-ease(t,1.35,1.95))
    step_height = 4.*(pulse(t,.12,.27,.42)+pulse(t,1.35,1.65,1.95))
    load = 3.5*pulse(t,.14,.48,1.15)
    shift(pose,-load)
    goals = {}
    for side in ('l','r'):
        p = idle['foot_'+side].translation.copy()
        if side == lead:
            p += FWD*12.*stride
        # Rear heel yields slightly into the strike, with the toe still in
        # contact. The support calculation includes the long claw geometry.
        pitch = 7.*pulse(t,.30,.59,.98) if side == attack_side else 0.
        turn = base.v15.rot(RIGHT,pitch)
        goals[side] = (p,turn@idle['foot_'+side].to_quaternion(),
                       turn@idle['ball_'+side].to_quaternion(),step_height if side == lead else 0.)
    drop = fit_contact_legs(pose,goals,floor,skin,rest,local,hinges)
    return pose,dict(pelvis_support_drop_cm=drop,load_cm=load,lead_clearance_cm=step_height)


def casting_pose(source, idle, rest, local, hinges, skin, floor, t):
    pose = {n:m.copy() for n,m in source.items()}
    hover = ease(t,.18,.98)*(1-ease(t,1.62,2.14))
    relaxed = ease(t,.26,1.05)*(1-ease(t,1.58,2.10))
    bob = 1.4*math.sin((t-.98)*math.pi*2/1.8)*pulse(t,.88,1.24,1.7)
    height = 40.*hover+bob
    landing = 4.5*pulse(t,2.07,2.23,2.40)
    shift(pose,height-landing)
    goals = {}
    for side in ('l','r'):
        p = idle['foot_'+side].translation.copy()
        p -= FWD*(7. if side == 'l' else 10.)*relaxed
        pitch = base.v15.rot(RIGHT,(11. if side == 'l' else 14.)*relaxed)
        clearance = height+(6. if side == 'l' else 9.)*relaxed
        goals[side] = (p,pitch@idle['foot_'+side].to_quaternion(),
                       pitch@idle['ball_'+side].to_quaternion(),clearance)
    drop = fit_contact_legs(pose,goals,floor,skin,rest,local,hinges)
    return pose,dict(hover_cm=height,landing_compression_cm=landing,pelvis_support_drop_cm=drop)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    caches, sources = {}, {}
    for family, manifest_path in (
        ('melee',base.ROOT/'LibrarySweepV27/Motion/library_sweep_manifest_v27.json'),
        ('casting',base.ROOT/'LibraryCastV28/Motion/library_cast_manifest_v28.json')):
        record = json.loads(manifest_path.read_text(encoding='utf-8'))
        bpy.ops.wm.open_mainfile(filepath=record['source'])
        rig = base.v20.original_rig()
        rig.data.pose_position = 'POSE'
        ordered = sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive))
        for role,entry in record['clips'].items():
            caches[role] = base.v17.cache_action(rig,bpy.data.actions[entry['action']],entry['frames'],ordered)
        sources[family] = str(manifest_path)
    bpy.ops.wm.open_mainfile(filepath=str(base.SOURCE))
    rig = base.v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive))
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local = {p.name:rest[p.parent.name].inverted()@rest[p.name] if p.parent else rest[p.name].copy() for p in ordered}
    idle = base.v17.cache_action(rig,bpy.data.actions['A_M07_Idle_PalmArmV20'],1,ordered)[0]
    hinges = {s:base.v17.hinge_data(rest,s) for s in ('l','r')}
    skin = {s:sole_inputs(rig,rest,s) for s in ('l','r')}
    floor = min(base.support_height(idle,skin[s]) for s in skin)
    scene = bpy.context.scene
    scene.render.fps,scene.render.fps_base = FPS,1.
    scene.unit_settings.system,scene.unit_settings.scale_length = 'METRIC',.01
    hidden = {o.name:o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    manifest = dict(revision='SupportHoverV30',fps=FPS,source=str(OUT/'M07_SupportHover_V30.blend'),
        source_manifests=sources,clips={},idle_support_floor_cm=floor,
        melee_contact_seconds=.60,melee_duration_seconds=2.,gather_seconds=1.1,release_seconds=1.3,
        release_contact_seconds=.30,hover_height_cm=40.,landing_complete_seconds=2.40,
        policy='Saved upper-body library rotations retained; separate sole contact and signed knee hinges baked offline; complete hover and soft landing in one casting clock',
        geometry_modified=False,weights_modified=False,native_code_modified=False,new_runtime_ik=False,
        source_saved=False,animation_fbx_exported=False,ue_imported=False,ue_saved=False,
        tested=False,runtime_tested=False,rendered=False,user_review_pending=True)
    authored, records = {}, {}
    for role,side in (('SweepLeft','l'),('SweepRight','r')):
        authored[role],records[role] = [],[]
        for i,src in enumerate(caches[role]):
            pose,info = melee_pose(src,idle,rest,local,hinges,skin,floor,i/FPS,side)
            authored[role].append(pose)
            records[role].append(info)
    full_cast = caches['MagicGather']+caches['MagicRelease'][1:]
    floating, float_info = [],[]
    for i,src in enumerate(full_cast):
        pose,info = casting_pose(src,idle,rest,local,hinges,skin,floor,i/FPS)
        floating.append(pose)
        float_info.append(info)
    split = len(caches['MagicGather'])-1
    authored.update(MagicGather=floating[:split+1],MagicRelease=floating[split:])
    records.update(MagicGather=float_info[:split+1],MagicRelease=float_info[split:])
    actions = {}
    for role,frames in authored.items():
        action = bpy.data.actions.new('A_M07_'+role+'_SupportHoverV30')
        action.use_fake_user = True
        base.motion.activate(rig,action)
        previous = {}
        for i,pose in enumerate(frames):
            scene.frame_set(i+1)
            base.running.insert_frame(rig,pose,rest,ordered,i+1,previous)
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
            duration_seconds=(len(frames)-1)/FPS,production_curves=records[role],
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsSupportHoverV30/A_M07_'+role)
        print('M07_V30_SUPPORT_HOVER_EXPORTED '+role,flush=True)
    for name,value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    base.motion.activate(rig,actions['MagicRelease'])
    scene.frame_start,scene.frame_end = 1,len(authored['MagicRelease'])
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'],compress=True)
    manifest.update(source_saved=True,animation_fbx_exported=True)
    (OUT/'support_hover_manifest_v30.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('M07_V30_SUPPORT_HOVER_SOURCE_SAVED '+str(OUT),flush=True)


if __name__ == '__main__':
    main()
