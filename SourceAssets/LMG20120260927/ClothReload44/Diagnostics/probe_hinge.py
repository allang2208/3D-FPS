"""Elbow hinge axis of the PKM V7 / 201 left arm in the upper-arm helper frame, and how far
the helpers are rolled away from the actual bend axis during the reloads."""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import diag_lib as D

BI, REST = D.BI, D.REST
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
unit = lambda v: v / np.linalg.norm(v)
H = 'upperarm_twist_02_l'


def hinge(W):
    a, e, t = (W[BI[n]][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
    u, f = e - a, t - e
    c = np.cross(u, f)
    bend = np.degrees(np.arctan2(np.linalg.norm(c), u @ f))
    return unit(c), bend, unit(u)


# rest skeleton
rel = rot(REST[BI['upperarm_l']]).T @ rot(REST[BI['lowerarm_l']])
rv = R.from_matrix(rel).as_rotvec()
hr, br, _ = hinge(REST)
h_rest_local = rot(REST[BI[H]]).T @ hr
print('rest: elbow bend %.1f deg, hinge axis in %s local %s; lowerarm-vs-upperarm rotvec axis %s (%.1f deg)' % (
    br, H, np.round(h_rest_local, 3), np.round(rot(REST[BI['upperarm_l']]).T @ rot(REST[BI[H]]) @ unit(rv) if np.linalg.norm(rv) > 1e-6 else rv, 3),
    np.degrees(np.linalg.norm(rv))))
for fam in ('201_idle', '201_vertical_idle', '201_canted_idle', '201_prism_idle', '201_angled_idle'):
    idle = json.loads((D.HERE / 'Inputs' / (fam + '.json')).read_text())
    W0 = D.worlds({n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])})[0]
    h, b, u = hinge(W0)
    hl = rot(W0[BI[H]]).T @ h
    print('%-18s bend %5.1f  hinge in helper local %s  angle to rest %.1f deg' % (
        fam, b, np.round(hl, 3), np.degrees(np.arccos(np.clip(hl @ h_rest_local, -1, 1)))))


def roll_off(W, hl_ref):
    h, b, u = hinge(W)
    g = rot(W[BI[H]]) @ hl_ref
    g, h2 = unit(g - u * (g @ u)), unit(h - u * (h @ u))
    return np.degrees(np.arctan2(np.cross(g, h2) @ u, g @ h2)), b


for label, f in (('201 base reload', 'Tracks/base_b53_tracks.json.gz'), ('PKM reload_empty', 'Diagnostics/pkm_reload_empty_asbase.json.gz'),
                 ('PKM reload', 'Diagnostics/pkm_reload_asbase.json.gz')):
    tr = D.load_tracks(D.HERE / f)
    W = D.worlds(tr, np.arange(0, len(tr['hand_l']), 3))
    rows = np.array([roll_off(W[k], h_rest_local) for k in range(len(W))])
    bent = rows[:, 1] > 35
    print('%-18s helper roll off the bend axis (frames bent >35 deg): %s' % (
        label, 'min %.0f max %.0f median %.0f' % (rows[bent, 0].min(), rows[bent, 0].max(), np.median(rows[bent, 0])) if bent.any() else 'n/a'))
