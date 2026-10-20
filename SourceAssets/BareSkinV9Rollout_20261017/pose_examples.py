"""Pose-example correctives (JC_Pose_*) for the transitions the joint keys and held grips miss.

Per pose-source group: on the lead mesh, frames of every installed clip (ClipsSim = true clip data with the twist as shipped)
are scored by the pinholes left with all current correctives; greedily, the worst frame becomes an example
(whole-side fold untangle at that pose, pulled back to bind), unless it lies within 1.5 sigma of an
existing example or makes any held pose worse. The same example poses are then authored on every mesh of
the group. Output: Work/<batch>_pose/<key>.json (morphs_only payloads for install_batch.py).

python pose_examples.py batch1 [mesh substring ...]
"""
import sys, json, time, traceback
import numpy as np
from rollout import R, load_snapshot, key_of
from transfer import weld
from jc import Rig, Driver, frame_pose, pose_name, pose_value, pose_distance, pose_weight

import os
BATCH = sys.argv[1]; only = sys.argv[2:]
CLIPSRC = os.environ.get('V9R_CLIPSRC', 'ClipsSim')        # true clip data with the twist as it will be imported
plan = json.loads((R / (BATCH + '.json')).read_text())
OUT = R / 'Work' / (BATCH + os.environ.get('V9R_POSE_SUB', '_pose')); OUT.mkdir(exist_ok=True)
HELD_KEYS = ('idle', 'hold', 'ready')
# R2 (10-18): more examples per side, closer together, and a larger rest-space reach (the worst transition
# frames, e.g. LMG201 right hand at full supination, need up to ~3 cm to unfold; 0.5 cm left 16 of 70 folds)
K_MAX, MIN_COUNT, MIN_SEP, STEP, CAP = int(os.environ.get('V9R_KMAX', '24')), 4, 1.0, 2, 2.5
GROUPS = [g for g in os.environ.get('V9R_GROUPS', '').split(',') if g]     # redo only these groups ('|'-joined sources)


def is_held(path):
    n_ = '_'.join(path.split('/')[-1].lower().split('_')[2:])
    return any(k in n_ for k in HELD_KEYS) or n_ == 'guard' or n_.endswith('_guard')


def rotate(v, a, b):
    ax = np.cross(a, b); s = np.linalg.norm(ax); c = a @ b
    if s < 1e-9: return v
    ax /= s; th = np.arctan2(s, c)
    return v * np.cos(th) + np.cross(ax, v) * np.sin(th) + ax * (ax @ v) * (1 - np.cos(th))


