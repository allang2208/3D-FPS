"""Natural-realistic skin fields for the M4 V9 arms, rasterised into the new UV0 (4096).

Everything is generated from the V9 rest surface (cm) and the native bones, so the left/right arms and the
old hand/forearm split read as one continuous skin. Outputs (Work/):
  height16.png + height.json   relief for the Blender normal bake (cm, 16 bit)
  T_M4SkinV9_Colour.png         linear albedo encoded sRGB
  T_M4SkinV9_Masks.png          R ambient occlusion, G roughness, B cavity, A scatter amount
No human scan is used; the accepted atlas only contributes its nail / palm / palm-crease masks.
"""
import json, time
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from m4data import M4, R

RES = 4096; t0 = time.time()
OUT = R / 'Work'
m = M4(); wv = m.weld
P = np.load(OUT / 'geometry.npz')['welded']; X = P[wv]
UVN = np.load(OUT / 'uv_new.npy'); NRM = np.load(OUT / 'normals.npy')
J = m.joint; geo_rep = json.loads((OUT / 'geometry_report.json').read_text())['anatomy']['features']


def log(*a): print('[%.0fs]' % (time.time() - t0), *a, flush=True)


# ---------------------------------------------------------------- rasterise
tri = np.full((RES, RES), -1, np.int32); bary = np.zeros((RES, RES, 2), np.float32)
for t in range(len(m.T)):
    p = UVN[t] * RES; lo = np.clip(np.floor(p.min(0)).astype(int), 0, RES - 1); hi = np.clip(np.ceil(p.max(0)).astype(int), 0, RES)
    if (hi - lo).min() <= 0: continue
    xs, ys = np.meshgrid(np.arange(lo[0], hi[0]) + .5, np.arange(lo[1], hi[1]) + .5)
    A, B, C = p; v0 = B - A; v1 = C - A; den = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(den) < 1e-14: continue
    px = xs - A[0]; py = ys - A[1]
    w1 = (px * v1[1] - v1[0] * py) / den; w2 = (v0[0] * py - px * v0[1]) / den
    ins = (w1 >= -1e-4) & (w2 >= -1e-4) & (w1 + w2 <= 1 + 1e-4)
    yy = ys[ins].astype(int); xx = xs[ins].astype(int)
    tri[yy, xx] = t; bary[yy, xx, 0] = w1[ins]; bary[yy, xx, 1] = w2[ins]
cov = tri >= 0; iy, ix = np.nonzero(cov); T = tri[iy, ix]; b1 = bary[iy, ix, 0]; b2 = bary[iy, ix, 1]; b0 = 1 - b1 - b2
del bary
log('raster texels', len(T))


def interp(attr):                                       # attr: (tris, 3, k)
    return attr[T, 0] * b0[:, None] + attr[T, 1] * b1[:, None] + attr[T, 2] * b2[:, None]


pos = interp(X[m.T]).astype(np.float32)
nrm = interp(NRM); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True); nrm = nrm.astype(np.float32)
olduv = interp(m.UV)
region = m.region[T]
atlas = np.asarray(Image.open(P_ := (R.parent / 'ModularOutfit20260924/OriginalShapeBareM4/WristContourV4/T_M4OriginalShape_SkinSurface.png')).convert('RGBA'), np.float32) / 255
def atlas_sample(img, uv):
    h, w = img.shape[:2]; x = np.clip(uv[:, 0] * w - .5, 0, w - 1.001); y = np.clip(uv[:, 1] * h - .5, 0, h - 1.001)
    x0 = x.astype(int); y0 = y.astype(int); fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
mk = atlas_sample(atlas, olduv); mk[region != 2] = 0
nail, crease_atlas, palm_mask = mk[:, 0], mk[:, 2], mk[:, 3]
del atlas
left = pos[:, 0] < 0
log('attributes')


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def hash3(c):
    c = c.astype(np.int64)
    h = (c[..., 0] * 73856093) ^ (c[..., 1] * 19349663) ^ (c[..., 2] * 83492791)
    h = (h ^ (h >> 13)) * 1274126177; h = h ^ (h >> 16)
    return ((h[..., None] >> np.array([0, 10, 20])) & 1023).astype(np.float32) / 1023.0


def value_noise(p, scale, seed=0):
    q = p / scale + seed * 17.13; i = np.floor(q); f = q - i; f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * hash3(i + np.array([dx, dy, dz]))[:, 0]
    return out - .5


