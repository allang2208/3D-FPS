"""Generic V9 joint correctives for one rollout mesh (port of BareSkinV9M4 correctives.py + grip_correctives.py).

Works on the welded V9 rest surface of the target in its own bind pose and its own reference skeleton.
Drivers mirror UFPSArmJointCorrectiveComponent and are evaluated on the pose-source (leader) skeleton.
Shapes: elbow 20/75/110/135, wrist flexion A/B, radial, ulnar (per side present), held-grip examples.
Every key is fold-guarded: no fold the correction introduces, and folds inside the zone are untangled.
"""
import json
import numpy as np
import scipy.sparse as sp
from scipy.spatial.transform import Rotation as Rot


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def tent(x, a, b, c): return float(np.clip((x - a) / (b - a), 0, 1) if x <= b else np.clip((c - x) / (c - b), 0, 1))


class Rig:
    def __init__(self, P, TW, W, region_v, bones, sgn):
        """P welded rest (n,3); TW welded triangles; W welded weight rows; region_v per welded vertex;
        bones {name: {index, parent, t, q}} of this mesh; sgn = outward sign of (b-a)x(c-a)."""
        self.P = P; self.TW = TW; self.W = W; self.vreg = region_v; self.sgn = sgn; self.n = len(P)
        self.bones = bones
        self.ref_t = {k: np.array(v['t']) for k, v in bones.items()}
        self.ref_q = {k: Rot.from_quat(v['q']) for k, v in bones.items()}
        by_index = {v['index']: k for k, v in bones.items()}
        self.children = {k: [] for k in bones}
        for k, v in bones.items():
            p = by_index.get(v['parent'])
            if p: self.children[p].append(k)
        self.used = sorted({b for w in W for b in w if b in bones})
        self.Widx = np.zeros((self.n, 8), int); self.Wval = np.zeros((self.n, 8))
        for i, w in enumerate(W):
            items = sorted([(b, x) for b, x in w.items() if b in bones], key=lambda x: -x[1])[:8]
            for k, (b, x) in enumerate(items): self.Widx[i, k] = self.used.index(b); self.Wval[i, k] = x
        self.Wval /= np.maximum(self.Wval.sum(axis=1, keepdims=True), 1e-12)
        rows, cols = [], []
        for t in TW:
            for a in range(3):
                for b in range(3):
                    if a != b: rows.append(t[a]); cols.append(t[b])
        self.Adj = sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(self.n, self.n)).tocsr(); self.Adj.data[:] = 1
        deg = np.asarray(self.Adj.sum(axis=1)).ravel(); self.Lop = sp.diags(1 / np.maximum(deg, 1)) @ self.Adj
        self.S0 = self.smooth(P); n0 = self.vnormals(self.S0)
        self.tan_nb = np.zeros(self.n, int)
        for i in range(self.n):
            nbs = self.Adj.indices[self.Adj.indptr[i]:self.Adj.indptr[i + 1]]
            if len(nbs) == 0: self.tan_nb[i] = i; continue
            e = self.S0[nbs] - self.S0[i]; e -= np.outer(e @ n0[i], n0[i]); self.tan_nb[i] = nbs[np.argmax(np.linalg.norm(e, axis=1))]
        self.delta = np.einsum('vji,vj->vi', self.frames(self.S0), P - self.S0)
        self.finger = np.array([any(f in d and 'metacarpal' not in d for f in ('thumb', 'index', 'middle', 'ring', 'pinky'))
                                for d in [max(w, key=w.get) if w else '' for w in W]])
        sides = []
        for w in W:
            s = [b[-1] for b, x in w.items() if x > .01 and len(b) > 2 and b[-2] == '_' and b[-1] in 'lr']
            sides.append(max(set(s), key=s.count) if s else 'c')
        self.side = np.array(sides)

    # ---------------------------------------------------------------- geometry helpers
    def smooth(self, X, iters=30, lam=.5):
        for _ in range(iters): X = (1 - lam) * X + lam * (self.Lop @ X)
        return X

    def vnormals(self, X):
        T = self.TW; f = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]) * self.sgn
        n = np.zeros_like(X)
        for k in range(3): np.add.at(n, T[:, k], f)
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)

    def frames(self, X):
        n = self.vnormals(X); e = X[self.tan_nb] - X; e -= np.einsum('ij,ij->i', e, n)[:, None] * n
        t = e / np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-12); return np.stack([t, np.cross(n, t), n], axis=2)

    def delta_mush(self, Xp):
        Sp = self.smooth(Xp); return Sp + np.einsum('vij,vj->vi', self.frames(Sp), self.delta)

    def inverted(self, X, faces_mask):
        T = self.TW; f = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]) * self.sgn
        vn = np.zeros_like(X)
        for k in range(3): np.add.at(vn, T[:, k], f)
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
        return np.nonzero((np.einsum('ij,ij->i', f, vn[T].mean(axis=1)) < 0) & faces_mask)[0]

    def fold_guard(self, Xp, corr, mask):
        zone_f = mask[self.TW].max(axis=1) > 0
        before = len(self.inverted(Xp, zone_f)); it = 0
        for it in range(60):
            Xc = Xp + corr; bad = self.inverted(Xc, zone_f)
            if not len(bad): break
            vs = set(self.TW[bad].ravel().tolist())
            for _ in range(2 + it // 20): vs |= {int(u) for v in list(vs) for u in self.Adj.indices[self.Adj.indptr[v]:self.Adj.indptr[v + 1]]}
            vs = np.array(sorted(vs)); avg = self.Lop @ Xc; corr[vs] += .5 * (avg[vs] - Xc[vs])
        return corr, dict(folds_before=int(before), folds_left=int(len(self.inverted(Xp + corr, zone_f))))

    # ---------------------------------------------------------------- skinning
    def descendants(self, b):
        out = [b]
        for c in self.children.get(b, []): out += self.descendants(c)
        return out

    def key_matrices(self, rotations):
        Rm = np.tile(np.eye(3), (len(self.used), 1, 1)); Tv = np.zeros((len(self.used), 3))
        for b, (rot, pivot) in rotations.items():
            M = rot.as_matrix()
            for d in self.descendants(b):
                if d in self.used:
                    k = self.used.index(d); Rm[k] = M @ Rm[k]; Tv[k] = M @ Tv[k] + pivot - M @ pivot
        return Rm, Tv

    def pose_matrices(self, pose):
        """pose {bone: (t (3,), q (4,))} component space -> skin matrices against this mesh's reference."""
        Rm = np.tile(np.eye(3), (len(self.used), 1, 1)); Tv = np.zeros((len(self.used), 3))
        for k, b in enumerate(self.used):
            if b not in pose: continue
            t, q = pose[b]; Mp = Rot.from_quat(q).as_matrix(); Mr = self.ref_q[b].as_matrix()
            Rm[k] = Mp @ Mr.T; Tv[k] = np.asarray(t) - Rm[k] @ self.ref_t[b]
        return Rm, Tv

    def lbs(self, X, Rm, Tv):
        A = np.einsum('vk,vkij->vij', self.Wval, Rm[self.Widx]); t = np.einsum('vk,vki->vi', self.Wval, Tv[self.Widx])
        return np.einsum('vij,vj->vi', A, X) + t, A

    # ---------------------------------------------------------------- correctives
    def side_frame(self, s):
        rt = self.ref_t
        S_, E_, W_ = rt['upperarm_' + s], rt['lowerarm_' + s], rt['hand_' + s]
        up = (E_ - S_) / np.linalg.norm(E_ - S_); fd = (W_ - E_) / np.linalg.norm(W_ - E_)
        hinge = np.cross(up, fd); hinge /= np.linalg.norm(hinge)
        f0 = rt['middle_01_' + s] - W_; f0 /= np.linalg.norm(f0)
        r0 = rt['index_metacarpal_' + s] - rt['pinky_metacarpal_' + s]; r0 -= (r0 @ f0) * f0; r0 /= np.linalg.norm(r0)
        return dict(S=S_, E=E_, W=W_, up=up, fd=fd, hinge=hinge, f0=f0, r0=r0, z0=np.cross(f0, r0),
                    rest=float(np.degrees(np.arccos(np.clip(up @ fd, -1, 1)))))

    def joint_keys(self, log=print):
        shapes, meta = {}, {}
        P = self.P
        for s in ('l', 'r'):
            need = ['upperarm_' + s, 'lowerarm_' + s, 'hand_' + s, 'middle_01_' + s, 'index_metacarpal_' + s, 'pinky_metacarpal_' + s]
            on = self.side == s
            if not all(b in self.bones for b in need) or on.sum() < 50: continue
            F = self.side_frame(s); E_, W_ = F['E'], F['W']
            d_e = np.linalg.norm(P - E_, axis=1); d_w = np.linalg.norm(P - W_, axis=1)
            mask_e = on * (1 - smoothstep(7.5, 11.5, d_e)) * (self.vreg <= 1)
            mask_w = on * (1 - smoothstep(4.5, 7.0, d_w)) * (~self.finger)
            outer = F['up'] - F['fd']; outer -= (outer @ F['hinge']) * F['hinge']; outer /= np.linalg.norm(outer)
            keys = []
            for ang in (20.0, 75.0, 110.0, 135.0):
                if ang < F['rest'] - 1 and ang != 20.0: continue
                if ang == 20.0 and F['rest'] < 25: continue
                cands = [Rot.from_rotvec(sg * F['hinge'] * np.radians(ang - F['rest'])) for sg in (1, -1)]
                rot = min(cands, key=lambda r: abs(np.degrees(np.arccos(np.clip(F['up'] @ r.apply(F['fd']), -1, 1))) - ang))
                keys.append(('JC_ElbowFlex%d_%s' % (ang, s.upper()), {'lowerarm_' + s: (rot, E_)}, mask_e, ang))
            for name, axis, deg in (('JC_WristFlexA_%s', F['r0'], 40.0), ('JC_WristFlexB_%s', F['r0'], -40.0),
                                    ('JC_WristRadial_%s', F['z0'], 20.0), ('JC_WristUlnar_%s', F['z0'], -35.0)):
                keys.append((name % s.upper(), {'hand_' + s: (Rot.from_rotvec(axis * np.radians(deg)), W_)}, mask_w, deg))
            for name, rots, mask, val in keys:
                if mask.max() <= 0: continue
                Rm, Tv = self.key_matrices(rots); Xp, A = self.lbs(P, Rm, Tv)
                if name.startswith('JC_ElbowFlex20'): corr = np.zeros_like(P)
                elif name.startswith('JC_Elbow'):
                    corr = (self.delta_mush(Xp) - Xp) * mask[:, None]
                    o_rot = rots['lowerarm_' + s][0]; bis = outer + o_rot.apply(outer); bis /= np.linalg.norm(bis)
                    outer_w = smoothstep(-.35, .25, self.vnormals(Xp) @ bis); corr *= outer_w[:, None]
                    crease = (1 - outer_w) * mask * (1 - smoothstep(4.5, 7.5, np.linalg.norm(Xp - E_, axis=1)))
                    relax = self.smooth(Xp, 16) - Xp; rm = np.linalg.norm(relax, axis=1); relax *= np.minimum(1, .5 / np.maximum(rm, 1e-9))[:, None]
                    corr += relax * crease[:, None]
                else:
                    corr = (self.delta_mush(Xp) - Xp) * mask[:, None]
                    inner = rots['hand_' + s][0].apply(F['f0']) - F['f0']; inner /= np.linalg.norm(inner)
                    comp = smoothstep(.1, .55, self.vnormals(Xp) @ inner) * mask * (1 - smoothstep(3.5, 6.0, np.linalg.norm(Xp - W_, axis=1)))
                    corr *= (1 - comp)[:, None]
                    relax = self.smooth(Xp, 14) - Xp; rm = np.linalg.norm(relax, axis=1); relax *= np.minimum(1, .3 / np.maximum(rm, 1e-9))[:, None]
                    corr += relax * comp[:, None]
                for _ in range(12): corr = .5 * corr + .5 * (self.Lop @ corr) * (mask > 0)[:, None]
                corr *= (mask > 0)[:, None]
                if name.startswith('JC_Elbow') and val > F['rest']:
                    k = (val - F['rest']) / (135 - F['rest']); o_rot = rots['lowerarm_' + s][0]
                    ol = o_rot.apply(outer) * .5 + outer * .5; ol /= np.linalg.norm(ol)
                    g = np.exp(-(np.linalg.norm(Xp - (E_ + ol * 3.2), axis=1) / 1.6) ** 2) * mask
                    nrm = self.frames(Xp)[:, :, 2]; corr += nrm * (0.18 * k * g * np.clip(nrm @ ol, 0, 1))[:, None]
                corr, guard = self.fold_guard(Xp, corr, mask)
                rest = np.linalg.solve(A, corr[:, :, None])[:, :, 0]
                mag = np.linalg.norm(rest, axis=1); rest *= np.minimum(1, 1.2 / np.maximum(mag, 1e-9))[:, None]; rest[mag < .004] = 0
                if not (np.linalg.norm(rest, axis=1) > .012).any(): continue
                shapes[name] = rest
                meta[name] = dict(side=s, value=float(val), rest_elbow_deg=F['rest'], vertices=int((np.linalg.norm(rest, axis=1) > .012).sum()),
                                  max_rest_cm=float(np.linalg.norm(rest, axis=1).max()), **guard)
                log(name, json.dumps(meta[name]))
        return shapes, meta


class Driver:
    """Mirror of UFPSArmJointCorrectiveComponent, on the pose-source (leader) reference skeleton."""
    SIGMA = 12.0

    def __init__(self, leader_bones, grip_names=()):
        self.rt = {k: np.array(v['t']) for k, v in leader_bones.items()}
        self.rq = {k: Rot.from_quat(v['q']) for k, v in leader_bones.items()}
        self.sides = {}
        for s in ('l', 'r'):
            need = ['upperarm_' + s, 'lowerarm_' + s, 'hand_' + s, 'lowerarm_twist_01_' + s, 'middle_01_' + s, 'index_metacarpal_' + s, 'pinky_metacarpal_' + s]
            if not all(b in self.rt for b in need): continue
            rt = self.rt; f0 = rt['middle_01_' + s] - rt['hand_' + s]; f0 /= np.linalg.norm(f0)
            r0 = rt['index_metacarpal_' + s] - rt['pinky_metacarpal_' + s]; r0 -= (r0 @ f0) * f0; r0 /= np.linalg.norm(r0)
            tq = self.rq['lowerarm_twist_01_' + s].inv()
            U = rt['lowerarm_' + s] - rt['upperarm_' + s]; Fw = rt['hand_' + s] - rt['lowerarm_' + s]
            mcp = {}
            for f in ('index', 'middle', 'ring', 'pinky'):
                a = rt[f'{f}_01_{s}'] - rt[f'{f}_metacarpal_{s}']; b = rt[f'{f}_02_{s}'] - rt[f'{f}_01_{s}']
                mcp[f] = float(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
            qL = self.rq['lowerarm_' + s]
            self.sides[s] = dict(F0=tq.apply(f0), R0=tq.apply(r0), Z0=tq.apply(np.cross(f0, r0)),
                                 rest=float(np.degrees(np.arccos(np.clip(U @ Fw / np.linalg.norm(U) / np.linalg.norm(Fw), -1, 1)))), mcp=mcp,
                                 rel_hand=qL.inv() * self.rq['hand_' + s], axis_l=qL.inv().apply(Fw / np.linalg.norm(Fw)))
        self.grips = {s: [(n, [float(x) for x in n.split('_')[3:7]]) for n in grip_names if n.startswith('JC_Grip_%s_' % s.upper())] for s in 'lr'}
        self.poses = {s: [(n, [pose_value(x) for x in n.split('_')[3:11]]) for n in grip_names if n.startswith('JC_Pose_%s_' % s.upper())] for s in 'lr'}

    def signature(self, pose, s):
        """elbow, wrist flexion, deviation, hand roll, 4 MCP extras (mirror of the C++ driver)."""
        D = self.sides[s]; g = lambda n: np.asarray(pose[n + '_' + s][0])
        U = g('lowerarm') - g('upperarm'); Fw = g('hand') - g('lowerarm')
        e = float(np.degrees(np.arccos(np.clip(U @ Fw / np.linalg.norm(U) / np.linalg.norm(Fw), -1, 1))))
        q = Rot.from_quat(pose['lowerarm_twist_01_' + s][1])
        h = q.inv().apply(g('middle_01') - g('hand')); h /= np.linalg.norm(h)
        along = h @ D['F0']; flex = float(np.degrees(np.arctan2(-(h @ D['Z0']), along))); dev = float(np.degrees(np.arctan2(h @ D['R0'], along)))
        rel = (Rot.from_quat(pose['lowerarm_' + s][1]).inv() * Rot.from_quat(pose['hand_' + s][1]) * D['rel_hand'].inv()).as_quat()
        if rel[3] < 0: rel = -rel
        roll = float(np.degrees(2 * np.arctan2(rel[:3] @ D['axis_l'], rel[3])))
        return [e, flex, dev, roll] + self.mcp_extra(pose, s)

    def mcp_extra(self, pose, s):
        out = []
        for f in ('index', 'middle', 'ring', 'pinky'):
            a = np.asarray(pose[f'{f}_01_{s}'][0]) - pose[f'{f}_metacarpal_{s}'][0]; b = np.asarray(pose[f'{f}_02_{s}'][0]) - pose[f'{f}_01_{s}'][0]
            out.append(max(0.0, float(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1)))) - self.sides[s]['mcp'][f]))
        return out

    def weights(self, pose):
        w = {}
        for s, D in self.sides.items():
            S = s.upper(); g = lambda n: np.asarray(pose[n + '_' + s][0])
            U = g('lowerarm') - g('upperarm'); Fw = g('hand') - g('lowerarm')
            e = float(np.degrees(np.arccos(np.clip(U @ Fw / np.linalg.norm(U) / np.linalg.norm(Fw), -1, 1))))
            w['JC_ElbowFlex20_' + S] = float(np.clip((D['rest'] - e) / (D['rest'] - 20), 0, 1)) if D['rest'] > 21 else 0.0
            w['JC_ElbowFlex75_' + S] = tent(e, D['rest'], 75, 110); w['JC_ElbowFlex110_' + S] = tent(e, 75, 110, 135)
            w['JC_ElbowFlex135_' + S] = float(np.clip((e - 110) / 25, 0, 1))
            q = Rot.from_quat(pose['lowerarm_twist_01_' + s][1])
            h = q.inv().apply(g('middle_01') - g('hand')); h /= np.linalg.norm(h)
            along = h @ D['F0']; flex = float(np.degrees(np.arctan2(-(h @ D['Z0']), along))); dev = float(np.degrees(np.arctan2(h @ D['R0'], along)))
            sane = 1 - smoothstep(95, 135, max(abs(flex), abs(dev)))
            w['JC_WristFlexA_' + S] = float(np.clip(flex / 40, 0, 1)) * sane; w['JC_WristFlexB_' + S] = float(np.clip(-flex / 40, 0, 1)) * sane
            w['JC_WristRadial_' + S] = float(np.clip(dev / 20, 0, 1)) * sane; w['JC_WristUlnar_' + S] = float(np.clip(-dev / 35, 0, 1)) * sane
            if self.grips[s]:
                ex = self.mcp_extra(pose, s)
                for n, e_ in self.grips[s]:
                    w[n] = float(np.exp(-.5 * sum(((x - y) / self.SIGMA) ** 2 for x, y in zip(ex, e_))))
            if self.poses[s]:
                sig = self.signature(pose, s)
                for n, c_ in self.poses[s]: w[n] = pose_weight(sig, c_)
        return w


