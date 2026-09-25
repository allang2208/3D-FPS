"""M16: register the reload grip on the M16 magazine instead of a hand-tuned
world offset.

The M16 reload reuses the whole accepted M4 left arm, but the two clips were
joined by a constant offset in weapon space (transplant.py `contact_shift`),
which cannot describe how one magazine shell sits relative to another.  Measured
against the accepted AKM wrap, that offset had the index finger 21 mm inside the
shell while the pinky floated 20 mm outside.

This pass stores the refined M4 grip as a relation to the M4 shell frame and
rebuilds it on the M16 shell at the matching height, then re-solves the arm.
Magazine travel, right hand, weapon root and every cue stay untouched: only the
left hand chain and its shoulder / elbow are rewritten, weighted by the clip's own
grip ramp.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
sys.path.insert(0, str(O))
import grip_lib as G

DIGITS = G.DIGITS
PARTS = ['hand_l'] + [f'{d}_{k}_l' for d in DIGITS for k in ('01', '02', '03')]
STEP = 0.5
CACHE = O / 'm16_cache'
CACHE.mkdir(exist_ok=True)

# accepted AKM wrap profile, used only to choose the grip height convention
AKM_TARGET = {
    'hand_l': 45.14, 'thumb_01_l': 7.77, 'thumb_02_l': 1.28, 'thumb_03_l': 23.77,
    'index_01_l': 20.86, 'index_02_l': 22.82, 'index_03_l': 15.46,
    'middle_01_l': 10.12, 'middle_02_l': 7.09, 'middle_03_l': 0.07,
    'ring_01_l': -1.08, 'ring_02_l': 2.63, 'ring_03_l': -2.97,
    'pinky_01_l': -3.62, 'pinky_02_l': 14.91, 'pinky_03_l': 8.71,
}

CLIPS = {
    'reload': {'end': 126, 'window': [43, 61, 95, 108], 'ref': 76, 'm4': 'reload'},
    'reload_empty': {'end': 162, 'window': [35, 43, 80, 100], 'ref': 80, 'm4': 'reload_empty'},
}
M4_FILES = {
    'reload': O / 'M4Animations/A_M4_ExtContact_reload.blend',
    'reload_empty': O / 'M4Animations/A_M4_ExtContact_reload_empty.blend',
}
M4_ACTIONS = {
    'reload': 'A_M4_ExtContact_reload_GripPrecise',
    'reload_empty': 'A_M4_ExtContact_reload_empty_GripPrecise',
}
M4_MAG = 'M4_Magazine Light.003_Export'
FAMILIES = ['base', 'vertical', 'canted', 'prism', 'angled']


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def rigid_mix(a, b, w):
    if w <= 0:
        return a.copy()
    if w >= 1:
        return b.copy()
    pa, qa, sa = a.decompose(); pb, qb, sb = b.decompose()
    return Matrix.LocRotScale(pa.lerp(pb, w), qa.slerp(qb, w), sa.lerp(sb, w))


def pose_dict(rig):
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def eval_world(obj, dg):
    e = obj.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys


def eval_parts(arms, dg):
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    parts = {p: [] for p in PARTS}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in parts:
            parts[best].append(M @ v.co)
    e.to_mesh_clear()
    return parts


def profile(parts, tree):
    out = {}
    for p, pts in parts.items():
        if not pts:
            continue
        d = []
        for q in pts:
            loc, nor, _, dist = tree.find_nearest(q)
            if loc is None:
                continue
            d.append(-dist if (q - loc).dot(nor) < 0 else dist)
        d.sort()
        out[p] = round(d[len(d) // 2] * 1000, 2)
    return out


def travel_direction(rig, frames=(43, 76)):
    """Insertion direction in the magazine rest frame.

    The magazine rides its carrier bone, so its position must be compared in
    weapon space; the difference is then rotated into the shell's rest frame.
    Only the sign of this direction is used (floorplate -> feed end)."""
    pos, D = {}, {}
    for f in frames:
        bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
        pose = pose_dict(rig)
        D[f] = G.deform(rig, pose)
        pos[f] = rig.matrix_world @ pose['WPN_SOCKET_Magazine'].translation
    d = D[frames[1]].inverted().to_3x3() @ (pos[frames[1]] - pos[frames[0]])
    return d.normalized() if d.length > 1e-6 else None


def make_shell(rig, mag, up_dir, palm_rest):
    return G.Shell(G.shell_points(rig, mag), palm_hint=palm_rest, up_dir=up_dir)


def find_mag(rig):
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o.parent == rig and 'agazine' in o.name and \
                any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups):
            return o
    raise RuntimeError('no magazine mesh')


def bake(rig, poses, name, scene, end):
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    local = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in rest}
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data.action = act
    for b in rig.pose.bones:
        b.rotation_mode = 'QUATERNION'
        for prop in ['location', 'rotation_quaternion', 'scale']:
            b.keyframe_insert(prop, frame=0)
    curves = {(c.data_path, c.array_index): c for la in act.layers for st in la.strips
              for bag in st.channelbags for c in bag.fcurves}
    for n in rest:
        rows = []; prev = None
        for p in poses:
            m = local[n].inverted() @ (p[parents[n]].inverted() @ p[n] if parents[n] else p[n])
            loc, q, sc = m.decompose()
            if prev and prev.dot(q) < 0:
                q.negate()
            prev = q.copy(); rows.append((loc, q, sc))
        for prop, field, cnt in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
            for axis in range(cnt):
                c = curves[(f'pose.bones["{n}"].{prop}', axis)]
                c.keyframe_points.clear(); c.keyframe_points.add(len(rows))
                c.keyframe_points.foreach_set('co', [v for j, row in enumerate(rows) for v in [j * STEP, row[field][axis]]])
                for k in c.keyframe_points:
                    k.interpolation = 'LINEAR'
                c.update()
    scene.render.fps = 60; scene.render.fps_base = 1.0
    scene.frame_start = 0; scene.frame_end = end
    return act


# ------------------------------------------------------- M4 grip relation -----
RELATION = {}
M4SHELL = {}
for kind, spec in CLIPS.items():
    bpy.ops.wm.open_mainfile(filepath=str(M4_FILES[kind]), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    act = bpy.data.actions[M4_ACTIONS[kind]]
    rig.animation_data.action = act; rig.animation_data.action_slot = act.slots[0]
    mag = bpy.data.objects[M4_MAG]
    up = travel_direction(rig)
    bpy.context.scene.frame_set(spec['ref']); bpy.context.view_layer.update()
    pose = pose_dict(rig)
    D = G.deform(rig, pose)
    palm_rest = D.inverted() @ (rig.matrix_world @ pose['hand_l'].translation)
    shell = make_shell(rig, mag, up, palm_rest)
    if shell.l.dot(up) < 0:
        raise RuntimeError('shell axis disagrees with insertion direction')
    h = shell.height(G.knuckle_rest(rig, pose, D))
    F = shell.frame_matrix(h)
    RELATION[kind] = {n: (D @ F).inverted() @ (rig.matrix_world @ pose[n]) for n in G.HAND_CHAIN}
    M4SHELL[kind] = {'length': shell.length, 'height': h}
    print('M4 %-13s shell %.1f mm  grip %.1f mm from floorplate' % (kind, shell.length * 1000, h * 1000), flush=True)

report = {'clips': {}}
for family in FAMILIES:
    for kind, spec in CLIPS.items():
        src = S / 'M16RemovalMelee20260920/Animations' / family / \
            ('A_M16_' + ('' if family == 'base' else family + '_') + kind + '.blend')
        bpy.ops.wm.open_mainfile(filepath=str(src), use_scripts=False)
        rig = bpy.data.objects['SK_M4_Infima']
        arms = bpy.data.objects['SK_Manny_Arms_Export']
        scene = bpy.context.scene
        act = rig.animation_data.action
        mag = find_mag(rig)
        restb = rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
        W = rig.matrix_world; Wi = W.inverted()
        up = travel_direction(rig)
        scene.frame_set(spec['ref']); bpy.context.view_layer.update()
        pose = pose_dict(rig)
        D = G.deform(rig, pose)
        palm_rest = D.inverted() @ (W @ pose['hand_l'].translation)
        shell = make_shell(rig, mag, up, palm_rest)
        if shell.l.dot(up) < 0:
            raise RuntimeError('M16 shell axis disagrees with insertion direction')
        dlen = shell.length - M4SHELL[kind]['length']
        # choose the height convention from the measured contact profile
        dg = bpy.context.evaluated_depsgraph_get()
        mv, mp = eval_world(mag, dg)
        tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
        parts = eval_parts(arms, dg)
        cur_hand = W @ pose['hand_l']
        options = {}
        for tag, h in [('same_from_floorplate', M4SHELL[kind]['height']),
                       ('same_from_feed_end', M4SHELL[kind]['height'] + dlen)]:
            target = D @ shell.frame_matrix(h) @ RELATION[kind]['hand_l']
            delta = target @ cur_hand.inverted()
            pr = profile({k: [delta @ p for p in v] for k, v in parts.items()}, tree)
            err = sum((pr[k] - AKM_TARGET[k]) ** 2 for k in AKM_TARGET if k in pr)
            options[tag] = {'height_mm': round(h * 1000, 2), 'error': round(err, 1), 'profile': pr}
            print('  %-22s h=%.1f mm  err=%.1f' % (tag, h * 1000, err), flush=True)
        chosen = min(options, key=lambda t: options[t]['error'])
        h16 = options[chosen]['height_mm'] / 1000.0
        print('%s/%s -> %s (err %.1f)  %s' % (family, kind, chosen, options[chosen]['error'],
                                              json.dumps(options[chosen]['profile'])), flush=True)
        F16 = shell.frame_matrix(h16)
        poses = []
        for j in range(int(spec['end'] / STEP) + 1):
            f = j * STEP
            scene.frame_set(int(f), subframe=f % 1)
            bpy.context.view_layer.update()
            p = pose_dict(rig)
            w0, w1, w2, w3 = spec['window']
            w = smooth(w0, w1, f) * (1 - smooth(w2, w3, f))
            if w > 0:
                Dm = G.deform(rig, p)
                target = Dm @ F16 @ RELATION[kind]['hand_l']
                cur = W @ p['hand_l']
                delta = rigid_mix(Matrix.Identity(4), target @ cur.inverted(), w)
                original = {n: W @ m for n, m in p.items()}
                tgt = {n: delta @ original[n] for n in G.HAND_CHAIN}
                full = G.solve_arm(rig, [b.name for b in rig.pose.bones], original, tgt)
                p = {n: (Wi @ full[n] if n in full else m) for n, m in p.items()}
            poses.append(p)
        name = 'A_M16_%s%s_GripPrecise' % ('' if family == 'base' else family + '_', kind)
        bake(rig, poses, name, scene, spec['end'])
        folder = CACHE / family
        folder.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False); rig.select_set(True); bpy.context.view_layer.objects.active = rig
        scene.frame_set(spec['ref'])
        bpy.ops.export_scene.fbx(filepath=str(folder / (name + '.fbx')), use_selection=True,
                                 object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
                                 add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                                 bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                                 bake_anim_step=STEP, bake_anim_simplify_factor=0)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / ('A_M16_' + ('' if family == 'base' else family + '_') + kind + '.blend')))
        report['clips'][family + '/' + kind] = {
            'source': str(src), 'action': name, 'height_mm': round(h16 * 1000, 2),
            'convention': chosen, 'm4_shell_length_mm': round(M4SHELL[kind]['length'] * 1000, 2),
            'm16_shell_length_mm': round(shell.length * 1000, 2),
            'options': {k: {'height_mm': v['height_mm'], 'error': v['error'], 'profile': v['profile']}
                        for k, v in options.items()},
            'fbx': str(folder / (name + '.fbx'))}
        print('M16_GRIP_AUTHORED', family, kind, name, flush=True)
(O / 'm16_grip_authoring.json').write_text(json.dumps(report, indent=1))
print('M16_GRIP_OK', flush=True)
