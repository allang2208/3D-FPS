"""Replay the runtime 201 belt physics (LMG201BeltDynamics + FPKMSoftChain) on the
ClothReload44 tracks with the current Belt49 cells, and check the left-hand belt
contacts.  Static, level viewmodel (component == world, gravity -Z).

python -X utf8 sim_belt_phys.py [family ...]
"""
import sys, json
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
import diag_lib as D

FPS = 60.0
GRAV = -980.0
OLD_HIDDEN, NEW_VISIBLE = 2.45, 2.80
BI, NAMES, REST_INV = D.BI, D.NAMES, D.REST_INV
ramp = lambda x: (lambda c: c * c * (3 - 2 * c))(np.clip(x, 0, 1))


class Chain:
    """Port of FPKMSoftChain::Solve (PKMSoftBeltDynamics.cpp)."""

    def __init__(self):
        self.last = -1.0

    def reset(self):
        self.last = -1.0

    def solve(self, guide, now, gravity, pinned_start, pin_end, strength, corridor):
        guide = np.asarray(guide, float)
        if len(guide) < 3 or strength <= .001:
            self.reset()
            return guide.copy()
        n = len(guide)
        el = now - self.last
        if self.last < 0 or el < 0 or el > .12 or getattr(self, 'pos', np.zeros((0, 3))).shape[0] != n or \
                np.sum((guide[0] - self.prev[0]) ** 2) > 6400:
            self.pos = guide.copy(); self.prev = guide.copy(); self.vel = np.zeros_like(guide)
            self.L = np.linalg.norm(np.diff(guide, axis=0), axis=1)
            self.last = now
            return guide.copy()
        pinned = lambda i: i < pinned_start or (pin_end and i == n - 1)
        steps = max(1, int(np.ceil(el * 240)))
        dt = el / steps
        for s in range(steps):
            goals = self.prev + (guide - self.prev) * (s + 1) / steps
            before = self.pos.copy()
            for i in range(n):
                if pinned(i):
                    self.pos[i] = goals[i]
                    continue
                self.vel[i] *= np.exp(-3.6 * dt)
                self.vel[i] += (np.array([0, 0, gravity * .65]) * strength + (goals[i] - self.pos[i]) * 42) * dt
                self.pos[i] += self.vel[i] * dt
            for it in range(20):
                for i in range(n):
                    if pinned(i):
                        self.pos[i] = goals[i]
                        continue
                    u = i / (n - 1)
                    free = .2 + .8 * np.sin(np.pi * u) if pin_end else u
                    d = self.pos[i] - goals[i]
                    m = corridor * free * strength
                    ln = np.linalg.norm(d)
                    if ln > m:
                        d *= m / ln
                    self.pos[i] = goals[i] + d
                for j in range(n - 1):
                    i = n - 2 - j if it % 2 else j
                    wa, wb = (0. if pinned(i) else 1.), (0. if pinned(i + 1) else 1.)
                    dl = self.pos[i + 1] - self.pos[i]
                    dist = np.linalg.norm(dl)
                    if wa + wb == 0 or dist < 1e-8:
                        continue
                    c = dl * ((dist - self.L[i]) / (dist * (wa + wb)))
                    self.pos[i] += c * wa
                    self.pos[i + 1] -= c * wb
            for i in range(n):
                if pinned(i):
                    self.pos[i] = goals[i]
                self.vel[i] = (self.pos[i] - before[i]) / dt
        self.prev = guide.copy()
        self.last = now
        return self.pos.copy()


def between(a, b):
    a, b = D.unit(a), D.unit(b)
    return D.rotation_between(a, b)


z = np.load(Path(__file__).parent / 'belt49_cells.npz')
cpos, ccell, ctris = z['pos'], z['cell'], z['tris']
OLD = ['LMG201_Belt_%02d' % k for k in range(6)]
NEW = ['New_LMG201_Belt_%02d' % k for k in range(6)]
cells = {}
for n in OLD:
    vid = np.where(ccell == n)[0]
    remap = -np.ones(len(cpos), int)
    remap[vid] = np.arange(len(vid))
    tri = ctris[np.all(np.isin(ctris, vid), 1)]
    cells[n] = dict(v=cpos[vid], f=remap[tri], c=cpos[vid].mean(0))
body = D.Body()
newparts = {n: body.parts[n] for n in NEW}
new_skin = {n: D.Skin(body.pos[s], (body.bi[s], body.bw[s])) for n, s in newparts.items()}
new_tris = {}
for n, s in newparts.items():
    inp = np.zeros(len(body.pos), bool); inp[s] = True
    remap = -np.ones(len(body.pos), int); remap[s] = np.arange(len(s))
    new_tris[n] = remap[body.tris[inp[body.tris].all(1)]]