POSE_SIGMA = np.array([12., 12., 10., 20., 15., 15., 15., 15.])


def pose_value(tok): return -float(tok[1:]) if tok.startswith('m') else float(tok)


def pose_name(s, sig):
    return 'JC_Pose_%s_%s' % (s.upper(), '_'.join(('m%d' % -round(x)) if round(x) < 0 else '%d' % round(x) for x in sig))


def pose_distance(a, b):
    d = np.array(a, float) - np.array(b, float); d[3] = (d[3] + 180) % 360 - 180
    return float(np.sqrt(np.sum((d / POSE_SIGMA) ** 2)))


def pose_weight(a, b): return float(np.exp(-.5 * pose_distance(a, b) ** 2))


def frame_pose(clip, bones, fi):
    return {b: (np.array(f[:3]), np.array(f[3:])) for b, f in zip(bones, clip['frames'][fi])}


def grip_examples(rig, driver, shapes, held, clipdata, log=print, existing=()):
    """One held-grip example per held clip (middle frame), whole-arm fold untangle on top of the active keys."""
    out, meta = {}, {}
    taken = list(existing)
    bones = clipdata['bones']
    for path in held:
        c = clipdata['clips'].get(path)
        if not c or 'frames' not in c: continue
        pose = frame_pose(c, bones, len(c['frames']) // 2)
        for s in ('l', 'r'):
            if s not in driver.sides or (rig.side == s).sum() < 50: continue
            ex = [int(round(x)) for x in driver.mcp_extra(pose, s)]
            name = 'JC_Grip_%s_%s' % (s.upper(), '_'.join(str(x) for x in ex))
            if name in out or any(np.linalg.norm(np.array(ex) - np.array([float(v) for v in n.split('_')[3:7]])) < 8
                                  for n in list(out) + taken if n.startswith('JC_Grip_%s_' % s.upper())):
                continue
            w = driver.weights(pose); d = np.zeros_like(rig.P)
            for n_, x in w.items():
                if x > 1e-4 and n_ in shapes: d += shapes[n_] * x
            Rm, Tv = rig.pose_matrices(pose); Xp, A = rig.lbs(rig.P + d, Rm, Tv)
            mask = (rig.side == s).astype(float)
            corr, g1 = rig.fold_guard(Xp, np.zeros_like(rig.P), mask)
            for _ in range(4): corr = .5 * corr + .5 * (rig.Lop @ corr) * (mask > 0)[:, None]
            corr, g2 = rig.fold_guard(Xp, corr, mask)
            rest = np.linalg.solve(A, corr[:, :, None])[:, :, 0]
            mag = np.linalg.norm(rest, axis=1); rest *= np.minimum(1, .5 / np.maximum(mag, 1e-9))[:, None]; rest[mag < .004] = 0
            if not (np.linalg.norm(rest, axis=1) > .012).any(): continue
            out[name] = rest; meta[name] = dict(side=s, clip=path.split('/')[-1], folds_before=g1['folds_before'], folds_left=g2['folds_left'],
                                                vertices=int((np.linalg.norm(rest, axis=1) > .012).sum()))
            log(name, json.dumps(meta[name]))
    return out, meta


def validate(rig, driver, shapes, clipdata, every=3):
    """Pinholes (faces against vertex normals) per clip, plain skinning vs with all correctives."""
    report = {}; bones = clipdata['bones']; allf = np.ones(len(rig.TW), bool)
    for path, c in clipdata['clips'].items():
        if 'frames' not in c: continue
        worst = [0, 0]
        for fi in range(0, len(c['frames']), every):
            pose = frame_pose(c, bones, fi); Rm, Tv = rig.pose_matrices(pose)
            Xb, _ = rig.lbs(rig.P, Rm, Tv)
            w = driver.weights(pose); d = np.zeros_like(rig.P)
            for n_, x in w.items():
                if x > 1e-4 and n_ in shapes: d += shapes[n_] * x
            Xc, _ = rig.lbs(rig.P + d, Rm, Tv)
            worst = [max(worst[0], len(rig.inverted(Xb, allf))), max(worst[1], len(rig.inverted(Xc, allf)))]
        report[path.split('/')[-1]] = dict(plain=worst[0], corrected=worst[1])
    return report
