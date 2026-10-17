"""Locate the loading port / receiver underside of both guns in their WPN_root frame (metres)."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from rig import fk, row2m, inv, m2q

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text()); G = json.loads((O / 'geometry.json').read_text())


def gun_points(key, sk):
    g = G[key]; skin = {i for i, s in enumerate(g['slots']) if any(k in s.lower() for k in ('skin', 'bare', 'manny', 'arm', 'hand'))}
    v = np.array(g['positions']); t = np.array(g['triangles']); m = np.array(g['materials']); dom = np.array(g['dominant'])
    keep = np.unique(t[~np.isin(m, list(skin))])
    root = row2m(sk['ref_world']['WPN_root'])
    loc = (inv(root) @ np.c_[v, np.ones(len(v))].T).T[:, :3]
    return loc, dom, keep, g['slots'], skin, t, m


for key, sk in (('super90', D['super90']), ('m870', D['m870'])):
    loc, dom, keep, slots, skin, t, m = gun_points(key, sk)
    print('==', key, 'slots', slots, 'skin slots', sorted(skin))
    gp = loc[keep]
    print(' gun bbox min', gp.min(0).round(3), 'max', gp.max(0).round(3))
    print(' dominant bones of gun verts', Counter(dom[keep]).most_common(8))
    for bone in ('WPN_Load', 'WPN_bolt', 'WPN_Trigger'):
        sel = keep[dom[keep] == bone]
        if len(sel): print(' ', bone, 'n', len(sel), 'centroid', loc[sel].mean(0).round(3), 'min', loc[sel].min(0).round(3), 'max', loc[sel].max(0).round(3))
    root = row2m(sk['ref_world']['WPN_root'])
    for bone in ('WPN_Load', 'WPN_SOCKET_Magazine', 'WPN_Shell', 'WPN_bolt', 'WPN_SOCKET_Muzzle', 'WPN_SOCKET_Eject', 'WPN_Trigger'):
        b = inv(root) @ row2m(sk['ref_world'][bone]); print('  ref', bone, b[:3, 3].round(3))
# Super90 seat: WPN_Shell relative to WPN_root at source frame 110 (normal_7), also dock 87 and 75.
s = D['super90']; clip = D['super90_clips']['normal_7']['rows']
for f in (60, 75, 87, 92, 100, 110, 118, 124, 130):
    w = fk(s['names'], s['parents'], clip[f]); r = w['WPN_root']
    sh = inv(r) @ w['WPN_Shell']; pl = inv(r) @ w['WPN_SOCKET_Magazine']; hl = inv(r) @ w['hand_l']
    yax = sh[:3, 1] / np.linalg.norm(sh[:3, 1])
    print('f%3d shell %s yaxis %s plunger %s hand_l %s root(world cm) %s' % (f, sh[:3, 3].round(3), yax.round(3), pl[:3, 3].round(3), hl[:3, 3].round(3), r[:3, 3].round(1)))
idle = fk(s['names'], s['parents'], D['super90_clips']['idle']['rows'][0])
mi = fk(D['m870']['names'], D['m870']['parents'], D['m870_clips']['idle']['rows'][0])
for name, w in (('super90 idle', idle), ('m870 idle', mi)):
    r = w['WPN_root']; print(name, 'WPN_root cm', r[:3, 3].round(2), 'axes x', (r[:3, 0] / np.linalg.norm(r[:3, 0])).round(3), 'y', (r[:3, 1] / np.linalg.norm(r[:3, 1])).round(3), 'z', (r[:3, 2] / np.linalg.norm(r[:3, 2])).round(3), 'scale', np.linalg.norm(r[:3, :3], axis=0).round(2))
    print('   hand_l in gun', (inv(r) @ w['hand_l'])[:3, 3].round(3), 'hand_r in gun', (inv(r) @ w['hand_r'])[:3, 3].round(3))
