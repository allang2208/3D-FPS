"""SVD reload support-arm repair: keep the accepted left hand, move the shoulder
outside the camera volume, and re-solve the arm with preserved bone lengths.

Diagnosis (2026-09-25 probe): during the return/settle of A_SVD_reload[_empty] the
support arm's deltoid/upper-arm mass ends up in front of the eye. The bone chain keeps
its lengths and the hand keeps its contact, so the visible defect is pure
magnification: the closest on-screen support-arm surface falls from ~263 mm (idle
baseline) to 72-129 mm, i.e. the arm is drawn 2-3.5x too large and covers up to 21% of
the frame. The accepted M16/ASH-12 remedy - relocate the shoulder and let the elbow
follow the IK - is applied to the support arm only.

Camera model matches the accepted SVD reviews: eye (0,-0.10,0.05) m, +Y view axis,
+Z up, 5 mm near clip, 82 deg protected cone, 75 deg vertical FOV at 2.39:1.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
import numpy as np

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAMILY = ARGS[0] if ARGS else 'base'
CLIPS = [a for a in ARGS[1:] if a in ('reload', 'reload_empty')] or ['reload', 'reload_empty']
EXPLORE = '--explore' in ARGS
JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
S = JOB.parent
OUT_BLEND = JOB / 'Blends'
OUT_FBX = JOB / 'Animations'
OUT_BLEND.mkdir(parents=True, exist_ok=True)
OUT_FBX.mkdir(parents=True, exist_ok=True)

SOURCES = {
    'reload': dict(dir=S / 'SVDThumbUp20260923', blend='SVD_{f}_Editable.blend',
                   action='A_SVD_{p}reload', frames=400),
    'reload_empty': dict(dir=S / 'SVDChargeGrasp20260924', blend='SVD_{f}_Grasp.blend',
                         action='A_SVD_{p}reload_empty', frames=515),
}

W0, W1, RAMP_IN, RAMP_OUT = 274, 344, 14, 14
FULL0, FULL1 = W0 + RAMP_IN, W1 - RAMP_OUT          # 288 .. 330
STRICT = [f for f in range(284, 333, 2)]
KEYFRAMES = [288, 296, 304, 312, 320, 328]
CAM = Vector((0.0, -0.10, 0.05))
NEAR = 0.005
TV82, TH82 = math.tan(math.radians(82 / 2)), math.tan(math.radians(82 / 2)) * 16 / 9
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
DEPTH_TARGET_MM = 200.0

EDIT_BONES = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l',
              'upperarm_twist_01_l', 'upperarm_twist_02_l',
              'lowerarm_twist_01_l', 'lowerarm_twist_02_l']


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (10 + x * (-15 + 6 * x))


def blend_weight(f):
    if f <= W0 or f >= W1:
        return 0.0
    if f < FULL0:
        return ease((f - W0) / RAMP_IN)
    if f > FULL1:
        return 1.0 - ease((f - FULL1) / RAMP_OUT)
    return 1.0


def sample(rig, action, frame):
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def curves(action):
    return {(c.data_path, c.array_index): c
            for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for c in bag.fcurves}


class SupportSurface:
    """Linear-blend evaluation of the support-arm vertices plus the camera metric."""

    def __init__(self, rig, arms, rest):
        self.CAM = np.array([(rig.matrix_world.inverted() @ CAM)[i] for i in range(3)])
        to_rig = rig.matrix_world.inverted() @ arms.matrix_world
        left = {n for n in (g.name for g in arms.vertex_groups) if n.endswith('_l')}
        left_ids = {arms.vertex_groups[n].index for n in left}
        rows, groups = [], []
        per_bone = {}
        for v in arms.data.vertices:
            pairs = [(arms.vertex_groups[g.group].name, g.weight) for g in v.groups
                     if g.group in left_ids and g.weight > 1e-6]
            if not pairs:
                continue
            best = max(pairs, key=lambda p: p[1])[0]
            if best.startswith(('thumb', 'index', 'middle', 'ring', 'pinky')):
                group = 'fingers'
            elif best.startswith(('upperarm', 'lowerarm')):
                group = best.split('_')[0]
            else:
                group = 'hand'
            share = sum(w for _, w in pairs)
            co = to_rig @ v.co
            row = len(rows)
            rows.append(v.index)
            groups.append(group)
            for name, weight in pairs:
                local = rest[name].inverted() @ co
                per_bone.setdefault(name, []).append(
                    (row, [local.x, local.y, local.z, 1.0], weight / share))
        self.ids = rows
        self.group = np.array(groups)
        self.by_bone = {}
        for name, entries in per_bone.items():
            self.by_bone[name] = (np.array([e[0] for e in entries], dtype=np.int64),
                                  np.array([e[1] for e in entries], dtype=float),
                                  np.array([e[2] for e in entries], dtype=float))
        print('SURFACE', len(rows), {g: int((self.group == g).sum()) for g in set(groups)}, flush=True)

    def positions(self, pose):
        out = np.zeros((len(self.ids), 4))
        for name, (ids, coords, weights) in self.by_bone.items():
            matrix = np.array(pose[name], dtype=float)
            out[ids] += (coords @ matrix.T) * weights[:, None]
        return out[:, :3] - self.CAM

    def probe(self, pose):
        v = self.positions(pose)
        x, depth, z = v[:, 0], v[:, 1], v[:, 2]
        pen = np.minimum.reduce([depth - NEAR, TH82 * depth - x, TH82 * depth + x,
                                 TV82 * depth - z, TV82 * depth + z]) + 0.006
        onscreen = (depth > 0.006) & (np.abs(x) <= TH75 * depth) & (np.abs(z) <= TV75 * depth)
        min_depth = float(depth[onscreen].min()) if onscreen.any() else None
        return min_depth, pen, onscreen

    def closest(self, pose, count=8):
        _, pen, onscreen = self.probe(pose)
        v = self.positions(pose)
        rows = [(float(v[i, 1]), int(i)) for i in np.flatnonzero(onscreen)]
        rows.sort()
        out = []
        for depth, i in rows[:count]:
            weights = []
            for name, (ids, _, _) in self.by_bone.items():
                hit = np.flatnonzero(ids == i)
                if hit.size:
                    weights.append((name, round(float(self.by_bone[name][2][hit[0]]), 3)))
            out.append(dict(depth_mm=round(depth * 1000, 1),
                            pos_cm=[round(float(v[i, k]) * 100, 1) for k in range(3)],
                            weights=weights))
        return out


def circle(C, A, T, reach):
    """Basis of the shoulder's kinematically valid circle (clavicle sphere around C,
    preserved arm extension around the unchanged wrist)."""
    R = (A - C).length
    n = (T - C)
    d = n.length
    if d < 1e-6:
        return None
    n = n / d
    L = max(abs(d - R) + 1e-4, min(min((A - T).length, reach), d + R - 1e-4))
    x = (d * d + R * R - L * L) / (2 * d)
    rho = math.sqrt(max(0.0, R * R - x * x))
    O = C + n * x
    u = n.orthogonal().normalized()
    v = n.cross(u).normalized()
    rel = A - O
    return O, u, v, rho, math.atan2(rel.dot(v), rel.dot(u))


def corrected(pose, weight, params, extra=None, anchor=None):
    """One frame of the repaired support arm; the wrist matrix is preserved exactly.

    params: (elbow-pole weight, shoulder swing along the valid circle in degrees).
    anchor: optional camera-space shoulder target (an accepted-pose-derived point that
    overrides the ring swing).
    extra: optional (dx_cm, dy_cm, dz_cm) wrist offset for exploration only.
    """
    cn, un, fn, hn = 'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'
    pole_w, swing_deg = params
    old = pose
    p = {n: m.copy() for n, m in old.items()}
    C, A, E, T = (old[cn].translation.copy(), old[un].translation.copy(),
                  old[fn].translation.copy(), old[hn].translation.copy())
    if extra:
        T = T + Vector(extra) * 0.01
        H = old[hn].copy()
        H.translation = T
        p[hn] = H
    l1 = (E - A).length
    l2 = (T - E).length
    reach = l1 + l2 - 0.002
    if anchor is not None:
        # Accepted viewmodel technique (ASH-12 right arm, 2026-09-19): translate the
        # arm root instead of only rotating the clavicle. The clavicle is shifted by
        # the same delta so its length and the shoulder-region skinning stay rigid.
        target = CAM + Vector(anchor)
        A_new = A.lerp(target, weight)
        if (T - A_new).length > reach:
            A_new = T + (A_new - T).normalized() * reach
        p[cn] = old[cn].copy()
        p[cn].translation = C + (A_new - A)
    else:
        basis = circle(C, A, T, reach)
        if basis is None:
            return p
        O, u, v, rho, theta0 = basis
        theta = theta0 + math.radians(swing_deg) * weight
        A_new = O + (u * math.cos(theta) + v * math.sin(theta)) * rho
        if (T - A_new).length > reach:
            A_new = T + (A_new - T).normalized() * reach
    p[cn] = Matrix.LocRotScale(C, (A - C).rotation_difference(A_new - C) @ old[cn].to_quaternion(),
                               old[cn].to_scale())
    axis = (T - A_new).normalized()
    dist = (T - A_new).length
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * max(dist, 1e-6))
    old_pole = (E - A) - axis * ((E - A).dot(axis))
    hint = Vector((-1.0, 0.0, -1.0)).normalized()
    hint = hint - axis * hint.dot(axis)
    if old_pole.length < 1e-6:
        pole = hint.normalized()
    elif hint.length < 1e-6:
        pole = old_pole.normalized()
    else:
        pole = old_pole.normalized().lerp(hint.normalized(), pole_w).normalized()
    E_new = A_new + axis * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    for name, origin, old_tip, tip in ((un, A_new, old[fn].translation, E_new),
                                       (fn, E_new, old[hn].translation, T)):
        p[name] = Matrix.LocRotScale(
            origin, (old_tip - old[name].translation).rotation_difference(tip - origin) @ old[name].to_quaternion(),
            old[name].to_scale())
        prefix = 'upperarm' if name == un else 'lowerarm'
        for suffix in ('01', '02'):
            twist = f'{prefix}_twist_{suffix}_l'
            if twist in p:
                p[twist] = p[name] @ old[name].inverted() @ old[twist]
    p[hn] = old[hn].copy()
    return p


def load_clip(family, clip):
    spec = SOURCES[clip]
    prefix = '' if family == 'base' else family + '_'
    blend_path = spec['dir'] / spec['blend'].format(f=family)
    action_name = spec['action'].format(p=prefix)
    frames = spec['frames']
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    for ob in list(bpy.context.scene.objects):
        if ob.type == 'MESH' and ob is not arms:
            # Hidden, not deleted: the saved deliverable blend keeps the weapon
            # geometry for future editing, while frame sampling stays cheap.
            ob.hide_viewport = True
            ob.hide_render = True
    source = bpy.data.actions[action_name]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    lr = {n: (rest[parents[n]].inverted() @ m if parents[n] else m.copy()) for n, m in rest.items()}
    poses = [sample(rig, source, f) for f in range(frames + 1)]
    surface = SupportSurface(rig, arms, rest)
    return dict(family=family, clip=clip, blend=blend_path, action=action_name, frames=frames,
                rig=rig, arms=arms, source=source, rest=rest, parents=parents, lr=lr,
                poses=poses, surface=surface)


ANCHORS = [(-0.12, 0.02, -0.16), (-0.16, 0.02, -0.16), (-0.20, 0.02, -0.16), (-0.24, 0.02, -0.16),
           (-0.12, 0.05, -0.20), (-0.16, 0.05, -0.20), (-0.20, 0.05, -0.20), (-0.24, 0.05, -0.20),
           (-0.16, 0.02, -0.24), (-0.20, 0.02, -0.24), (-0.24, 0.02, -0.24), (-0.20, 0.05, -0.26),
           (-0.14, 0.00, -0.20), (-0.26, 0.03, -0.18), (-0.18, 0.03, -0.30)]


def explore(family, clip):
    ctx = load_clip(family, clip)
    surface, poses = ctx['surface'], ctx['poses']
    for f in KEYFRAMES:
        base = surface.probe(poses[f])[0]
        C = poses[f]['clavicle_l'].translation - CAM
        A = poses[f]['upperarm_l'].translation - CAM
        T = poses[f]['hand_l'].translation - CAM
        basis = circle(poses[f]['clavicle_l'].translation, poses[f]['upperarm_l'].translation,
                       poses[f]['hand_l'].translation, 0.549)
        print('EXPLORE frame', f, 'original_mm', None if base is None else round(base * 1000, 1),
              'C_cm', [round(v * 100, 1) for v in C], 'A_cm', [round(v * 100, 1) for v in A],
              'T_cm', [round(v * 100, 1) for v in T],
              'rho_cm', None if basis is None else round(basis[3] * 100, 1), flush=True)
        for anchor in ANCHORS:
            for pw in (0.0, 0.5, 1.0):
                pose = corrected(poses[f], 1.0, (pw, 0), anchor=anchor)
                depth = surface.probe(pose)[0]
                print(f'   anchor {anchor} pole {pw} depth_mm '
                      f'{None if depth is None else round(depth * 1000, 1)} A_cm '
                      f'{[round(v * 100, 1) for v in (pose["upperarm_l"].translation - CAM)]}', flush=True)
        for swing in range(0, 360, 45):
            pose = corrected(poses[f], 1.0, (0.5, swing))
            depth = surface.probe(pose)[0]
            print(f'   swing {swing:4d} depth_mm '
                  f'{None if depth is None else round(depth * 1000, 1)} A_cm '
                  f'{[round(v * 100, 1) for v in (pose["upperarm_l"].translation - CAM)]}', flush=True)
        for row in surface.closest(corrected(poses[f], 1.0, (1.0, 0), anchor=ANCHORS[0])):
            print('   closest(anchor0)', row, flush=True)


def run(family, clip):
    ctx = load_clip(family, clip)
    surface, poses = ctx['surface'], ctx['poses']
    frames, rig, source, parents, lr = (ctx['frames'], ctx['rig'], ctx['source'],
                                        ctx['parents'], ctx['lr'])
    before = {f: surface.probe(poses[f])[0] for f in STRICT}
    print('BEFORE', family, clip, {f: (None if before[f] is None else round(before[f] * 1000, 1))
                                   for f in KEYFRAMES if f in before}, flush=True)

    scored = []
    for anchor in ANCHORS:
        for pw in (0.0, 0.5, 1.0):
            worst_depth, cost = 1e9, 0.0
            per_frame = {}
            for f in KEYFRAMES:
                fixed = corrected(poses[f], 1.0, (pw, 0), anchor=anchor)
                depth = surface.probe(fixed)[0]
                depth = 1e9 if depth is None else depth
                per_frame[f] = None if depth > 1e8 else round(depth * 1000, 1)
                worst_depth = min(worst_depth, depth)
                cost += (fixed['upperarm_l'].translation - poses[f]['upperarm_l'].translation).length
            ok = worst_depth * 1000.0 >= DEPTH_TARGET_MM
            scored.append(((0 if ok else 1, -round(worst_depth, 4), round(cost, 6)),
                           (anchor, pw), worst_depth, per_frame))
    scored.sort(key=lambda row: row[0])
    for row in scored[:6]:
        print('  CAND', row[1], 'worst_mm', round(row[2] * 1000, 1), row[3], flush=True)
    chosen = scored[0][1]
    print('CHOSEN', family, clip, chosen, 'worst_depth_mm', round(scored[0][2] * 1000, 1), flush=True)

    fixed_poses = []
    for f in range(frames + 1):
        w = blend_weight(f)
        fixed_poses.append(poses[f] if w <= 1e-6
                           else corrected(poses[f], w, (chosen[1], 0), anchor=chosen[0]))
    after = {f: surface.probe(fixed_poses[f])[0] for f in STRICT}
    hand_delta = max((fixed_poses[f]['hand_l'].translation - poses[f]['hand_l'].translation).length
                     for f in range(frames + 1))
    length_delta = 0.0
    for f in range(frames + 1):
        a = (fixed_poses[f]['lowerarm_l'].translation - fixed_poses[f]['upperarm_l'].translation).length
        b = (poses[f]['lowerarm_l'].translation - poses[f]['upperarm_l'].translation).length
        c = (fixed_poses[f]['hand_l'].translation - fixed_poses[f]['lowerarm_l'].translation).length
        d = (poses[f]['hand_l'].translation - poses[f]['lowerarm_l'].translation).length
        length_delta = max(length_delta, abs(a - b), abs(c - d))
    outside = max((fixed_poses[f]['hand_l'].inverted() @ poses[f]['hand_l']).to_quaternion().angle
                  for f in list(range(0, W0)) + list(range(W1, frames + 1)))
    report = dict(blend=str(ctx['blend']), action=ctx['action'], frames=frames,
                  params=dict(anchor=list(chosen[0]), elbow_pole=chosen[1]),
                  before_min_depth_mm={str(f): (None if before[f] is None else round(before[f] * 1000, 1))
                                       for f in STRICT},
                  after_min_depth_mm={str(f): (None if after[f] is None else round(after[f] * 1000, 1))
                                      for f in STRICT},
                  hand_world_delta_mm=round(hand_delta * 1000, 5),
                  bone_length_delta_mm=round(length_delta * 1000, 6),
                  outside_window_hand_angle_deg=round(math.degrees(outside), 6),
                  game_tested=False)

    action = source.copy()
    source.name = 'REFERENCE_' + source.name
    source.use_fake_user = True
    action.name = ctx['action']
    action.use_fake_user = True
    original = curves(source)
    tracks = curves(action)
    for name in EDIT_BONES:
        rows = []
        for f in range(frames + 1):
            w = blend_weight(f)
            pose = fixed_poses[f] if w > 1e-6 else poses[f]
            local = lr[name].inverted() @ (pose[parents[name]].inverted() @ pose[name])
            rows.append(local.decompose())
        for prop, index, count in (('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)):
            path = f'pose.bones["{name}"].{prop}'
            values, last = [], None
            for f in range(frames + 1):
                if blend_weight(f) > 1e-6:
                    v = rows[f][index].copy()
                else:
                    v = (Quaternion([original[(path, j)].evaluate(f) for j in range(4)])
                         if prop == 'rotation_quaternion'
                         else Vector([original[(path, j)].evaluate(f) for j in range(3)]))
                if prop == 'rotation_quaternion':
                    if last is not None and last.dot(v) < 0:
                        v.negate()
                    last = v.copy()
                values.append(v)
            for j in range(count):
                c = tracks[(path, j)]
                c.keyframe_points.clear()
                c.keyframe_points.add(frames + 1)
                c.keyframe_points.foreach_set('co', [v for f, row in enumerate(values) for v in (f, row[j])])
                for k in c.keyframe_points:
                    k.interpolation = 'LINEAR'
                c.update()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.render.fps = 120
    bpy.context.scene.render.fps_base = 1
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = frames
    bpy.context.scene.frame_set(FULL0)
    bpy.context.view_layer.update()
    blend_out = OUT_BLEND / f'SVD_{family}_{clip}_LeftArm.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
    for ob in bpy.context.scene.objects:
        ob.select_set(ob is rig)
    bpy.context.view_layer.objects.active = rig
    fbx = OUT_FBX / f'{ctx["action"]}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
                             axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_step=1,
                             bake_anim_simplify_factor=0)
    report.update(blend_out=str(blend_out), fbx=str(fbx))
    print('AUTHORED', family, clip, str(fbx), flush=True)
    return report


if __name__ == '__main__':
    if EXPLORE:
        explore(FAMILY, CLIPS[0])
    else:
        report = {}
        for family in [FAMILY]:
            for clip in CLIPS:
                report[f'{family}/{clip}'] = run(family, clip)
                (JOB / f'authoring_{family}_{clip}.json').write_text(json.dumps({f'{family}/{clip}': report[f'{family}/{clip}']}, indent=2))
        summary = {k: (v['params'], min(x for x in v['after_min_depth_mm'].values() if x is not None))
                   for k, v in report.items()}
        print('LEFT_ARM_AUTHORED', json.dumps(summary), flush=True)