class MeshState:
    def __init__(self, pk, leader_bones):
        self.pk = pk; self.key = key_of(pk)
        self.t = load_snapshot(pk); self.p = json.loads((R / 'Work' / BATCH / (self.key + '.json')).read_text())
        X = np.array(self.p['positions']); T = np.array(self.t['triangles']); self.T = T
        w, n = weld(X); self.w = w; P = np.zeros((n, 3)); P[w] = X; self.P = P
        W = [dict(x) for x in self.t['weights']]; vid = {v: i for i, v in enumerate(self.t['vertex_ids'])}; self.vid = vid
        for v, row in self.p['weights'].items(): W[vid[int(v)]] = row
        Ww = [None] * n
        for v in range(len(X)): Ww[w[v]] = W[v]
        sg = np.sign(np.einsum('ij,ij->', np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]), np.array(self.p['vertex_normals'])[T].mean(axis=1))) or 1.0
        self.rig = Rig(P, w[T], Ww, np.zeros(n), self.t['bones'], sg)
        self.names = list(self.p['morphs']); self.S = np.zeros((len(self.names), n, 3))
        for k, name in enumerate(self.names):
            for row in self.p['morphs'][name]:
                v = vid[row[0]]; self.S[k, w[v]] = np.array(row[1:4]) - X[v]
        if self.p.get('morphs_only'): pass
        self.new = {}
        self.driver = Driver(leader_bones, [n_ for n_ in self.names if n_.startswith(('JC_Grip_', 'JC_Pose_'))])
        self.face_side = {s: (self.rig.side[self.rig.TW] == s).any(axis=1) for s in 'lr'}

    def delta(self, pose):
        wts = self.driver.weights(pose); d = np.zeros_like(self.P)
        if self.names:
            wv = np.array([wts.get(n_, 0.0) for n_ in self.names])
            nz = wv > 1e-4
            if nz.any(): d += np.einsum('k,kvi->vi', wv[nz], self.S[nz])
        return d

    def posed(self, pose):
        Rm, Tv = self.rig.pose_matrices(pose); d = self.delta(pose)
        Xp, A = self.rig.lbs(self.P + d, Rm, Tv); return Xp, A

    def count(self, pose, s):
        Xp, _ = self.posed(pose); return len(self.rig.inverted(Xp, self.face_side[s]))

    def add_example(self, pose, s, sig):
        Xp, A = self.posed(pose); mask = (self.rig.side == s).astype(float)
        corr, g1 = self.rig.fold_guard(Xp, np.zeros_like(self.P), mask)
        if g1['folds_before'] == 0: return None
        for _ in range(4): corr = .5 * corr + .5 * (self.rig.Lop @ corr) * (mask > 0)[:, None]
        corr, g2 = self.rig.fold_guard(Xp, corr, mask)
        rest = np.linalg.solve(A, corr[:, :, None])[:, :, 0]
        mag = np.linalg.norm(rest, axis=1); rest *= np.minimum(1, CAP / np.maximum(mag, 1e-9))[:, None]; rest[mag < .004] = 0
        if not (np.linalg.norm(rest, axis=1) > .012).any(): return None
        name = pose_name(s, sig)
        self.names.append(name); self.S = np.concatenate([self.S, rest[None]], axis=0); self.new[name] = rest
        self.driver.poses[s].append((name, [pose_value(x) for x in name.split('_')[3:11]]))
        return name

    def remove(self, name):
        k = self.names.index(name); self.names.pop(k); self.S = np.delete(self.S, k, axis=0); self.new.pop(name, None)
        for s in 'lr': self.driver.poses[s] = [x for x in self.driver.poses[s] if x[0] != name]

    def payload(self):
        X = np.array(self.p['positions']); VN = np.array(self.p['vertex_normals']); G0 = self.rig.vnormals(self.P); morphs = {}
        for name, d in self.new.items():
            moved = np.linalg.norm(d, axis=1) > .012; G1 = self.rig.vnormals(self.P + d); rows = []
            for v in range(len(X)):
                if not moved[self.w[v]]: continue
                nn = rotate(VN[v], G0[self.w[v]], G1[self.w[v]]); nn /= np.linalg.norm(nn)
                rows.append([int(self.t['vertex_ids'][v]), *map(float, X[v] + d[self.w[v]]), *map(float, nn)])
            morphs[name] = rows
        # installed after the mesh payload it was authored on: install checks the mesh receipt hash then
        return dict(path=self.pk, key=self.key, sha=None, after_mesh_receipt=True, morphs_only=True, morphs=morphs, stale_prefix='JC_Pose_', keep=[],
                    pose_source=self.p.get('pose_source'), vertex_ids=self.p['vertex_ids'][:1], positions=self.p['positions'][:1],
                    vertex_normals=self.p['vertex_normals'][:1])


def frames_of(sources):
    out = []
    for s_ in sources:
        f = R / CLIPSRC / (s_ + '.json')
        if not f.exists(): continue
        cd = json.loads(f.read_text())
        for path, c in cd['clips'].items():
            if 'frames' not in c: continue
            held = is_held(path)
            for fi in range(0, len(c['frames']), 1 if held else STEP):
                out.append(dict(clip=path, held=held, pose=frame_pose(c, cd['bones'], fi), src=s_, fi=fi))
    return out


groups = {}
for e in plan['meshes']:
    srcs = tuple(e.get('pose_sources') or [e['pose_source']])
    if only and not any(o in e['mesh'] for o in only): continue
    if GROUPS and '|'.join(srcs) not in GROUPS: continue
    groups.setdefault(srcs, []).append(e)
