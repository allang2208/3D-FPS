"""Nail the PKM left-elbow defect.

Two independent measurements on the real V7 surface and weights:
  1. the signed axial (twist) difference between the bones that share the
     elbow band, about the live forearm axis;
  2. the surface's own roll change around the limb axis, measured per vertex
     against the arm's own bend plane, so a rigid arm motion reads zero.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 60, 0),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120, 1),
    'reload_empty': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
                     'PKM34_base_reload_empty', 120, 1),
}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_REST_M = [__import__('mathutils').Matrix(m.tolist()) for m in AU_REST]
N_V7 = len(V7_BONES)
B = {n: V7_BONES.index(n) for n in (
    'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
    'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l')}

e_rest = V7_REST[B['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[B['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[B['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))

rel = V7_VERTS - e_rest
t_all = rel @ f0 / FLEN
radius = np.linalg.norm(rel - np.outer(t_all * FLEN, f0), axis=1)

ARM_L = (radius < 0.075) & (t_all > -1.0) & (t_all < 1.2)
BANDS = {
    'upper_mid': (-0.55, -0.25),
    'upper_low': (-0.25, -0.10),
    'elbow': (-0.10, 0.10),
    'fore_low': (0.10, 0.30),
    'fore_mid': (0.30, 0.60),
    'fore_high': (0.60, 0.95),
}
BAND_MASK = {k: ARM_L & (t_all >= a) & (t_all < b) for k, (a, b) in BANDS.items()}

# rest angular coordinate of every vertex about the forearm axis, in the arm's
# own bend-plane frame
p1_0 = u0 - (u0 @ f0) * f0
p1_0 /= np.linalg.norm(p1_0)
p2_0 = np.cross(f0, p1_0)
perp0 = rel - np.outer(rel @ f0, f0)
phi0 = np.arctan2(perp0 @ p2_0, perp0 @ p1_0)


def deform_with(skin):
    out = np.zeros((len(V7_VERTS), 3))
    homo = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)
    for k in range(V7_WIDX.shape[1]):
        idx = V7_WIDX[:, k]
        w = V7_WVAL[:, k]
        active = (idx >= 0) & (w > 0.0)
        out[active] += w[active, None] * np.einsum(
            'nij,nj->ni', skin[idx[active]], homo[active])[:, :3]
    return out


def axial_deg(q):
    """signed angle of quaternion q about the world +Z of the frame it lives in"""
    v = Vector((q.x, q.y, q.z))
    return math.degrees(2 * math.atan2(v.z, q.w))


def run(blend, action_name, fps, step_div):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = fps
    start, end = map(int, action.frame_range)
    step = max(1, int(fps / (15 if step_div else 10)))

    rows = []
    for frame in range(start, end + 1, step):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        delta = {}
        for n in AU_BONES:
            delta[n] = rig.pose.bones[n].matrix @ AU_REST_M[AU_BONES.index(n)].inverted()
        s = np.array(rig.pose.bones['upperarm_l'].matrix.translation)
        e = np.array(rig.pose.bones['lowerarm_l'].matrix.translation)
        w = np.array(rig.pose.bones['hand_l'].matrix.translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)
        axis = Vector(f.tolist())

        # axial difference of each bone's delta about the live forearm axis
        def rel_axial(a, b):
            q = (delta[a].to_3x3().to_quaternion().inverted()
                 @ delta[b].to_3x3().to_quaternion())
            return axial_deg(q)

        # surface roll change in the bend-plane frame
        p1 = u - (u @ f) * f
        p1 /= np.linalg.norm(p1)
        p2 = np.cross(f, p1)
        skin = np.tile(np.eye(4), (N_V7, 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in delta:
                skin[i] = np.array(delta[n])
        posed = deform_with(skin)
        relp = posed - e
        perpp = relp - np.outer(relp @ f, f)
        phip = np.arctan2(perpp @ p2, perpp @ p1)
        dphi = np.degrees((phip - phi0 + np.pi) % (2 * np.pi) - np.pi)

        row = {'frame': frame, 'seconds': round(frame / fps, 4),
               'bend_deg': round(math.degrees(math.acos(max(-1, min(1, u @ f)))), 1),
               'ax_up02_lo': round(rel_axial('upperarm_twist_02_l', 'lowerarm_l'), 1),
               'ax_lo_lo02': round(rel_axial('lowerarm_l', 'lowerarm_twist_02_l'), 1),
               'ax_lo02_lo01': round(rel_axial('lowerarm_twist_02_l', 'lowerarm_twist_01_l'), 1),
               'ax_up_up02': round(rel_axial('upperarm_l', 'upperarm_twist_02_l'), 1),
               'ax_up_lo': round(rel_axial('upperarm_l', 'lowerarm_l'), 1)}
        for name, mask in BAND_MASK.items():
            if mask.sum() == 0:
                continue
            val = dphi[mask]
            row['roll_' + name] = round(float(val.mean()), 1)
            row['spread_' + name] = round(float(np.percentile(val, 95)
                                                - np.percentile(val, 5)), 1)
        rows.append(row)
    return rows


report = {'bands': {k: int(m.sum()) for k, m in BAND_MASK.items()},
          'forearm_length_m': round(FLEN, 4)}
for key, (blend, action_name, fps, sd) in CLIPS.items():
    report[key] = run(blend, action_name, fps, sd)

(HERE / 'elbow_shear.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

print('band vertex counts:', report['bands'])
hdr = ['sec', 'bend', 'up02-lo', 'lo-lo02', 'lo02-lo01', 'up-up02',
       'roll_elb', 'spr_elb', 'roll_fmid', 'spr_fmid']
for key in CLIPS:
    rows = report[key]
    print('\n== %s ==' % key)
    print('%6s %5s | %8s %8s %9s %8s | %8s %8s %9s %9s' % tuple(hdr))
    n = len(rows)
    for r in rows[::max(1, n // 16)]:
        print('%6.2f %5.0f | %8.1f %8.1f %9.1f %8.1f | %8.1f %8.1f %9.1f %9.1f' % (
            r['seconds'], r['bend_deg'], r['ax_up02_lo'], r['ax_lo_lo02'],
            r['ax_lo02_lo01'], r['ax_up_up02'], r['roll_elbow'], r['spread_elbow'],
            r['roll_fore_mid'], r['spread_fore_mid']))
print('\nSHEAR_DONE')