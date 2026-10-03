"""Measure what the PKM left elbow actually does at every sampled frame.

Reports, for the real V7 weights:
  * elbow bend angle
  * the world rotation delta of each bone that skins the elbow band
  * the pairwise difference between those deltas (the shear the band sees)
  * the axial (twist) part of each delta about the live forearm axis
  * how deep the outer elbow surface collapses
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'
OUT = HERE / 'Review'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 60),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120),
    'reload_empty': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
                     'PKM34_base_reload_empty', 120),
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
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
N_V7, N_AU = len(V7_BONES), len(AU_BONES)
MAP = np.array([AU_INDEX.get(n, -1) for n in V7_BONES])
B = {n: V7_BONES.index(n) for n in (
    'clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
    'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l')}

# rest geometry of the left arm
REST = {n: V7_REST[i] for n, i in B.items()}
e_rest = REST['lowerarm_l'][:3, 3]
s_rest = REST['upperarm_l'][:3, 3]
w_rest = REST['hand_l'][:3, 3]
u_rest = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f_rest = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
fore_len = float(np.linalg.norm(w_rest - e_rest))

rel = V7_VERTS - e_rest
t_all = rel @ f_rest / fore_len
radial = rel - np.outer(t_all * fore_len, f_rest)
radius = np.linalg.norm(radial, axis=1)

# left-arm band vertices only: close to the forearm axis
BAND = {
    'elbow': (t_all > -0.20) & (t_all < 0.20) & (radius < 0.075),
    'upper_band': (t_all > -0.60) & (t_all < -0.20) & (radius < 0.075),
    'fore_band': (t_all > 0.20) & (t_all < 0.85) & (radius < 0.075),
    'outer_elbow': (t_all > -0.15) & (t_all < 0.15) & (radius < 0.075),
}

# weights per band
wmap = np.zeros((len(V7_VERTS), len(B)))
for k, n in enumerate(B):
    wmap[:, k] = np.where(V7_WIDX == B[n], V7_WVAL, 0.0).sum(axis=1)
elbow_w = {n: float(wmap[BAND['elbow'], k].mean()) for k, n in enumerate(B)}

WATCH = ['upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l']


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


def angle_between(q1, q2):
    d = q1.rotation_difference(q2).angle
    return math.degrees(min(d, 2 * math.pi - d))


def run(blend, action_name, fps):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = fps
    start, end = map(int, action.frame_range)
    step = max(1, int(fps / 15))

    rows = []
    for frame in range(start, end + 1, step):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {n: rig.pose.bones[n].matrix.copy() for n in AU_BONES}
        delta_au = {n: pose[n] @ AU_REST_M[i].inverted()
                    for i, n in enumerate(AU_BONES)}
        delta_np = {n: np.array(m) for n, m in delta_au.items()}

        s = rig.pose.bones['upperarm_l'].matrix.translation
        e = rig.pose.bones['lowerarm_l'].matrix.translation
        w = rig.pose.bones['hand_l'].matrix.translation
        u = (e - s).normalized()
        f = (w - e).normalized()
        bend = math.degrees(u.angle(f))
        axis = f.copy()

        quats = {}
        for n in WATCH:
            m = delta_au[n]
            quats[n] = m.to_3x3().to_quaternion()
            if quats[n].w < 0:
                quats[n].negate()

        def twist(n):
            q = quats[n]
            v = Vector((q.x, q.y, q.z))
            return math.degrees(2 * math.atan2(v.dot(axis), q.w))

        skin = np.tile(np.eye(4), (N_V7, 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in delta_np:
                skin[i] = delta_np[n]
        posed = deform_with(skin)

        # outer elbow collapse: distance from the joint to the farthest surface
        # point along the outward bisector
        out_dir = -(Vector(u) + Vector(f)).normalized()
        elbow_out = e + out_dir * 0.0
        el = BAND['elbow']
        pv = posed[el] - np.array(elbow_out)
        proj = pv @ np.array(out_dir)
        depth = float(proj.max())
        rest_pv = V7_VERTS[el] - np.array(elbow_out)
        rest_depth = float((rest_pv @ np.array(out_dir)).max())

        rows.append({
            'frame': frame,
            'seconds': round(frame / fps, 4),
            'bend_deg': round(bend, 1),
            'elbow_out_mm': round(depth * 1000, 1),
            'elbow_out_rest_mm': round(rest_depth * 1000, 1),
            'twist_upperarm_l': round(twist('upperarm_l'), 1),
            'twist_up_tw01': round(twist('upperarm_twist_01_l'), 1),
            'twist_up_tw02': round(twist('upperarm_twist_02_l'), 1),
            'twist_lowerarm_l': round(twist('lowerarm_l'), 1),
            'twist_lo_tw02': round(twist('lowerarm_twist_02_l'), 1),
            'twist_lo_tw01': round(twist('lowerarm_twist_01_l'), 1),
            'd_up02_vs_lo': round(angle_between(quats['upperarm_twist_02_l'],
                                                quats['lowerarm_l']), 1),
            'd_lo_vs_lo02': round(angle_between(quats['lowerarm_l'],
                                                quats['lowerarm_twist_02_l']), 1),
            'd_lo02_vs_lo01': round(angle_between(quats['lowerarm_twist_02_l'],
                                                  quats['lowerarm_twist_01_l']), 1),
            'd_up_vs_up02': round(angle_between(quats['upperarm_l'],
                                                quats['upperarm_twist_02_l']), 1),
        })
    return rows


report = {'elbow_band_weights': {n: round(v, 3) for n, v in elbow_w.items()},
          'forearm_length_m': round(fore_len, 4)}
for key, (blend, action_name, fps) in CLIPS.items():
    report[key] = run(blend, action_name, fps)

(HERE / 'elbow_diagnosis.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

print('elbow band weights:', report['elbow_band_weights'])
for key in CLIPS:
    rows = report[key]
    print('\n== %s (%d samples) ==' % (key, len(rows)))
    print('%6s %5s | %5s %6s | %7s %7s %7s | %7s %7s %7s' % (
        'sec', 'bend', 'outmm', 'rest', 'up', 'up02', 'lo', 'lo02', 'lo01', 'up02-lo'))
    for r in rows[::max(1, len(rows) // 14)]:
        print('%6.2f %5.0f | %5.1f %6.1f | %7.1f %7.1f %7.1f | %7.1f %7.1f %7.1f' % (
            r['seconds'], r['bend_deg'], r['elbow_out_mm'], r['elbow_out_rest_mm'],
            r['twist_upperarm_l'], r['twist_up_tw02'], r['twist_lowerarm_l'],
            r['twist_lo_tw02'], r['twist_lo_tw01'], r['d_up02_vs_lo']))
print('\nDIAG_DONE')