report = json.loads((OUT / 'report.json').read_text()) if (OUT / 'report.json').exists() else {}
for srcs, entries in groups.items():
    todo = [e for e in entries if not (OUT / (key_of(e['mesh']) + '.json')).exists()]
    if not todo: continue
    t0 = time.time()
    try:
        leader = load_snapshot(plan['viewmodels'][srcs[0]])['bones']
        lead_e = next((e for e in entries if e.get('role') == 'viewmodel'), entries[0])
        lead = MeshState(lead_e['mesh'], leader)
        frames = frames_of(srcs); examples = []
        for s in 'lr':
            if s not in lead.driver.sides or (lead.rig.side == s).sum() < 50: continue
            for fr in frames: fr['sig_' + s] = lead.driver.signature(fr['pose'], s); fr['n_' + s] = lead.count(fr['pose'], s)
            base_held = {id(fr): fr['n_' + s] for fr in frames if fr['held']}
            rejected = set(); added = 0; passes = 0; added_at_pass = 0
            while added < K_MAX + 8:
                # past the budget only frames that are still bad (>= 15) get extra examples (A762 reload stayed at 20
                # because later examples pushed it up after its turn)
                floor = MIN_COUNT if added < K_MAX else 15
                # a frame that is still bad may sit closer to an existing example (that example only half reaches it)
                cand = [fr for fr in frames if fr['n_' + s] >= floor and id(fr) not in rejected and
                        all(pose_distance(fr['sig_' + s], ex[2]) >= (MIN_SEP if fr['n_' + s] < 15 else .35) for ex in examples if ex[1] == s)]
                if not cand:
                    # frames rejected early can work once other examples exist: retry them while passes still add
                    # something (A762 reload 20 -> 0 was refused early and accepted on the final state)
                    if not rejected or passes >= 4 or (passes and added == added_at_pass): break
                    passes += 1; added_at_pass = added; rejected = set(); continue
                fr = max(cand, key=lambda x: x['n_' + s])
                sig = [round(x) for x in fr['sig_' + s]]
                if pose_name(s, sig) in lead.names: rejected.add(id(fr)); continue
                name = lead.add_example(fr['pose'], s, sig)
                if name is None: rejected.add(id(fr)); continue
                sig_r = [pose_value(x) for x in name.split('_')[3:11]]
                near = [x for x in frames if pose_weight(x['sig_' + s], sig_r) > .02]
                newn = {id(x): lead.count(x['pose'], s) for x in near}
                worse = [x for x in near if x['held'] and newn[id(x)] > base_held[id(x)] + 1]
                # the neighbourhood must improve: as a whole, or (R3c) in its worst frame with at most 15 % more in
                # total - QBZ191 equip 17 -> 0 left 12 neighbours at 3 and was refused by the sum rule alone
                old_sum = sum(x['n_' + s] for x in near); new_sum = sum(newn.values())
                old_max = max(x['n_' + s] for x in near); new_max = max(newn.values())
                better = (new_sum < old_sum or (new_max <= old_max - 3 and new_sum <= 1.15 * old_sum)
                          or (new_max <= old_max / 2 and new_sum <= 1.3 * old_sum))   # LMG201 reload 24 -> 0, neighbours 1 -> 8
                if worse or newn[id(fr)] >= fr['n_' + s] or not better:
                    lead.remove(name); rejected.add(id(fr)); continue
                for x in near: x['n_' + s] = newn[id(x)]
                examples.append((name, s, sig_r, fr['clip'], fr['src'], fr['fi'])); added += 1
        # author the same examples on every mesh of the group (the lead keeps its own)
        results = {lead_e['mesh']: lead}
        for e in entries:
            if e['mesh'] == lead_e['mesh']: continue
            ms = MeshState(e['mesh'], leader); results[e['mesh']] = ms
            for name, s, sig_r, clip, src_, fi in examples:
                if s not in ms.driver.sides or (ms.rig.side == s).sum() < 50: continue
                fr = next(x for x in frames if x['clip'] == clip and x['src'] == src_ and x['fi'] == fi)
                ms.add_example(fr['pose'], s, [round(v) for v in sig_r])
        for pk, ms in results.items():
            if not (OUT / (ms.key + '.json')).exists():
                (OUT / (ms.key + '.json')).write_text(json.dumps(ms.payload()))
        # summary on the lead: worst held and worst overall, before -> after
        held_b = max([x for x in base_held.values()] or [0]) if examples or True else 0
        summ = dict(examples=[e_[0] for e_ in examples], lead=lead_e['mesh'], seconds=round(time.time() - t0),
                    worst_after={s: max([fr['n_' + s] for fr in frames if 'n_' + s in fr] or [0]) for s in 'lr'},
                    held_after={s: max([fr['n_' + s] for fr in frames if fr['held'] and 'n_' + s in fr] or [0]) for s in 'lr'})
        report['|'.join(srcs)] = summ
        (OUT / 'report.json').write_text(json.dumps(report, indent=1))
        print('%-40s examples %2d  worst after %s held after %s  %ds' % ('|'.join(srcs)[:40], len(examples), summ['worst_after'], summ['held_after'], summ['seconds']), flush=True)
    except Exception:
        (OUT / ('error_' + '_'.join(srcs)[:60] + '.txt')).write_text(traceback.format_exc())
        print('FAILED', srcs, traceback.format_exc().splitlines()[-1], flush=True)
