"""Offline LMG201 reload diagnostics (read only).

Everything is UE component space, centimetres, the same frame that the saved
UE animations evaluate in (checked against ChainmailReloadFit20260929 compressed
poses to < 0.01 cm).  Linear blend skinning with the saved reference skeleton.
"""
import json, gzip
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

SA = Path('D:/FPS3D/FPSGAME/SourceAssets')
L201 = SA / 'LMG20120260927'
HERE = L201 / 'ClothReload44'
_inp = json.loads((L201 / 'ClothFeed33' / 'inputs.json').read_text())['meshes']['201']
NAMES = _inp['names']
BI = {n: i for i, n in enumerate(NAMES)}
PARENT = np.array(_inp['parents'])


def mat(v):
    m = np.eye(4)
    m[:3, :3] = Rot.from_quat(v[3:7]).as_matrix() @ np.diag(v[7:10])
    m[:3, 3] = v[:3]
    return m


REST = np.array([mat(v) for v in _inp['rest']])
REST_INV = np.linalg.inv(REST)
SIDE_BONES = {s: [n for n in NAMES if n.endswith('_' + s) and any(n.startswith(k) for k in (
    'clavicle', 'upperarm', 'lowerarm', 'hand', 'index', 'middle', 'ring', 'pinky', 'thumb'))] for s in 'lr'}

# Runtime constants (FPSGAMECharacter.cpp / .h, LMG201WeaponAssets.h)
HIP = np.array([9.0, 9.0, -11.0])      # M4Hip (0,7,-7) + LMG (9,2,-4)
ACTION = np.array([10.0, 0.0, -5.0])   # M4ActionViewmodelLocation
VFOV = 75.0
ASPECT = 16 / 9


def load_tracks(path):
    with gzip.open(path, 'rt', encoding='utf8') as f:
        t = json.load(f)
    return {n: np.asarray(v, float) for n, v in t.items()}


def local_mats(rows):
    """rows (F,10) -> (F,4,4)"""
    F = len(rows)
    m = np.zeros((F, 4, 4))
    m[:, :3, :3] = Rot.from_quat(rows[:, 3:7]).as_matrix() * rows[:, None, 7:10]
    m[:, :3, 3] = rows[:, :3]
    m[:, 3, 3] = 1
    return m


def worlds(tracks, frames=None):
    """(F,B,4,4) component-space bone matrices."""
    F = len(next(iter(tracks.values())))
    frames = np.arange(F) if frames is None else np.asarray(frames)
    W = np.zeros((len(frames), len(NAMES), 4, 4))
    for i, n in enumerate(NAMES):
        loc = local_mats(tracks[n][frames]) if n in tracks else np.broadcast_to(
            np.linalg.inv(REST[PARENT[i]]) @ REST[i] if PARENT[i] >= 0 else REST[i], (len(frames), 4, 4))
        W[:, i] = W[:, PARENT[i]] @ loc if PARENT[i] >= 0 else loc
    return W


class Skin:
    """LBS mesh with up to K influences."""

    def __init__(self, pos, weights, tris=None, mats=None, K=8, name=''):
        self.name = name
        self.p = np.asarray(pos, float)
        V = len(self.p)
        self.idx = np.zeros((V, K), np.int32)
        self.w = np.zeros((V, K))
        if isinstance(weights, tuple):  # (bone_idx, bone_w) already in NAMES order
            bi, bw = weights
            k = min(K, bi.shape[1])
            self.idx[:, :k], self.w[:, :k] = bi[:, :k], bw[:, :k]
        else:
            for v, d in enumerate(weights):
                items = sorted(((w, BI[n]) for n, w in d.items() if n in BI and w > 0), reverse=True)[:K]
                s = sum(w for w, _ in items) or 1
                for k, (w, b) in enumerate(items):
                    self.idx[v, k], self.w[v, k] = b, w / s
        self.tris = None if tris is None else np.asarray(tris, np.int64)
        self.mats = None if mats is None else np.asarray(mats)
        self.dom = self.idx[:, 0]

    def pose(self, W, sel=None):
        S = W @ REST_INV  # (B,4,4)
        idx, w, p = (self.idx, self.w, self.p) if sel is None else (self.idx[sel], self.w[sel], self.p[sel])
        M = (S[idx] * w[..., None, None]).sum(1)  # (V,4,4)
        return np.einsum('vij,vj->vi', M[:, :3, :3], p) + M[:, :3, 3]


