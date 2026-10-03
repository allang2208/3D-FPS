"""Empirical twist profile of the PKM left arm surface.

For each slice along the limb, the mean roll change of the surface about the
limb axis, measured in the arm's own bend-plane frame.  This needs no
assumption about bone axis conventions.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 60, 0),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120, 980),
    'reload_empty': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
                     'PKM34_base_reload_empty', 120, 621),
}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [__import__('mathutils').Matrix(m.tolist())
             for m in author['rest'].astype(np.float64)]
N_V7 = len(V7_BONES)
IDX = {n: V7_BONES.index(n) for n in (
    'upperarm_l', 'lowerarm_l', 'hand_l',
    'upperarm_twist_01_l', 'upperarm_twist_02_l',
    'lowerarm_twist_01_l', 'lowerarm_twist_02_l')}

e_rest = V7_REST[IDX['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[IDX['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[IDX['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
rel = V7_VERTS - e_rest
t_all = rel @ f0 / FLEN
radius = np.linalg.norm(rel - np.outer(t_all * FLEN, f0), axis=1)
ARM = (radius < 0.075) & (t_all > -0.75) & (t_all < 1.15)

p1_0 = u0 - (u0 @ f0) * f0
p1_0 /= np.linalg.norm(p1_0)
p2_0 = np.cross(f0, p1_0)
perp0 = rel - np.outer(rel @ f0, f0)
phi0 = np.arctan2(perp0 @ p2_0, perp0 @ p1_0)

# weights, for interpreting the profile
wmap = {n: np.where(V7_WIDX == i, V7_WVAL, 0.0).sum(axis=1) for n, i in IDX.items()}

EDGES = np.arange(-0.70, 1.15, 0.05)


def deform_with(skin):
    out = np.zeros((len(V7_VERTS), 3))
    homo = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)
    for k in range(V7_WIDX.shape[1]):
        idx = V7_WIDX[:, k]
        w = V7_WVAL[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             homo[act])[:, :3]
    return out


report = {}
for key, (blend, action_name, fps, frame) in CLIPS.items():
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(frame)
    bpy.context.view_layer.update()

    delta = {}
    for i, n in enumerate(AU_BONES):
        delta[n] = rig.pose.bones[n].matrix @ AU_REST_M[i].inverted()
    s = np.array(rig.pose.bones['upperarm_l'].matrix.translation)
    e = np.array(rig.pose.bones['lowerarm_l'].matrix.translation)
    w = np.array(rig.pose.bones['hand_l'].matrix.translation)
    u = (e - s) / np.linalg.norm(e - s)
    f = (w - e) / np.linalg.norm(w - e)
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

    rows = []
    for lo in EDGES[:-1]:
        sel = ARM & (t_all >= lo) & (t_all < lo + 0.05)
        if sel.sum() < 12:
            continue
        rows.append({
            't': round(float(lo + 0.025), 3),
            'n': int(sel.sum()),
            'roll': round(float(dphi[sel].mean()), 1),
            'spread': round(float(np.percentile(dphi[sel], 95)
                                  - np.percentile(dphi[sel], 5)), 1),
            'r_mm': round(float(radius[sel].mean() * 1000), 1),
            'w': {n: round(float(wmap[n][sel].mean()), 2)
                  for n in ('upperarm_twist_01_l', 'upperarm_twist_02_l',
                            'lowerarm_l', 'lowerarm_twist_02_l',
                            'lowerarm_twist_01_l')},
        })
    report[key] = rows

(HERE / 'twist_profile.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

for key, rows in report.items():
    print('\n===== %s =====' % key)
    print('%6s %5s %7s %8s | %5s %5s %5s %5s %5s' % (
        't', 'n', 'roll', 'spread', 'ut01', 'ut02', 'la', 'lt02', 'lt01'))
    for r in rows:
        w = r['w']
        print('%6.2f %5d %7.1f %8.1f | %5.2f %5.2f %5.2f %5.2f %5.2f' % (
            r['t'], r['n'], r['roll'], r['spread'],
            w['upperarm_twist_01_l'], w['upperarm_twist_02_l'], w['lowerarm_l'],
            w['lowerarm_twist_02_l'], w['lowerarm_twist_01_l']))
print('\nPROFILE_DONE')