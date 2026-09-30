"""Left upper arm / elbow structure of the PKM V7 bare arm (the 201 uses the same skin)
and its cross-section during the 201 and PKM reloads.

1. weights by station along shoulder->elbow->wrist (rest pose)
2. per frame: upper-arm helper roll vs the humerus (IK / elbow-plane) frame, and the skin
   cross-section radius of upper arm and forearm slices relative to the idle pose
"""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import diag_lib as D

BI, NAMES, REST = D.BI, D.NAMES, D.REST
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
unit = lambda v: v / np.linalg.norm(v)
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
P = lambda n: REST[BI[n]][:3, 3]
S0, E0, H0 = P('upperarm_l'), P('lowerarm_l'), P('hand_l')
arm_bones = [n for n in ('clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
                         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l')]
ids = [BI[n] for n in arm_bones]
left = np.isin(skin.idx[:, 0], ids)
v = np.where(left)[0]


def station(p):
    """-1..0 shoulder->elbow, 0..1 elbow->wrist (rest)."""
    u = (p - S0) @ (E0 - S0) / ((E0 - S0) @ (E0 - S0))
    f = (p - E0) @ (H0 - E0) / ((H0 - E0) @ (H0 - E0))
    return np.where(u < 1, u - 1, f)


st = station(skin.p[v])
print('== rest weights by station (share of each bone in the slice) ==')
edges = np.array([-1.1, -.8, -.6, -.4, -.25, -.1, 0, .1, .25, .45, .65, .85, 1.0])
for a, b in zip(edges, edges[1:]):
    m = v[(st >= a) & (st < b)]
    if not len(m):
        continue
    tot = {}
    for k in range(skin.idx.shape[1]):
        for bi, w in zip(skin.idx[m, k], skin.w[m, k]):
            if w > 0:
                tot[NAMES[bi]] = tot.get(NAMES[bi], 0) + w
    s = sum(tot.values())
    print('%5.2f..%5.2f n=%4d %s' % (a, b, len(m), ', '.join('%s %.2f' % (n.replace('_l', ''), w / s)
                                                         for n, w in sorted(tot.items(), key=lambda x: -x[1])[:4])))


def section(W, sel_st, lo, hi, upper):
    """mean radial distance of the skin from the live bone axis in a station band."""
    m = v[(sel_st >= lo) & (sel_st < hi)]
    p = skin.pose(W, m)
    a, b = (W[BI['upperarm_l']][:3, 3], W[BI['lowerarm_l']][:3, 3]) if upper else (W[BI['lowerarm_l']][:3, 3], W[BI['hand_l']][:3, 3])
    ax = unit(b - a)
    d = p - a
    return float(np.linalg.norm(d - np.outer(d @ ax, ax), axis=1).mean())


def helper_roll(W):
    """roll of upperarm_twist_01/02 about the humerus axis relative to upperarm_l (vs idle)."""
    out = []
    for n in ('upperarm_twist_01_l', 'upperarm_twist_02_l'):
        rel = rot(W[BI['upperarm_l']]).T @ rot(W[BI[n]])
        out.append(rel)
    return out


BANDS_U = [(-.85, -.65), (-.65, -.45), (-.45, -.25)]
BANDS_F = [(.15, .35), (.35, .55), (.55, .75)]


def run(label, tracks, idle_W, every=6):
    W = D.worlds(tracks, np.arange(0, len(tracks['hand_l']), every))
    ru0 = [section(idle_W, st, *b, True) for b in BANDS_U]
    rf0 = [section(idle_W, st, *b, False) for b in BANDS_F]
    h0 = helper_roll(idle_W)
    rows = []
    for k in range(len(W)):
        ru = min(section(W[k], st, *b, True) / r0 for b, r0 in zip(BANDS_U, ru0))
        rf = min(section(W[k], st, *b, False) / r0 for b, r0 in zip(BANDS_F, rf0))
        hr = helper_roll(W[k])
        ax = np.array([1.0, 0, 0])  # bone-local long axis (UE bones: X)
        rolls = [np.degrees(R.from_matrix(h0[j].T @ hr[j]).magnitude()) for j in range(2)]
        rows.append((k * every / 120, ru, rf, rolls[0], rolls[1]))
    rows = np.array(rows)
    i = rows[:, 1].argmin()
    print('%-22s upper-arm section min %.2f @%.2fs (helper roll vs humerus %.0f/%.0f deg) | forearm section min %.2f | helper roll max %.0f' % (
        label, rows[i, 1], rows[i, 0], rows[i, 3], rows[i, 4], rows[:, 2].min(), rows[:, 3:].max()))
    return rows


idle = json.loads((D.HERE / 'Inputs/201_idle.json').read_text())
W0 = D.worlds({n: np.array([v_]) for n, v_ in zip(D.NAMES, idle['poses'][0])})[0]
print('== cross-section during the reloads (ratio to idle; 1 = unchanged) ==')
r201 = run('201 base reload', D.load_tracks(D.HERE / 'Tracks/base_b53_tracks.json.gz'), W0)
r201e = run('201 base reload_empty', D.load_tracks(D.HERE / 'Tracks/base_empty_b53_tracks.json.gz'), W0)
pk = D.load_tracks(D.HERE / 'Diagnostics/pkm_reload_empty_asbase.json.gz')
Wp0 = D.worlds(pk, [0])[0]
rp = run('PKM reload_empty', pk, Wp0)
rpn = run('PKM reload', D.load_tracks(D.HERE / 'Diagnostics/pkm_reload_asbase.json.gz'), Wp0)
np.savez(D.HERE / 'Diagnostics/upperarm_probe.npz', r201=r201, r201e=r201e, rp=rp, rpn=rpn)