def voronoi(p, cell, chunk=1_000_000):
    F1 = np.empty(len(p), np.float32); F2 = np.empty(len(p), np.float32); ID = np.empty(len(p), np.float32)
    for s in range(0, len(p), chunk):
        q = p[s:s + chunk] / cell; base = np.floor(q)
        f1 = np.full(len(q), 9.0, np.float32); f2 = np.full(len(q), 9.0, np.float32); idv = np.zeros(len(q), np.float32)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    c = base + np.array([dx, dy, dz]); h = hash3(c)
                    d = np.linalg.norm(c + h - q, axis=1).astype(np.float32)
                    closer = d < f1
                    f2 = np.where(closer, f1, np.minimum(f2, d)); idv = np.where(closer, h[:, 0] * .5 + h[:, 1] * .5, idv); f1 = np.minimum(f1, d)
        F1[s:s + chunk] = f1 * cell; F2[s:s + chunk] = f2 * cell; ID[s:s + chunk] = idv
    return F1, F2, ID


# ---------------------------------------------------------------- anatomical frames per texel
def unit(v): return v / np.linalg.norm(v)


fr = {}
for s in ('l', 'r'):
    S_, E_, W_ = J('upperarm_' + s), J('lowerarm_' + s), J('hand_' + s)
    up = unit(E_ - S_); fd = unit(W_ - E_); Lf = np.linalg.norm(W_ - E_)
    dorsal = np.array(geo_rep['frame_' + s]['dorsal']); medial = np.array(geo_rep['frame_' + s]['medial'])
    f0 = unit(J('middle_01_' + s) - W_); r0 = J('index_metacarpal_' + s) - J('pinky_metacarpal_' + s); r0 = unit(r0 - (r0 @ f0) * f0)
    dh = dorsal - (dorsal @ f0) * f0 - (dorsal @ r0) * r0; dh = unit(dh)
    fingers = {}
    for f in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        j1, j2, j3 = J(f'{f}_01_{s}'), J(f'{f}_02_{s}'), J(f'{f}_03_{s}')
        tip = j3 + (j3 - j2) * (.95 if f != 'thumb' else 1.05)
        fingers[f] = [j1, j2, j3, tip]
    # forearm rotating frame: dorsal at the wrist, unwinding toward the elbow
    dw = dorsal - (dorsal @ fd) * fd; dw = unit(dw)
    me = medial - (medial @ fd) * fd; me = unit(me)
    fr[s] = dict(S=S_, E=E_, W=W_, up=up, fd=fd, Lf=Lf, dorsal=dh, f0=f0, r0=r0, fingers=fingers, dw=dw, me=me)

H = np.zeros(len(T), np.float32)                     # relief, cm (+ = raised)
crease_d = np.zeros(len(T), np.float32)              # fine groove depth record (for colour / cavity)
red = np.zeros(len(T), np.float32); vein = np.zeros(len(T), np.float32)
palmar = np.zeros(len(T), np.float32); inner_arm = np.zeros(len(T), np.float32)
seg_t = np.zeros(len(T), np.float32); on_distal = np.zeros(len(T), bool)
rough_add = np.zeros(len(T), np.float32)
w_hand_all = np.zeros(len(T), np.float32)           # smooth hand weight: no feature switches on the old split


def segdist(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1); q = a + np.outer(t, ab)
    return np.linalg.norm(p - q, axis=1), t


def lines(u, centres, width, depth):
    out = 0
    for c in centres: out = out + np.exp(-((u - c) / width) ** 2)
    return -depth * out


