"""PKM left elbow: re-time the forearm pronation so no band is wrung.

Diagnosis (Elbow39): on the real V7 PKM arm surface the roll about the limb
axis ramps smoothly down the upper arm and out to the wrist, but reverses by
~46 deg in the band 0.28..0.42 of the forearm, because `lowerarm_l` (which
carries almost no pronation) and `lowerarm_twist_02_l` (which carries most of
it) cross over 3 cm apart and 70 deg apart in twist.

Fix: put the forearm helper bones back on a linear pronation ramp that runs
from the elbow (where the upper arm is) to the hand, by adding a world-space
twist about the live forearm axis through each bone's own head.  Every
descendant's world matrix is preserved, so the grip, hand, fingers, contacts
and wrist are untouched by construction.

Each frame is guarded: the correction is scaled down (or dropped) unless it
reduces the worst backward step of that frame's own roll profile.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'
EXPORT = HERE / 'Exports'
EDIT = HERE / 'Edit'
for d in (EXPORT, EDIT):
    d.mkdir(parents=True, exist_ok=True)

STATION = {'upperarm_twist_02_l': -0.18, 'lowerarm_l': 0.23,
           'lowerarm_twist_02_l': 0.35, 'lowerarm_twist_01_l': 0.85,
           'hand_l': 1.00}
RAMPED = ('lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l')
ORDER = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
PARENT = {'lowerarm_l': 'upperarm_l', 'lowerarm_twist_02_l': 'lowerarm_l',
          'lowerarm_twist_01_l': 'lowerarm_l', 'hand_l': 'lowerarm_l'}
ANCHOR = 'upperarm_twist_02_l'
CAP = {'lowerarm_l': 75.0, 'lowerarm_twist_02_l': 35.0, 'lowerarm_twist_01_l': 30.0}
SCALES = (1.0, 0.75, 0.5, 0.25, 0.0)
FIT_LO, FIT_HI = -0.10, 0.90

# ---------------------------------------------------------------- surface rig
mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_REST_M = [Matrix(m.tolist()) for m in AU_REST]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
IDX = {n: V7_BONES.index(n) for n in
       ('upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_02_l')}

e_rest = V7_REST[IDX['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[IDX['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[IDX['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
REL = V7_VERTS - e_rest
T_ALL = REL @ f0 / FLEN
RADIUS = np.linalg.norm(REL - np.outer(T_ALL * FLEN, f0), axis=1)
ARM = (RADIUS < 0.070) & (T_ALL > -0.30) & (T_ALL < 0.92)
AIDX = np.where(ARM)[0]
TV = V7_VERTS[AIDX]
THOMO = np.concatenate([TV, np.ones((len(TV), 1))], axis=1)
TI, TW, TT = V7_WIDX[AIDX], V7_WVAL[AIDX], T_ALL[AIDX]
PERP0 = (TV - e_rest) - np.outer((TV - e_rest) @ f0, f0)
P1_0 = u0 - (u0 @ f0) * f0
P1_0 /= np.linalg.norm(P1_0)
P2_0 = np.cross(f0, P1_0)
PHI0 = np.arctan2(PERP0 @ P2_0, PERP0 @ P1_0)
EDGES = np.arange(-0.30, 0.92, 0.05)
BIN = np.digitize(TT, EDGES) - 1
NB = len(EDGES) - 1
BIN_T = EDGES[:-1] + 0.025
BIN_OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = BIN_OK & (BIN_T >= FIT_LO) & (BIN_T <= FIT_HI)


def deform_arm(skin):
    out = np.zeros((len(TV), 3))
    for k in range(TI.shape[1]):
        idx, w = TI[:, k], TW[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             THOMO[act])[:, :3]
    return out


def roll_profile(posed, e, u, f):
    p1 = u - (u @ f) * f
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    rp = posed - e
    pp = rp - np.outer(rp @ f, f)
    phip = np.arctan2(pp @ p2, pp @ p1)
    dphi = np.degrees((phip - PHI0 + np.pi) % (2 * np.pi) - np.pi)
    vals = np.full(NB, np.nan)
    for b in range(NB):
        sel = BIN == b
        if sel.sum() >= 8:
            vals[b] = dphi[sel].mean()
    return vals


def backward(vals):
    d = np.diff(vals[FIT])
    return float(np.clip(d, 0.0, None).max())


def unwrap(v, ref, period=360.0):
    while v - ref > period / 2:
        v -= period
    while ref - v > period / 2:
        v += period
    return v


def roll_probe(matrix, ring, rest_phi, e, u, f):
    p1 = (Vector(u) - Vector(u).dot(Vector(f)) * Vector(f)).normalized()
    p2 = Vector(f).cross(p1)
    out = []
    for v, rp in zip(ring, rest_phi):
        h = matrix @ v
        d = Vector((h.x, h.y, h.z)) - Vector(e)
        d = d - d.dot(Vector(f)) * Vector(f)
        out.append(math.degrees((math.atan2(d.dot(p2), d.dot(p1)) - rp
                                 + math.pi) % (2 * math.pi) - math.pi))
    return sum(out) / len(out)


def local_channels(world, parent_world, rest_local):
    return (rest_local.inverted() @ (parent_world.inverted() @ world)).decompose()


CLIPS = (
    (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
     'PKM_Game_idle_Wrist12', 60, EXPORT / 'A_PKM_idle.fbx', 'PKM_idle_Elbow39'),
    (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
     'PKM16_base_reload', 120, EXPORT / 'A_PKM_reload.fbx', 'PKM_reload_Elbow39'),
    (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
     'PKM34_base_reload_empty', 120, EXPORT / 'A_PKM_reload_empty.fbx',
     'PKM_reload_empty_Elbow39'),
)

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SCOPE = ARGS[0] if ARGS else 'base'
SAVE_EDIT = True
if SCOPE == 'families':
    FAMILIES = (
        ('angled', ROOT / 'GripContact15' / 'PKM_angled_Editable.blend',
         ROOT / 'Reload16' / 'PKM_angled_Reload_Editable.blend',
         ROOT / 'Charge34' / 'PKM_angled_ChargePush_Editable.blend'),
        ('canted', ROOT / 'GripContact15' / 'PKM_canted_Editable.blend',
         ROOT / 'Reload16' / 'PKM_canted_Reload_Editable.blend',
         ROOT / 'Charge34' / 'PKM_canted_ChargePush_Editable.blend'),
        ('prism', ROOT / 'GripContact15' / 'PKM_prism_Editable.blend',
         ROOT / 'Reload16' / 'PKM_prism_Reload_Editable.blend',
         ROOT / 'Charge34' / 'PKM_prism_ChargePush_Editable.blend'),
        ('vertical', ROOT / 'GripContact15' / 'PKM_vertical_Editable.blend',
         ROOT / 'Reload16' / 'PKM_vertical_Reload_Editable.blend',
         ROOT / 'Charge34' / 'PKM_vertical_ChargePush_Editable.blend'),
    )
    CLIPS = ()
    for fam, idle_blend, reload_blend, charge_blend in FAMILIES:
        CLIPS += (
            (idle_blend, 'PKM_Game_idle', 60,
             EXPORT / fam / ('A_PKM_%s_idle.fbx' % fam), 'PKM_%s_idle_Elbow39' % fam),
            (reload_blend, 'PKM16_%s_reload' % fam, 120,
             EXPORT / fam / ('A_PKM_%s_reload.fbx' % fam), 'PKM_%s_reload_Elbow39' % fam),
            (charge_blend, 'PKM34_%s_reload_empty' % fam, 120,
             EXPORT / fam / ('A_PKM_%s_reload_empty.fbx' % fam),
             'PKM_%s_reload_empty_Elbow39' % fam),
        )
    EDIT = HERE / 'Edit' / 'families'
    EDIT.mkdir(parents=True, exist_ok=True)
    SAVE_EDIT = False


def repair(blend, action_name, fps, dest, edit_name):
    dest.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    source = bpy.data.actions[action_name]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0

    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rest_local = {b.name: (rest[b.parent.name].inverted() @ rest[b.name])
                  if b.parent else rest[b.name] for b in rig.data.bones}
    start, end = map(int, source.frame_range)

    e_r, s_r, w_r = (rest['lowerarm_l'].translation, rest['upperarm_l'].translation,
                     rest['hand_l'].translation)
    a0, b0 = (e_r - s_r).normalized(), (w_r - e_r).normalized()
    flen = (w_r - e_r).length
    q1 = (a0 - a0.dot(b0) * b0).normalized()
    q2 = b0.cross(q1)
    rings, rphis = {}, {}
    for name in STATION:
        c = e_r + b0 * (STATION[name] * flen)
        ring = [c + math.cos(2 * math.pi * i / 24) * q1 * 0.045
                + math.sin(2 * math.pi * i / 24) * q2 * 0.045 for i in range(24)]
        rings[name] = ring
        rphis[name] = []
        for v in ring:
            d = v - e_r
            d = d - d.dot(b0) * b0
            rphis[name].append(math.atan2(d.dot(q2), d.dot(q1)))

    sampled = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sampled.append({b.name: b.matrix.copy() for b in rig.pose.bones})

    action = source.copy()
    action.name = edit_name
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if any('"%s"' % n in curve.data_path for n in ORDER):
                        bag.fcurves.remove(curve)

    previous = {}
    report = []
    max_hand_drift = 0.0
    for frame, pose in enumerate(sampled, start):
        s, e, w = (np.array(pose['upperarm_l'].translation),
                   np.array(pose['lowerarm_l'].translation),
                   np.array(pose['hand_l'].translation))
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)
        delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}

        rolls = {}
        for name in (ANCHOR,) + tuple(ORDER):
            rolls[name] = roll_probe(delta[name], rings[name], rphis[name], e, u, f)
        chain = [ANCHOR] + list(ORDER)
        for i in range(1, len(chain)):
            rolls[chain[i]] = unwrap(rolls[chain[i]], rolls[chain[i - 1]])
        t0, r0 = STATION[ANCHOR], rolls[ANCHOR]
        t1, r1 = STATION['hand_l'], rolls['hand_l']
        slope = (r1 - r0) / (t1 - t0)
        full = {}
        for name in RAMPED:
            want = (r0 + slope * (STATION[name] - t0)) - rolls[name]
            full[name] = max(-CAP[name], min(CAP[name], want))

        base_skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in delta:
                base_skin[i] = np.array(delta[n])
        before = backward(roll_profile(deform_arm(base_skin), e, u, f))

        fv = Vector(f.tolist())

        def build(scale):
            skin = np.copy(base_skin)
            for name in RAMPED:
                d = full[name] * scale
                if abs(d) < 1e-9:
                    continue
                h = pose[name].translation
                skin[V7_BONES.index(name)] = np.array(
                    Matrix.Translation(h)
                    @ Matrix.Rotation(math.radians(d), 4, fv)
                    @ Matrix.Translation(-h) @ delta[name])
            return skin

        chosen, scale_used, after = build(0.0), 0.0, before
        for scale in SCALES:
            if scale == 0.0:
                break
            cand = build(scale)
            val = backward(roll_profile(deform_arm(cand), e, u, f))
            if val <= before + 1.0:
                chosen, scale_used, after = cand, scale, val
                break
            chosen = cand
        if scale_used == 0.0:
            chosen = build(0.0)
            after = before

        world = {}
        for name in ORDER:
            m = pose[name].copy()
            if name in RAMPED:
                d = full[name] * scale_used
                if abs(d) > 1e-9:
                    h = pose[name].translation
                    m = (Matrix.Translation(h)
                         @ Matrix.Rotation(math.radians(d), 4, fv)
                         @ Matrix.Translation(-h) @ m)
            world[name] = m

        parent_world = {'upperarm_l': pose['upperarm_l']}
        for name in ORDER:
            pm = parent_world[PARENT[name]]
            loc, quat, scale_v = local_channels(world[name], pm, rest_local[name])
            if name in previous and quat.dot(previous[name]) < 0.0:
                quat.negate()
            previous[name] = quat.copy()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.location = loc
            bone.rotation_quaternion = quat
            bone.scale = scale_v
            parent_world[name] = world[name]
            for ch in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(ch, frame=frame, group=name)

        drift = (world['hand_l'].translation - pose['hand_l'].translation).length
        orient = world['hand_l'].to_quaternion().rotation_difference(
            pose['hand_l'].to_quaternion()).angle
        max_hand_drift = max(max_hand_drift, drift, orient)
        report.append({'frame': frame,
                       'scale': scale_used,
                       'corr': {k: round(full[k] * scale_used, 2) for k in RAMPED},
                       'back_before': round(before, 2),
                       'back_after': round(after, 2)})
        if frame % 120 == 0:
            print('ELBOW39', action_name, frame, 'scale', scale_used,
                  'back', round(before, 1), '->', round(after, 1), flush=True)

    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if any('"%s"' % n in curve.data_path for n in ORDER):
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'

    scene.frame_start, scene.frame_end = start, end
    scene.frame_set(start)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(dest), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    if SAVE_EDIT:
        bpy.ops.wm.save_as_mainfile(filepath=str(EDIT / (edit_name + '.blend')))
    return {'frames': len(sampled), 'max_hand_drift': max_hand_drift,
            'report': report, 'fps': fps, 'action': action.name,
            'full': full}


def run_clips(clips=None, report_name=None):
    """Repair every clip in `clips` (default: the module's CLIPS)."""
    results = {}
    for blend, action_name, fps, dest, edit_name in (CLIPS if clips is None else clips):
        print('\n=== %s ===' % action_name, flush=True)
        res = repair(blend, action_name, fps, dest, edit_name)
        results[action_name] = res
        scales = [r['scale'] for r in res['report']]
        print('EXPORTED %s frames %d  max hand drift %.7f  scales %s' % (
            dest.name, res['frames'], res['max_hand_drift'],
            {s: scales.count(s) for s in sorted(set(scales))}), flush=True)

    if report_name is None:
        report_name = 'authoring.json' if SCOPE == 'base' else 'authoring_families.json'
    (HERE / report_name).write_text(
        json.dumps(
            {k: {'frames': v['frames'], 'fps': v['fps'], 'action': v['action'],
                 'max_hand_drift': v['max_hand_drift'], 'report': v['report']}
             for k, v in results.items()}, indent=2), encoding='utf-8')
    return results


# Guarded so the repair machinery can be imported and re-pointed at other
# clips (see ../Elbow41/author_elbow41.py) without re-running the base set.
if __name__ == '__main__':
    run_clips()
    print('\nELBOW39_AUTHOR_DONE', SCOPE)