def load_json_mesh(path, name=''):
    d = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    tris = d.get('triangles')
    mats = d.get('triangle_materials', d.get('materials'))
    return Skin(d['positions'], d['weights'], tris, mats, name=name)


def vertex_normals(p, tris):
    n = np.zeros_like(p)
    fn = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    for k in range(3):
        np.add.at(n, tris[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def edges_of(tris):
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    return np.unique(np.sort(e, axis=1), axis=0)


# ---------------------------------------------------------------- inside test
import numba


@numba.njit(parallel=True, fastmath=True, cache=True)
def winding_number(P, V, F):
    """Generalised winding number of points P w.r.t. triangle soup (V,F)."""
    out = np.zeros(P.shape[0])
    for i in numba.prange(P.shape[0]):
        s = 0.0
        px, py, pz = P[i, 0], P[i, 1], P[i, 2]
        for f in range(F.shape[0]):
            ax, ay, az = V[F[f, 0], 0] - px, V[F[f, 0], 1] - py, V[F[f, 0], 2] - pz
            bx, by, bz = V[F[f, 1], 0] - px, V[F[f, 1], 1] - py, V[F[f, 1], 2] - pz
            cx, cy, cz = V[F[f, 2], 0] - px, V[F[f, 2], 1] - py, V[F[f, 2], 2] - pz
            la = np.sqrt(ax * ax + ay * ay + az * az)
            lb = np.sqrt(bx * bx + by * by + bz * bz)
            lc = np.sqrt(cx * cx + cy * cy + cz * cz)
            det = ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
            div = la * lb * lc + (ax * bx + ay * by + az * bz) * lc + (bx * cx + by * cy + bz * cz) * la \
                + (cx * ax + cy * ay + cz * az) * lb
            s += 2.0 * np.arctan2(det, div)
        out[i] = s / (4.0 * np.pi)
    return out


# ---------------------------------------------------------------- gun body
class Body:
    """Saved SurfaceReform42 assembly split into rigid parts by dominant bone."""

    ARM_MATS = (0, 1, 2)

    def __init__(self, npz=None):
        npz = npz or next(p for p in (HERE / 'Diagnostics' / 'body_current.npz', HERE / 'Diagnostics' / 'body_s42.npz') if p.exists())
        z = np.load(npz)
        names = list(z['bones'])
        remap = np.array([BI.get(n, 0) for n in names])
        self.pos = z['pos'].astype(float)
        self.tris = z['tris']
        self.tri_mat = z['tri_mat']
        self.mats = list(z['mats'])
        self.bi = remap[z['bone_idx']]
        self.bw = z['bone_w']
        self.normals = vertex_normals(self.pos, self.tris)
        used = np.zeros(len(self.pos), bool)
        keep = ~np.isin(self.tri_mat, self.ARM_MATS)
        used[np.unique(self.tris[keep])] = True
        self.used = used
        dom = self.bi[:, 0]
        self.parts = {}
        for b in np.unique(dom[used]):
            sel = np.where(used & (dom == b))[0]
            self.parts[NAMES[b]] = sel
        # material id per vertex (first triangle wins) for visibility states
        vm = np.full(len(self.pos), -1)
        vm[self.tris[:, 0]] = self.tri_mat
        vm[self.tris[:, 1]] = self.tri_mat
        vm[self.tris[:, 2]] = self.tri_mat
        self.vmat = vm
        self._trees = {}

    def group(self, part):
        n = part
        if n.startswith('New_LMG201_Belt') or n.startswith('New_LMG201_Box'):
            return 'new_feed'
        if n.startswith('LMG201_Belt') or n.startswith('LMG201_Box') or n == 'LMG201_EmptyLink':
            return 'old_feed'
        if n == 'WPN_SOCKET_Magazine':
            return 'magazine'
        if n == 'LMG201_Cover':
            return 'cover'
        return 'gun'

    def _samples(self, part):
        """Triangle samples (barycentric) of one part; big faces subdivided."""
        if part in self._trees:
            return self._trees[part]
        sel = self.parts[part]
        inpart = np.zeros(len(self.pos), bool)
        inpart[sel] = True
        tri = self.tris[inpart[self.tris].all(1) & ~np.isin(self.tri_mat, self.ARM_MATS)]
        a, b, c = (self.pos[tri[:, k]] for k in range(3))
        area = .5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        n = np.clip(np.ceil(area / .01), 1, 64).astype(int)  # ~1 mm spacing
        rows, bary = [], []
        rng = np.random.default_rng(7)
        for k in np.unique(n):
            ids = np.where(n == k)[0]
            if k == 1:
                bb = np.tile([1 / 3, 1 / 3, 1 / 3], (len(ids), 1))[:, None]
            else:
                u = rng.random((len(ids), k, 2))
                flip = u.sum(-1) > 1
                u[flip] = 1 - u[flip]
                bb = np.concatenate([1 - u.sum(-1, keepdims=True), u], -1)
            rows.append(np.repeat(ids, bb.shape[1]))
            bary.append(bb.reshape(-1, 3))
        rows, bary = np.concatenate(rows), np.concatenate(bary)
        rigid = bool(np.all(self.bw[sel, 0] > .999))
        bone = BI[part]
        data = dict(tri=tri, rows=rows, bary=bary, rigid=rigid, bone=bone)
        if rigid:
            P = (bary[:, :, None] * np.stack([a[rows], b[rows], c[rows]], 1)).sum(1)
            fn = np.cross(b - a, c - a)
            fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
            loc = (REST_INV[bone][:3, :3] @ P.T).T + REST_INV[bone][:3, 3]
            nl = (REST_INV[bone][:3, :3] @ fn[rows].T).T
            nl /= np.linalg.norm(nl, axis=1, keepdims=True)
            data.update(tree=cKDTree(loc), loc=loc, nl=nl)
        else:
            vid = np.unique(tri)
            data.update(skin=Skin(self.pos[vid], (self.bi[vid], self.bw[vid])), vid=vid,
                        remap={v: i for i, v in enumerate(vid)})
            data['ltri'] = np.searchsorted(vid, tri)
        self._trees[part] = data
        return data

    def signed(self, pts, W, visible_groups, radius=3.0):
        """Signed distance (cm) to visible gun parts, positive outside.  The
        sign comes from the face normal of the nearest dense surface sample."""
        best = np.full(len(pts), np.inf)
        which = np.full(len(pts), '', object)
        for part in self.parts:
            if self.group(part) not in visible_groups:
                continue
            D = self._samples(part)
            if D['rigid']:
                A = W[D['bone']] @ REST_INV[D['bone']]
                Ainv = np.linalg.inv(A)
                q = (Ainv[:3, :3] @ pts.T).T + Ainv[:3, 3]
                sc = np.linalg.norm(A[:3, 0])
                d, j = D['tree'].query(q, distance_upper_bound=radius / sc)
                ok = np.isfinite(d)
                s = np.full(len(pts), np.inf)
                if ok.any():
                    if 'Vloc' not in D:
                        D['Vloc'] = (REST_INV[D['bone']][:3, :3] @ self.pos.T).T + REST_INV[D['bone']][:3, 3]
                    wn = winding_number(q[ok], D['Vloc'], D['tri'])
                    s[ok] = np.where(wn > .5, -d[ok], d[ok]) * sc
            else:
                vp = D['skin'].pose(W)
                lt = D['ltri']
                a, b, c = vp[lt[:, 0]], vp[lt[:, 1]], vp[lt[:, 2]]
                fn = np.cross(b - a, c - a)
                fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
                r = D['rows']
                P = (D['bary'][:, :, None] * np.stack([a[r], b[r], c[r]], 1)).sum(1)
                d, j = cKDTree(P).query(pts, distance_upper_bound=radius)
                ok = np.isfinite(d)
                s = np.full(len(pts), np.inf)
                if ok.any():
                    wn = winding_number(pts[ok], vp, lt)
                    s[ok] = np.where(wn > .5, -d[ok], d[ok])
            upd = np.abs(s) < np.abs(best)
            best[upd] = s[upd]
            which[upd] = part
        return best, which


def visible_groups(t, cloth=True, empty=False, reload=True):
    g = {'gun', 'cover'}
    if not cloth:
        g.add('magazine')
        return g
    old = (not reload) or t < 2.53
    new = reload and t >= 2.915
    if old:
        g.add('old_feed')
    if new:
        g.add('new_feed')
    return g


# ---------------------------------------------------------------- camera
def framing_alpha(t, duration=6.2, ret=5.45):
    a = 1 - np.exp(-16 * t)
    return np.minimum(a, np.clip((duration - t) / (duration - ret), 0, 1))


def camera(alpha):
    L = HIP + (ACTION - HIP) * alpha
    eye = np.array([-L[1], L[0], -L[2]])  # yaw 90 inverse
    fwd, right, up = np.array([0, -1., 0]), np.array([1., 0, 0]), np.array([0, 0, 1.])
    return eye, fwd, right, up


def view_metrics(pts, eye, fwd, right, up):
    v = pts - eye
    z = v @ fwd
    x = v @ right
    y = v @ up
    th = np.tan(np.radians(VFOV / 2))
    tw = th * ASPECT
    front = z > 1.0
    inside = front & (np.abs(x) < z * tw) & (np.abs(y) < z * th)
    dist = np.linalg.norm(v, axis=1)
    return inside, dist


# ---------------------------------------------------------------- arm checks
def swing_twist_angle(qrel, axis):
    """twist angle (deg) of rotation qrel (xyzw) about unit axis."""
    q = np.where(qrel[..., 3:4] < 0, -qrel, qrel)
    proj = (q[..., :3] * axis).sum(-1)
    return np.degrees(2 * np.arctan2(proj, q[..., 3]))


def arm_frames(W, side):
    b = lambda n: BI[n + '_' + side]
    return {k: W[:, b(k)] for k in ('clavicle', 'upperarm', 'lowerarm', 'hand', 'lowerarm_twist_01',
                                   'lowerarm_twist_02', 'upperarm_twist_01', 'upperarm_twist_02', 'middle_01')}


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def rot_only(m):
    r = m[..., :3, :3]
    return r / np.linalg.norm(r, axis=-2, keepdims=True)


def forearm_twist(W, side):
    """Axial rotation (deg) of hand and helpers relative to lowerarm, measured
    about the forearm axis and relative to the reference pose."""
    f = arm_frames(W, side)
    out = {}
    lo = rot_only(f['lowerarm'])
    lr = rot_only(REST[BI['lowerarm_' + side]][None])
    ax_l = unit(REST[BI['hand_' + side]][:3, 3] - REST[BI['lowerarm_' + side]][:3, 3])
    ax_local = (lr[0].T @ ax_l)
    for k in ('hand', 'lowerarm_twist_01', 'lowerarm_twist_02'):
        cr = rot_only(f[k])
        rr = rot_only(REST[BI[k + '_' + side]][None])
        rel = np.einsum('fji,fjk->fik', lo, cr) @ np.linalg.inv(np.einsum('fji,fjk->fik', lr, rr))
        q = Rot.from_matrix(rel).as_quat()
        out[k] = swing_twist_angle(q, ax_local)
    return out


def elbow_angle(W, side):
    s = W[:, BI['upperarm_' + side], :3, 3]
    e = W[:, BI['lowerarm_' + side], :3, 3]
    h = W[:, BI['hand_' + side], :3, 3]
    a, b = unit(s - e), unit(h - e)
    return np.degrees(np.arccos(np.clip((a * b).sum(-1), -1, 1)))


def bone_length_error(W):
    worst = 0.0
    for s in 'lr':
        for n in SIDE_BONES[s]:
            i = BI[n]
            p = PARENT[i]
            rl = np.linalg.norm(REST[i][:3, 3] - REST[p][:3, 3])
            pl = np.linalg.norm(W[:, i, :3, 3] - W[:, p, :3, 3], axis=-1)
            if n.startswith('clavicle'):
                continue  # root offset is reported separately
            worst = max(worst, float(np.abs(pl - rl).max()))
    return worst


def clavicle_shift(W, side):
    i, p = BI['clavicle_' + side], PARENT[BI['clavicle_' + side]]
    loc_rest = (np.linalg.inv(REST[p]) @ REST[i])[:3, 3]
    loc = (np.linalg.inv(W[:, p]) @ W[:, i])[:, :3, 3]
    scale = np.linalg.norm(W[:, p, :3, 0], axis=-1)[:, None]
    return np.linalg.norm((loc - loc_rest) * scale, axis=-1)


def rotation_between(a, b):
    """(F,3),(F,3) unit vectors -> (F,3,3) minimal rotation a->b."""
    v = np.cross(a, b)
    c = (a * b).sum(-1)
    s = np.linalg.norm(v, axis=-1)
    k = v / np.maximum(s, 1e-12)[..., None]
    ang = np.arctan2(s, c)
    return Rot.from_rotvec(k * ang[..., None]).as_matrix()


def elbow_cap_roll(W, side):
    """V43 recipe (RuneSword ChargedErgoV43/twist_distribution.forearm_roll):
    axial roll of lowerarm relative to the upper-arm transported frame (deg).
    The accepted 201 Skin07 idle keeps this near 0."""
    up, lo, ha = (BI[n + '_' + side] for n in ('upperarm', 'lowerarm', 'hand'))
    R = lambda i: rot_only(W[:, i])
    Rr = lambda i: rot_only(REST[i][None])[0]
    axis = unit(W[:, ha, :3, 3] - W[:, lo, :3, 3])
    rest_fore = unit(REST[ha][:3, 3] - REST[lo][:3, 3])
    up_d = R(up) @ Rr(up).T
    fo_d = R(lo) @ Rr(lo).T
    no_roll = rotation_between(np.einsum('fij,j->fi', up_d, rest_fore), axis) @ up_d
    rel = fo_d @ np.transpose(no_roll, (0, 2, 1))
    q = Rot.from_matrix(rel).as_quat()
    return swing_twist_angle(q, axis)


def seam_vertices(skin, side, a=('upperarm',), b=('lowerarm',), thr=.2):
    wa = np.zeros(len(skin.p))
    wb = np.zeros(len(skin.p))
    for k in range(skin.idx.shape[1]):
        n = np.array([NAMES[i] for i in skin.idx[:, k]])
        ok_side = np.char.endswith(n, '_' + side)
        wa += np.where(ok_side & np.any([np.char.startswith(n, x) for x in a], 0), skin.w[:, k], 0)
        wb += np.where(ok_side & np.any([np.char.startswith(n, x) for x in b], 0), skin.w[:, k], 0)
    return np.where((wa >= thr) & (wb >= thr))[0]


def blend_det(skin, W, sel):
    S = W @ REST_INV
    M = (S[skin.idx[sel]][..., :3, :3] * skin.w[sel][..., None, None]).sum(1)
    return np.linalg.det(M)


class RadiusProbe:
    """Cross-section collapse: vertex distance to the bone axis line relative
    to the reference pose.  Candy-wrapper twisting shows as ratio << 1."""

    def __init__(self, skin, side):
        self.side = side
        up = lambda n: REST[BI[n + '_' + side]][:3, 3]
        self.segs = {'upper': ('upperarm', 'lowerarm'), 'fore': ('lowerarm', 'hand')}
        self.sel = {}
        self.r0 = {}
        self.tt = {}
        for key, (a, b) in self.segs.items():
            A, B = up(a), up(b)
            d = B - A
            L = np.linalg.norm(d)
            t = ((skin.p - A) @ d) / (L * L)
            r = np.linalg.norm(skin.p - (A + t[:, None] * d), axis=1)
            mask = (t > .02) & (t < .98) & (r < 7) & (np.sign(skin.p[:, 0]) == (-1 if side == 'l' else 1))
            self.sel[key] = np.where(mask)[0]
            self.r0[key] = r[mask]
            self.tt[key] = t[mask]

    def ratios(self, skin_pts, W):
        out = {}
        for key, (a, b) in self.segs.items():
            A = W[BI[a + '_' + self.side]][:3, 3]
            B = W[BI[b + '_' + self.side]][:3, 3]
            d = B - A
            L = np.linalg.norm(d)
            p = skin_pts[self.sel[key]]
            t = ((p - A) @ d) / (L * L)
            r = np.linalg.norm(p - (A + t[:, None] * d), axis=1)
            rr = r / np.maximum(self.r0[key], .3)
            # near-joint bands: elbow = upper t>.8 + fore t<.2 ; wrist = fore t>.8
            out[key] = rr
        return out