def polyline_dist(x, y, pts):
    best = np.full(len(x), 99.0, np.float32)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / L2, 0, 1)
        best = np.minimum(best, np.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return best


for s in ('l', 'r'):
    F = fr[s]; on = (left if s == 'l' else ~left)
    k = np.nonzero(on)[0]; p = pos[k]; n = nrm[k]; reg = region[k]
    # ---- hand & fingers
    hand = reg == 2
    x_h = (p - F['W']) @ F['f0']; y_h = (p - F['W']) @ F['r0']
    w_hand = smoothstep(-3.0, -.3, x_h) * (np.linalg.norm(p - F['W'], axis=1) < 16); w_hand_all[k] = w_hand
    pal = smoothstep(-.05, -.55, n @ F['dorsal']) * w_hand
    palmar[k] = np.maximum(palmar[k], pal)
    best = np.full(len(k), 99.0); fid = np.full(len(k), -1); sid = np.full(len(k), -1); tpar = np.zeros(len(k))
    names = list(F['fingers'])
    for fi, f in enumerate(names):
        pts = F['fingers'][f]
        for si in range(3):
            d, t = segdist(p, pts[si], pts[si + 1])
            better = d < best; best = np.where(better, d, best); fid = np.where(better, fi, fid); sid = np.where(better, si, sid); tpar = np.where(better, t, tpar)
    finger = hand & (best < 1.15) & ~((sid == 0) & (tpar < .02))
    nailed = nail[k] > .6
    for fi, f in enumerate(names):
        pts = F['fingers'][f]; segs = [unit(pts[i + 1] - pts[i]) for i in range(3)]
        mine = finger & (fid == fi)
        if not mine.any(): continue
        bend = np.cross(segs[0], segs[2])
        ax = unit(bend) if np.linalg.norm(bend) > .15 else unit(F['r0'] - (F['r0'] @ segs[1]) * segs[1])
        nail_sel = mine & (sid == 2) & nailed
        nail_n = unit(n[nail_sel].mean(axis=0)) if nail_sel.sum() > 10 else F['dorsal']
        sign = 1.0 if np.cross(ax, segs[2]) @ nail_n > 0 else -1.0
        # joints: MCP (start of seg 0), PIP, DIP with the bisecting axis
        for ji, (joint, a, dstr, pstr, spacing) in enumerate((
                (pts[0], segs[0], .003, .0, .085), (pts[1], unit(segs[0] + segs[1]), .0065, .014, .055), (pts[2], unit(segs[1] + segs[2]), .0055, .013, .05))):
            if f == 'thumb' and ji == 0: continue
            dors = unit(np.cross(ax, a)) * sign; lat = unit(np.cross(a, dors))
            sel = mine & (np.linalg.norm(p - joint, axis=1) < .75)
            if not sel.any(): continue
            q = p[sel]; nn = n[sel]; delta = nn @ dors
            xj = (q - joint) @ a; yj = (q - joint) @ lat
            u = xj + 1.6 * yj * yj + .012 * value_noise(q, .15, 3 + ji)
            env = np.exp(-(xj / .28) ** 2) * smoothstep(.15, .55, delta) * smoothstep(1.0, .55, np.abs(yj) / .9)
            Hd = lines(u, [i * spacing for i in range(-3, 4)], .011, dstr) * env
            H[k[sel]] += Hd; crease_d[k[sel]] += -Hd
            if pstr:
                envp = np.exp(-(xj / .35) ** 2) * smoothstep(-.15, -.55, delta) * smoothstep(1.1, .7, np.abs(yj) / .8)
                Hp = lines(xj + .9 * yj * yj, [.02, -.05] if ji == 1 else [.0], .026, pstr * .8) * envp
                H[k[sel]] += Hp; crease_d[k[sel]] += -Hp
            red[k[sel]] += (.55 if ji else .35) * np.exp(-(xj / .35) ** 2) * smoothstep(.2, .6, delta)
        if f != 'thumb':                                   # finger-base palmar (digital) crease
            sel = mine & (sid == 0)
            dors = unit(np.cross(ax, segs[0])) * sign; lat = unit(np.cross(segs[0], dors))
            q = p[sel]; xj = (q - pts[0]) @ segs[0]; yj = (q - pts[0]) @ lat; xb = .3 * np.linalg.norm(pts[1] - pts[0])
            envp = smoothstep(-.15, -.55, n[sel] @ dors) * np.exp(-((xj - xb) / .4) ** 2)
            Hp = lines(xj + .8 * yj * yj, [xb, xb + .06], .028, .009) * envp; H[k[sel]] += Hp; crease_d[k[sel]] += -Hp
        sel = mine & (sid == 2)
        tt = tpar[sel]; seg_t[k[sel]] = tt; on_distal[k[sel]] = True
        dors = unit(np.cross(ax, segs[2])) * sign
        red[k[sel]] += .7 * smoothstep(.55, .95, tt) * (1 - .5 * smoothstep(.2, .6, n[sel] @ dors))
    # MCP knuckle redness + dorsal tendons + veins on the dorsal hand plane
    dh_w = smoothstep(.05, .45, n @ F['dorsal']) * w_hand
    knuck = [((J(f'{f}_01_{s}') - F['W']) @ F['f0'], (J(f'{f}_01_{s}') - F['W']) @ F['r0']) for f in ('index', 'middle', 'ring', 'pinky')]
    for (kx, ky) in knuck:
        d = np.hypot(x_h - kx, y_h - ky); red[k] += .6 * np.exp(-(d / .55) ** 2) * dh_w
        # extensor tendon: knuckle -> dorsal wrist centre
        tend = polyline_dist(x_h, y_h, [(kx - .3, ky), (kx * .55, ky * .55), (.35, .15 * np.sign(ky + 1e-6))])
        fade = smoothstep(.3, 1.0, x_h) * smoothstep(kx - .2, kx - .8, x_h) * (.7 + .6 * value_noise(p, 1.2, 101))
        H[k] += .014 * np.exp(-(tend / .26) ** 2) * fade * dh_w
    thumb_mcp = J(f'thumb_02_{s}'); tx, ty = (thumb_mcp - F['W']) @ F['f0'], (thumb_mcp - F['W']) @ F['r0']
    for off in (-.35, .35):                                  # EPL / EPB around the snuffbox
        tend = polyline_dist(x_h, y_h, [(tx, ty + off * .3), (tx * .5, ty * .8 + off), (.2, ty * .55 + off)])
        H[k] += .014 * np.exp(-(tend / .24) ** 2) * dh_w * smoothstep(-.2, .6, x_h)
    kx_mean = np.mean([q[0] for q in knuck]); ys = sorted(q[1] for q in knuck)
    webs = [((knuck[i][0] + knuck[i + 1][0]) / 2 * .82, (knuck[i][1] + knuck[i + 1][1]) / 2) for i in range(3)]
    rsign = 1.0
    veins_hand = [
        [webs[0], (kx_mean * .5, webs[0][1] * .9 + .2), (kx_mean * .28, ys[-1] * .6 + .5), (-.2, ys[-1] * .45 + .9)],
        [webs[1], (kx_mean * .48, webs[1][1] * .5 + .15), (kx_mean * .3, webs[1][1] * .2)],
        [webs[2], (kx_mean * .5, webs[2][1] * .9 - .1), (kx_mean * .3, ys[0] * .7 - .3), (-.2, ys[0] * .55 - .9)],
        [(kx_mean * .3, ys[-1] * .6 + .5), (kx_mean * .33, webs[1][1] * .2), (kx_mean * .3, ys[0] * .7 - .3)],
    ]
    for vi, pts in enumerate(veins_hand):
        wob = .06 * value_noise(p, .9, 11 + vi)
        d = polyline_dist(x_h + wob, y_h + wob, pts)
        rad = (.34 if vi < 3 else .30) * (1 + .25 * value_noise(p, 1.1, 61 + vi))
        prof = smoothstep(1, 0, d / rad) ** 2 * dh_w * smoothstep(-.6, .3, x_h)   # broad, soft-shouldered bulge
        prof *= smoothstep(-.15, .2, value_noise(p, 2.2, 71 + vi))          # veins come and go along their length
        H[k] += .024 * prof; vein[k] = np.maximum(vein[k], prof)
    # palm: accepted crease lines, thenar / hypothenar flush
    pc = crease_atlas[k] * smoothstep(.3, .7, palm_mask[k])
    H[k] -= .012 * pc; crease_d[k] += .012 * pc
    red[k] += .35 * pal * (smoothstep(1.0, 2.2, np.abs(y_h - np.mean(ys))) ) * smoothstep(.5, 1.5, x_h)
    # ---- forearm (cylindrical, frame unwinding from the wrist toward the elbow)
    fore = (1 - smoothstep(.3, 1.6, x_h)) * (1 - smoothstep(-.5, 2.5, (p - F['E']) @ (-F['up'])) * smoothstep(F['Lf'] * .7, F['Lf'] * 1.05, (F['W'] - p) @ F['fd']))
    sig = (F['W'] - p) @ F['fd']                         # cm from wrist toward elbow
    q = (p - F['W']) + np.outer(sig, F['fd'])
    # posterior (dorsal) reference turns from the hand dorsum at the wrist to the olecranon at the elbow
    outer_e = unit(F['up'] - F['fd']); d_e = unit(outer_e - (outer_e @ F['fd']) * F['fd'])
    theta = np.arctan2(np.cross(F['dw'], d_e) @ F['fd'], F['dw'] @ d_e)
    wgt = smoothstep(.05, .85, sig / F['Lf']) * theta
    c_, s_ = np.cos(wgt), np.sin(wgt); fxd = np.cross(F['fd'], F['dw'])
    d_s = np.outer(c_, F['dw']) + np.outer(s_, fxd)       # rotated dorsal per texel
    b_s = np.cross(F['fd'][None, :], d_s)
    if (fxd @ (F['r0'] - (F['r0'] @ F['fd']) * F['fd'])) < 0: b_s = -b_s   # +phi = radial side
    phi = np.degrees(np.arctan2(np.einsum('ij,ij->i', q, b_s), np.einsum('ij,ij->i', q, d_s)))
    rr_ = np.linalg.norm(q, axis=1)
    def vein_curve(phi0, phi1, s0, s1, rad, h, seed):
        u = np.clip((sig - s0) / (s1 - s0), 0, 1); path = phi0 + (phi1 - phi0) * u + 8 * np.sin(u * 5.3 + seed)
        dphi = np.radians((phi - path + 180) % 360 - 180) * rr_
        inside = smoothstep(s0 - .5, s0 + 1.5, sig) * smoothstep(s1 + .5, s1 - 2.0, sig)
        radv = rad * (1 + .3 * value_noise(p, 1.6, 81 + seed))
        prof = smoothstep(1, 0, np.abs(dphi) / radv) ** 2 * inside * fore
        prof *= smoothstep(-.2, .18, value_noise(p, 3.5, 91 + seed))        # sinks under fat in places
        H[k] += h * prof; vein[k] = np.maximum(vein[k], prof * .6)
    vein_curve(70, 110, -.5, F['Lf'] * .95, .50, .010, 1)         # cephalic, radial border
    vein_curve(-95, -125, -.5, F['Lf'] * .9, .52, .009, 2)       # basilic, ulnar border
    vein_curve(178, 172, 2.0, F['Lf'] * .82, .45, .006, 3)       # median antebrachial
    vein_curve(110, -135, F['Lf'] * .88, F['Lf'] * 1.02, .55, .008, 4)   # median cubital (diagonal)
    vein_curve(25, 45, 1.0, F['Lf'] * .55, .40, .005, 5)         # dorsal branch
    # palmar wrist tendons and creases
    palm_side = smoothstep(120, 150, np.abs(phi))
    for c0, h in ((180, .016), (155, .013)):
        dphi = np.radians((np.abs(phi) - c0 + 180) % 360 - 180) * rr_
        H[k] += h * np.exp(-(dphi / .28) ** 2) * smoothstep(.5, 1.5, sig) * smoothstep(8.5, 4.5, sig) * fore
    xw = -sig
    for c0, dep in ((-.55, .007), (.1, .010), (.65, .006)):
        Hw = lines(xw + .06 * (np.radians(np.abs(phi) - 180) * rr_) ** 2, [c0], .035, dep) * palm_side * smoothstep(-1.8, -1.0, xw) * smoothstep(1.4, .9, xw)
        H[k] += Hw; crease_d[k] += -Hw
    dorsal_side = 1 - smoothstep(30, 70, np.abs(phi))
    Hd = lines(xw + .03 * value_noise(p, .4, 7), [-1.0, -.75, -.5, -.25, 0, .25], .02, .0022) * dorsal_side * smoothstep(-1.6, -.8, xw) * smoothstep(.6, .2, xw)
    H[k] += Hd; crease_d[k] += -Hd
    inner_arm[k] = np.maximum(inner_arm[k], smoothstep(110, 160, np.abs(phi)) * fore)
    # ---- elbow: olecranon wrinkles, cubital crease, redness
    outer = unit(F['up'] - F['fd']); hinge = unit(np.cross(F['up'], F['fd']))
    def surface_pt(c, dirn, mask):
        kk = np.nonzero(mask)[0]; qq = p[kk] - c
        sc = qq @ dirn - 2.5 * np.linalg.norm(qq - np.outer(qq @ dirn, dirn), axis=1)
        return p[kk[np.argmax(sc)]]
    near = np.linalg.norm(p - F['E'], axis=1) < 6
    O = surface_pt(F['E'] + F['fd'] * .6, outer, near & (reg <= 1)); Fo = surface_pt(F['E'], -outer, near & (reg <= 1))
    dO = np.linalg.norm(p - O, axis=1); along = (p - O) @ F['fd']; lat = (p - O) @ hinge
    u = along + .12 * lat * lat + .16 * value_noise(p, .55, 9) + .07 * value_noise(p, .22, 10)
    gaps = smoothstep(-.25, .15, value_noise(p, .7, 12))             # wrinkles break up instead of contour rings
    Ho = lines(u, [i * .24 + .05 * np.sin(i * 2.3) for i in range(-4, 5)], .032, .0042) * gaps * np.exp(-(dO / 1.7) ** 2) * (reg <= 1)
    H[k] += Ho; crease_d[k] += -Ho; red[k] += .45 * np.exp(-(dO / 1.8) ** 2) * (reg <= 1)
    rough_add[k] += .05 * np.exp(-(dO / 1.8) ** 2)
    dF = (p - Fo) @ F['up']; latF = (p - Fo) @ hinge
    Hc = lines(dF + .08 * latF * latF, [0, .35], .14, .005) * np.exp(-(latF / 3.0) ** 2) * np.exp(-(np.linalg.norm(p - Fo, axis=1) / 3.2) ** 2) * (reg <= 1)
    H[k] += Hc; crease_d[k] += -Hc
    # upper arm inner side lighter
    qa = (p - F['S']) - np.outer((p - F['S']) @ F['up'], F['up'])
    medial_dir = F['me'] - (F['me'] @ F['up']) * F['up']
    inner_up = smoothstep(.2, .7, (qa / np.maximum(np.linalg.norm(qa, axis=1), 1e-6)[:, None]) @ unit(medial_dir))
    w_upper = smoothstep(-.5, 2.5, (p - F['E']) @ (-F['up'])) * (1 - w_hand)
    inner_arm[k] = np.maximum(inner_arm[k], inner_up * w_upper)
log('anatomy')

# ---------------------------------------------------------------- micro relief: furrows + pores
palmish = np.maximum(palmar, smoothstep(.3, .7, palm_mask))
skin = 1 - smoothstep(.25, .6, nail)
# one continuous furrow field everywhere (no cell-size switch on region borders); palms blend in a finer layer
F1, F2, _ = voronoi(pos, .082)
Hm = (-.0034 * (1 - smoothstep(0, .013, F2 - F1)) * (1 + .4 * value_noise(pos, .3, 21)) * (1 - .45 * palmish)).astype(np.float32)
idx = np.nonzero(palmish > .03)[0]
if len(idx):
    F1p, F2p, _ = voronoi(pos[idx], .05)
    Hm[idx] += -.0026 * (1 - smoothstep(0, .008, F2p - F1p)) * palmish[idx]
F1, _, ID = voronoi(pos, .11)
pore = (ID > .62) * np.exp(-(F1 / .016) ** 2) * (1 - .7 * palmish)
Hm += -.0028 * pore
Hm *= skin
H += Hm; crease_d += -np.minimum(Hm, 0) * .5
# macro undulation (muscle / fat), fading smoothly into the hand
H += .02 * value_noise(pos, 2.4, 31) * (1 - w_hand_all) + .004 * value_noise(pos, .9, 32) * (1 - .6 * palmish)
# nails: smooth plate, cuticle groove
H = H * (1 - .9 * smoothstep(.3, .7, nail))
cut = smoothstep(.15, .45, nail) * (1 - smoothstep(.45, .8, nail))
H -= .006 * cut
log('micro')

# ---------------------------------------------------------------- colour (linear)
base = np.array([.360, .235, .185], np.float32)
col = np.tile(base, (len(T), 1))
mott = value_noise(pos, 1.3, 41) * .07 + value_noise(pos, .38, 42) * .035
col *= (1 + mott)[:, None]
col *= (1 + np.stack([mott * .4, -mott * .1, -mott * .3], 1))
tan = (1 - palmar) * (1 - inner_arm)
col *= 1 - np.outer(tan, [.055, .065, .07])
col *= 1 + np.outer(palmar, [.11, .055, .03])
col *= 1 + np.outer(inner_arm * (1 - palmar), [.05, .045, .04])
redm = np.clip(red, 0, 1)
col *= 1 + np.outer(redm, [.07, -.035, -.03])
col *= 1 - np.outer(np.clip(vein, 0, 1) * .5, [.045, .02, -.01])
# freckles / moles: sparse, dorsal surfaces only
F1f, _, IDf = voronoi(pos, .8)
spot = (IDf > .78) * np.exp(-(F1f / (.03 + .04 * IDf)) ** 2) * tan * (1 - smoothstep(.3, .7, nail))
col *= 1 - np.outer(spot, [.13, .16, .17])
cr = np.clip(crease_d / .012, 0, 1)
col *= 1 - np.outer(cr, [.025, .035, .035])
# nails
nailw = smoothstep(.3, .7, nail)
ncol = np.array([.60, .42, .39], np.float32)
lun = on_distal * smoothstep(.36, .3, seg_t) * nailw
edge = on_distal * smoothstep(.9, .97, seg_t) * nailw
nail_col = np.tile(ncol, (len(T), 1)) * (1 + .12 * lun[:, None]) + np.outer(edge, [.18, .2, .2])
col = col * (1 - nailw[:, None]) + nail_col * nailw[:, None]
col *= (1 + np.outer(cut, [.04, -.03, -.03]))
col = np.clip(col, 0, 1)
log('colour')

# ---------------------------------------------------------------- AO / cavity / roughness / scatter
# macro AO from rest curvature (welded Laplacian along the normal), smoothed ~1 cm, interpolated per texel
nb = m.welded_adjacency(); Pn = np.zeros_like(P)
gn = np.zeros_like(P)
for t_, tt in enumerate(m.T):
    for c in range(3): gn[wv[tt[c]]] += NRM[t_, c]
gn /= np.linalg.norm(gn, axis=1, keepdims=True)
lap = np.array([(P[list(nb[i])].mean(axis=0) - P[i]) @ gn[i] if nb[i] else 0 for i in range(m.nw)])
for _ in range(6): lap = .5 * lap + .5 * np.array([lap[list(nb[i])].mean() if nb[i] else lap[i] for i in range(m.nw)])
ao_v = np.clip(1 - 6.0 * np.maximum(lap, 0), .55, 1)
ao = interp(ao_v[wv][m.T][..., None])[:, 0]
cav = 1 - np.clip(crease_d / .01, 0, 1) * .6
ao = ao * (.85 + .15 * cav)
rough = np.full(len(T), .50, np.float32)
rough += .05 * palmar - .03 * (1 - palmar) * w_hand_all + .02 * (1 - w_hand_all)
rough += -.05 * on_distal * smoothstep(.5, .9, seg_t) * palmar                # oily finger pads
rough += -.025 * np.clip(vein, 0, 1) + .08 * np.clip(crease_d / .008, 0, 1) + rough_add
rough += .03 * value_noise(pos, .45, 51)
rough = rough * (1 - nailw) + .26 * nailw
rough = np.clip(rough, .25, .7)
scatter = 1 - .7 * nailw
log('masks')


def to_image(vals, ch):
    img = np.zeros((RES, RES, ch), np.float32); img[iy, ix] = vals.reshape(len(T), ch)
    return img


def dilate(img):
    d, (yy, xx) = ndimage.distance_transform_edt(~cov, return_indices=True)
    return img[yy, xx]


def srgb(c): return np.where(c <= .0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - .055)


Hmin, Hmax = float(H.min()), float(H.max())
h16 = dilate(to_image((H - Hmin) / (Hmax - Hmin), 1))[:, :, 0]
Image.fromarray(np.round(h16 * 65535).astype(np.uint16)).save(OUT / 'height16.png')
(OUT / 'height.json').write_text(json.dumps(dict(min_cm=Hmin, max_cm=Hmax, range_cm=Hmax - Hmin)))
colour = dilate(to_image(srgb(col), 3))
Image.fromarray(np.round(colour * 255).astype(np.uint8), 'RGB').save(OUT / 'T_M4SkinV9_Colour.png')
masks = dilate(to_image(np.stack([ao, rough, cav, scatter], 1), 4))
Image.fromarray(np.round(np.clip(masks, 0, 1) * 255).astype(np.uint8), 'RGBA').save(OUT / 'T_M4SkinV9_Masks.png')
Image.fromarray(np.round(srgb(col.mean(0, keepdims=True)) * 255).astype(np.uint8).reshape(1, 1, 3)).save(OUT / 'mean_colour.png')
stats = dict(texels=int(len(T)), height_range_cm=[Hmin, Hmax], mean_albedo_linear=col.mean(0).tolist(),
             roughness_mean=float(rough.mean()), ao_mean=float(ao.mean()), vein_texels=int((vein > .2).sum()))
(OUT / 'fields_report.json').write_text(json.dumps(stats, indent=1))
log('done', json.dumps(stats))

