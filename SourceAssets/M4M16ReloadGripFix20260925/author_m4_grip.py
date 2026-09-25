"""M4: seat the left-hand grip on the magazine shell as precisely as the accepted
AKM wrap.

The current M4 contact clip already carries the accepted AKM hand shape; the
residual is a small rigid misplacement in the magazine's own cross-section frame
(measured against the AKM profile in refine.py).  This pass applies that bounded
rigid correction inside the magazine shell frame, weighted by the clip's own grip
ramp, then re-solves clavicle / upper arm / fore arm so the arm keeps its shape.
Magazine travel, right hand, weapon root and every cue stay untouched.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector

O = Path(__file__).parent; S = O.parent
sys.path.insert(0, str(O))
import grip_lib as G

cfg = json.loads((O / 'grip_fix.json').read_text())
CORR = cfg['correction']
T = Vector([v / 1000.0 for v in CORR['translation_mm']])
E = [math.radians(v) for v in CORR['euler_xyz_deg']]
if 'matrix' in CORR:
    C = Matrix([[float(x) for x in row] for row in CORR['matrix']])
else:
    C = Matrix.Translation(T) @ Matrix.Rotation(E[2], 4, 'Z') @ Matrix.Rotation(E[1], 4, 'Y') @ Matrix.Rotation(E[0], 4, 'X')
STEP = 0.5
MAGNAME = 'M4_Magazine Light.003_Export'


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


report = {'correction': CORR, 'clips': {}}
out_dir = O / 'M4Animations'
out_dir.mkdir(exist_ok=True)
for kind, spec in cfg['clips'].items():
    src = S / spec['file']
    bpy.ops.wm.open_mainfile(filepath=str(src), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    mag = bpy.data.objects[MAGNAME]
    scene = bpy.context.scene
    end = int(spec['end'])
    w0, w1, w2, w3 = spec['window']
    # shell frame of this rifle's magazine, in rest world space
    scene.frame_set(int(end * 0.6)); bpy.context.view_layer.update()
    shell = G.Shell(G.shell_points(rig, mag),
                    well_hint=rig.matrix_world @ rig.data.bones['WPN_SOCKET_Magazine'].head_local,
                    palm_hint=rig.matrix_world @ rig.pose.bones['hand_l'].matrix.translation)
    restb = rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
    ref = int(spec['window'][2] - (spec['window'][2] - spec['window'][1]) / 2)
    scene.frame_set(ref); bpy.context.view_layer.update()
    pose = pose_dict(rig)
    Dw = rig.matrix_world @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ rig.matrix_world.inverted()
    knuckle = sum((rig.matrix_world @ pose[f'{d}_01_l'].translation for d in G.DIGITS[1:]), Vector()) / 4
    h = shell.height(Dw.inverted() @ knuckle)
    F = shell.frame_matrix(h)
    print('%s: shell %.1f mm, grip height %.1f mm from floorplate' % (kind, shell.length * 1000, h * 1000), flush=True)
    poses = []
    W = rig.matrix_world
    Wi = W.inverted()
    for j in range(int(end / STEP) + 1):
        f = j * STEP
        scene.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        p = pose_dict(rig)
        w = smooth(w0, w1, f) * (1 - smooth(w2, w3, f))
        if w > 0:
            Cw = rigid_mix(Matrix.Identity(4), C, w)
            dw = W @ p['WPN_SOCKET_Magazine'] @ restb.inverted() @ Wi
            delta = dw @ F @ Cw @ F.inverted() @ dw.inverted()
            original = {n: W @ m for n, m in p.items()}
            target = {n: delta @ original[n] for n in G.HAND_CHAIN}
            full = G.solve_arm(rig, [b.name for b in rig.pose.bones], original, target)
            p = {n: (Wi @ full[n] if n in full else m) for n, m in p.items()}
        poses.append(p)
    name = spec['action'] + '_GripPrecise'
    act = bake(rig, poses, name, scene, end)
    fb = out_dir / (name + '.fbx')
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    scene.frame_set(int(spec['window'][2]))
    bpy.ops.export_scene.fbx(filepath=str(fb), use_selection=True, object_types={'ARMATURE'},
                             axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_step=STEP,
                             bake_anim_simplify_factor=0)
    blend = out_dir / (spec['action'] + '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report['clips'][kind] = {'source': str(src), 'action': name, 'file': str(blend), 'fbx': str(fb),
                             'end': end, 'window': spec['window'],
                             'grip_height_mm': round(h * 1000, 2), 'shell_length_mm': round(shell.length * 1000, 2)}
    print('M4_GRIP_AUTHORED', kind, name, flush=True)
(O / 'm4_grip_authoring.json').write_text(json.dumps(report, indent=1))
print('M4_GRIP_OK', flush=True)