box = body.parts['LMG201_Box']
box_skin = D.Skin(body.pos[box], (body.bi[box], body.bw[box]))
inb = np.zeros(len(body.pos), bool); inb[box] = True
rb = -np.ones(len(body.pos), int); rb[box] = np.arange(len(box))
box_tris = rb[body.tris[inb[body.tris].all(1)]]
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
hand_bones = {BI[n] for n in NAMES if n.endswith('_l') and (n == 'hand_l' or n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky')))}
hand_v = np.where(np.isin(skin.dom, list(hand_bones)))[0]
tip_bones = {BI['thumb_03_l'], BI['index_03_l'], BI['middle_03_l']}
tip_v = np.where(np.isin(skin.dom, list(tip_bones)))[0]
# Cell centres the runtime uses: Belt49 rest centroids in each bone's rest frame.
cent = {n: cells[n]['c'] for n in OLD}
cent.update({NEW[k]: cells[OLD[k]]['c'] for k in range(6)})


def cell_world(W, n, v):
    S = W[BI[n]] @ REST_INV[BI[n]]
    return v @ S[:3, :3].T + S[:3, 3]


def guides(W, names):
    return np.array([(W[BI[n]] @ REST_INV[BI[n]] @ np.r_[cent[n], 1])[:3] for n in names])


def apply(W, names, G, Sv):
    W = W.copy()
    for i in range(1, 5):
        Rt = between(G[i + 1] - G[i - 1], Sv[i + 1] - Sv[i - 1])
        m = W[BI[names[i]]].copy()
        m[:3, :3] = Rt @ m[:3, :3]
        m[:3, 3] = Sv[i] + Rt @ (m[:3, 3] - G[i])
        W[BI[names[i]]] = m
    return W


def penetration(P, V, F, pad=.4):
    lo, hi = V.min(0) - pad, V.max(0) + pad
    m = np.all((P > lo) & (P < hi), 1)
    if not m.any():
        return 0, 0.0
    w = D.winding_number(P[m], V, F)
    ins = w > .5
    if not ins.any():
        return 0, 0.0
    d, _ = cKDTree(V).query(P[m][ins])
    return int(ins.sum()), float(d.max())


def run(fam, empty):
    tr = D.load_tracks(D.HERE / 'Tracks' / (fam + '_tracks.json.gz'))
    nf = len(tr['hand_l'])
    frames = np.arange(0, nf, int(120 / FPS))
    Wall = D.worlds(tr, frames)
    chains = {'old': Chain(), 'new': Chain()}
    rep = dict(dev_old=0., dev_new=0., pen_anim=[0, 0.], pen_phys=[0, 0.], tip_gap=[], cell5_out_view=0, cell5_out=0, pop_cm=0., pop_at=None)
    prev_c = {}
    box_in0 = None
    for k, f in enumerate(frames):
        t = f / 120.0
        W = Wall[k]
        Wp = W
        vis = []
        for side, names in (('old', OLD), ('new', NEW)):
            visible = (t < OLD_HIDDEN and not empty) if side == 'old' else t >= NEW_VISIBLE
            st = (.6 * ramp((t - 1.60) / .18) if side == 'old'
                  else .6 * ramp((t - NEW_VISIBLE) / .24) * (1 - ramp((t - 4.55) / .23)))
            if not visible or st < .001:
                chains[side].reset()
                if visible:
                    vis += names
                continue
            vis += names
            G = guides(W, names)
            Sv = chains[side].solve(G, t, GRAV, 1, True, st, .65)
            rep['dev_' + side] = max(rep['dev_' + side], float(np.linalg.norm(Sv - G, axis=1).max()))
            Wp = apply(Wp, names, G, Sv)
        if not vis:
            continue
        for n in vis:
            c = cell_world(Wp, n, cells[n]['v']).mean(0) if n in cells else new_skin[n].pose(Wp).mean(0)
            if n in prev_c and np.linalg.norm(c - prev_c[n]) > rep['pop_cm']:
                rep['pop_cm'], rep['pop_at'] = float(np.linalg.norm(c - prev_c[n])), (round(t, 3), n)
            prev_c[n] = c
        hp = skin.pose(W, hand_v)
        tp = skin.pose(W, tip_v)
        for key, WW in (('pen_anim', W), ('pen_phys', Wp)):
            for n in vis:
                if n in cells:
                    V, F = cell_world(WW, n, cells[n]['v']), cells[n]['f']
                else:
                    V, F = new_skin[n].pose(WW), new_tris[n]
                c, d = penetration(hp, V, F)
                if c:
                    rep[key][0] = max(rep[key][0], c)
                    if d > rep[key][1]:
                        rep[key][1] = d
                        rep[key + '_at'] = (round(t, 3), n)
        # finger tips to the held cell 0 during the pinch holds
        held = OLD[0] if (1.62 <= t <= 1.76 and not empty) else (NEW[0] if 3.86 <= t <= 4.78 else None)
        if held:
            V = cell_world(Wp, held, cells[OLD[0]]['v']) if held in cells else new_skin[held].pose(Wp)
            rep['tip_gap'].append(float(cKDTree(V).query(tp)[0].min()))
        # old cell 5 (rigid, bigger than before) leaving the pouch while it is visible
        if 'LMG201_Belt_05' in vis and 'LMG201_Box' in body.parts:
            V5 = cell_world(Wp, 'LMG201_Belt_05', cells['LMG201_Belt_05']['v'])
            B = box_skin.pose(Wp)
            inside = D.winding_number(V5, B, box_tris) > .5
            if box_in0 is None:
                box_in0 = inside
            out = box_in0 & ~inside
            eye, fw, r, u = D.camera(D.framing_alpha(t))
            iv, _ = D.view_metrics(V5[out], eye, fw, r, u)
            rep['cell5_out'] = max(rep['cell5_out'], int(out.sum()))
            rep['cell5_out_view'] = max(rep['cell5_out_view'], int(iv.sum()))
    g = rep.pop('tip_gap')
    rep['tip_gap_cm_hold'] = [round(min(g), 3), round(max(g), 3)] if g else None
    return rep


if __name__ == '__main__':
    fams = sys.argv[1:] or ['base']
    res = {}
    for fam in fams:
        for empty in (False, True):
            key = fam + ('_empty' if empty else '')
            res[key] = run(fam, empty)
            print(key, json.dumps(res[key]), flush=True)
    (Path(__file__).parent / 'belt_physics_check.json').write_text(json.dumps(res, indent=2))
