"""Measure an LMG201 cloth-box reload (tracks json.gz) offline.

python -X utf8 diagnose.py <label> <tracks.json.gz> [--step 4] [--garments] [--empty]
Writes Diagnostics/<label>.json (summary) and <label>.npz (per-frame series).
Read only; nothing is imported or saved to UE.
"""
import sys, json, time
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
import diag_lib as D

args = sys.argv[1:]
label, tracks_path = args[0], Path(args[1])
step = int(args[args.index('--step') + 1]) if '--step' in args else 4
use_garments = '--garments' in args
empty = '--empty' in args
duration = float(args[args.index('--duration') + 1]) if '--duration' in args else 6.2
ret = float(args[args.index('--return') + 1]) if '--return' in args else 5.45
phases = json.loads(args[args.index('--phases') + 1]) if '--phases' in args else {'old_hidden': 2.53, 'new_visible': 2.915}
if '--swap' in args:
    a, b = (float(x) for x in args[args.index('--swap') + 1].split(','))
    phases = {'old_hidden': a, 'new_visible': b}
OUT = D.HERE / 'Diagnostics'
t0 = time.time()

tracks = D.load_tracks(tracks_path)
F = len(tracks['hand_l'])
fps = 120.0
Wall = D.worlds(tracks)
frames = np.unique(np.r_[np.arange(0, F, step), F - 1])
body = D.Body()
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
region = {}
for n, i in D.BI.items():
    for key in ('upperarm', 'lowerarm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky', 'clavicle'):
        if n.startswith(key):
            region[i] = ('finger' if key in ('thumb', 'index', 'middle', 'ring', 'pinky') else key) + '_' + n[-1]
skin_region = np.array([region.get(b, 'other') for b in skin.dom])
skin_edges = D.edges_of(skin.tris)
e0 = np.linalg.norm(skin.p[skin_edges[:, 0]] - skin.p[skin_edges[:, 1]], axis=1)
ok_e = e0 > .05
skin_edges, e0 = skin_edges[ok_e], e0[ok_e]
edge_region = skin_region[skin_edges[:, 0]]
probes = {s: D.RadiusProbe(skin, s) for s in 'lr'}
seams = {('elbow', s): D.seam_vertices(skin, s, ('upperarm',), ('lowerarm',)) for s in 'lr'}
seams |= {('wrist', s): D.seam_vertices(skin, s, ('lowerarm',), ('hand',)) for s in 'lr'}
print('SEAMS', {k[0] + '_' + k[1]: len(v) for k, v in seams.items()}, flush=True)

garments = {}
if use_garments:
    specs = {
        'chainmail': D.SA / 'ChainmailReloadFit20260929/LMG201_saved.json',
        'sweater': D.SA / 'FieldSweaterKnit20260929/Authored/LMG201.json',
        'sleeves_default': D.SA / 'ModularOutfit20260925/FittedSleevesV1/Authored/PKM.json',
        'gloves_default': D.SA / 'ModularOutfit20260925/FittedFieldGlovesV1/Authored/PKM.json',
        'gloves_black': D.SA / 'BlackLeatherDetail20260928/StitchWearV4/Authored/PKM.json',
        'gloves_fingerless': D.SA / 'ModularOutfit20260927/TailoredFingerlessV1/Authored/PKM.json',
    }
    skin_n0 = D.vertex_normals(skin.p, skin.tris)
    stree = cKDTree(skin.p)
    for k, p in specs.items():
        if not p.exists():
            print('MISSING', k, p)
            continue
        g = D.load_json_mesh(p, k)
        d, j = stree.query(g.p, distance_upper_bound=4.0)
        okg = np.isfinite(d)
        h0 = np.full(len(g.p), np.nan)
        h0[okg] = np.einsum('ij,ij->i', g.p[okg] - skin.p[j[okg]], skin_n0[j[okg]])
        # visible skin that sits just inside this garment at rest (wrist band 3, fingers)
        gn0 = D.vertex_normals(g.p, g.tris)
        gtree = cKDTree(g.p)
        dd, jj = gtree.query(skin.p, distance_upper_bound=2.0)
        inside = np.isfinite(dd)
        sd = np.full(len(skin.p), np.nan)
        sd[inside] = np.einsum('ij,ij->i', skin.p[inside] - g.p[jj[inside]], gn0[jj[inside]])
        garments[k] = dict(mesh=g, j=j, ok=okg & (h0 > -.3) & (h0 < 3.0), h0=h0,
                           cover=np.where(inside & (sd < -.02) & (sd > -1.5))[0], cover_j=jj, gn0=gn0)
        print('GARMENT', k, len(g.p), 'fit', int(garments[k]['ok'].sum()), 'covered skin', len(garments[k]['cover']), flush=True)
    # visible skin sections regardless of outfit: 3 (wrist band)
    vis_skin = np.zeros(len(skin.p), bool)
    tri_m = np.asarray(skin.mats)
    for m in (3,):
        vis_skin[np.unique(skin.tris[tri_m == m])] = True

series = {k: [] for k in ('t', 'eye_min_l', 'eye_min_r', 'eye_bone_l', 'pen_depth', 'pen_count', 'pen_part',
                          'pen_region', 'radius_min_elbow_l', 'radius_min_fore_l', 'radius_min_elbow_r',
                          'stretch_max_l', 'stretch_p99_l', 'stretch_max_r', 'compress_min_l',
                          'det_elbow_med_l', 'det_elbow_min_l', 'det_wrist_min_l', 'det_elbow_min_r', 'det_wrist_min_r')}
gseries = {k: {'gun_depth': [], 'gun_count': [], 'sink_count': [], 'sink_max': [], 'float_max': [], 'poke_count': [], 'poke_max': []} for k in garments}
for fi in frames:
    t = fi / fps
    W = Wall[fi]
    sp = skin.pose(W)
    alpha = D.framing_alpha(t, duration, ret)
    eye, fwd, right, up = D.camera(alpha)
    inside, dist = D.view_metrics(sp, eye, fwd, right, up)
    for s in 'lr':
        m = inside & np.char.endswith(skin_region.astype(str), '_' + s)
        series['eye_min_' + s].append(float(dist[m].min()) if m.any() else np.inf)
        if s == 'l':
            series['eye_bone_l'].append(skin_region[m][np.argmin(dist[m])] if m.any() else '')
    vg = {'gun', 'cover'} | ({'old_feed'} if t < phases['old_hidden'] else set()) | ({'new_feed'} if t >= phases['new_visible'] else set())
    if empty and 'old_feed' in vg:
        vg = vg  # old belt hidden when empty is a material state; the pouch remains
    sdist, part = body.signed(sp, W, vg)
    pen = sdist < -.25
    series['pen_count'].append(int(pen.sum()))
    k = int(np.argmin(sdist))
    series['pen_depth'].append(float(-sdist[k]) if sdist[k] < 0 else 0.0)
    series['pen_part'].append(str(part[k]) if sdist[k] < 0 else '')
    series['pen_region'].append(str(skin_region[k]) if sdist[k] < 0 else '')
    for s in 'lr':
        rr = probes[s].ratios(sp, W)
        tu, tf = probes[s].tt['upper'], probes[s].tt['fore']
        eb = np.r_[rr['upper'][tu > .75], rr['fore'][tf < .25]]
        if s == 'l':
            series['radius_min_elbow_l'].append(float(np.percentile(eb, 1)))
            series['radius_min_fore_l'].append(float(np.percentile(rr['fore'][(tf > .25) & (tf < .9)], 1)))
        else:
            series['radius_min_elbow_r'].append(float(np.percentile(eb, 1)))
    el = np.linalg.norm(sp[skin_edges[:, 0]] - sp[skin_edges[:, 1]], axis=1) / e0
    for s in 'lr':
        m = np.char.endswith(edge_region.astype(str), '_' + s) & ~np.char.startswith(edge_region.astype(str), 'finger')
        series['stretch_max_' + s].append(float(el[m].max()))
        if s == 'l':
            series['stretch_p99_l'].append(float(np.percentile(el[m], 99.9)))
            series['compress_min_l'].append(float(np.percentile(el[m], .1)))
    for s in 'lr':
        de = D.blend_det(skin, W, seams[('elbow', s)])
        dw = D.blend_det(skin, W, seams[('wrist', s)])
        if s == 'l':
            series['det_elbow_med_l'].append(float(np.median(de)))
        series['det_elbow_min_' + s].append(float(de.min()))
        series['det_wrist_min_' + s].append(float(dw.min()))
    series['t'].append(t)
    if garments:
        sn = D.vertex_normals(sp, skin.tris)
        for gk, G in garments.items():
            g = G['mesh']
            gp = g.pose(W)
            sd, _ = body.signed(gp, W, vg)
            gseries[gk]['gun_count'].append(int((sd < -.25).sum()))
            gseries[gk]['gun_depth'].append(float(max(0, -sd.min())))
            ok = G['ok']
            h = np.einsum('ij,ij->i', gp[ok] - sp[G['j'][ok]], sn[G['j'][ok]])
            dh = h - G['h0'][ok]
            gseries[gk]['sink_count'].append(int(((h < -.1) & (G['h0'][ok] > .05)).sum()))
            gseries[gk]['sink_max'].append(float(max(0, -(h[G['h0'][ok] > .05]).min())) if (G['h0'][ok] > .05).any() else 0.)
            gseries[gk]['float_max'].append(float(np.percentile(np.abs(dh), 99.9)))
            cv = G['cover']
            cv = cv[vis_skin[cv]]
            if len(cv):
                gn = D.vertex_normals(gp, g.tris)
                jj = G['cover_j'][cv]
                s2 = np.einsum('ij,ij->i', sp[cv] - gp[jj], gn[jj])
                gseries[gk]['poke_count'].append(int((s2 > .05).sum()))
                gseries[gk]['poke_max'].append(float(max(0, s2.max())))
            else:
                gseries[gk]['poke_count'].append(0)
                gseries[gk]['poke_max'].append(0.)

# bone-level (full rate)
bone = {}
for s in 'lr':
    tw = D.forearm_twist(Wall, s)
    bone['hand_twist_' + s] = tw['hand']
    bone['tw01_' + s] = tw['lowerarm_twist_01']
    bone['tw02_' + s] = tw['lowerarm_twist_02']
    bone['elbow_' + s] = D.elbow_angle(Wall, s)
    bone['clav_shift_' + s] = D.clavicle_shift(Wall, s)
    bone['elbow_roll_' + s] = D.elbow_cap_roll(Wall, s)
hl = Wall[:, D.BI['hand_l'], :3, 3]
el = Wall[:, D.BI['lowerarm_l'], :3, 3]
jump_hand = np.r_[0, np.linalg.norm(np.diff(hl, axis=0), axis=1)] * 2  # per 1/60 s
jump_elbow = np.r_[0, np.linalg.norm(np.diff(el, axis=0), axis=1)] * 2
# twist speed (deg per 1/60 s)
tw_speed = np.r_[0, np.abs(np.diff(np.unwrap(np.radians(bone['hand_twist_l']))))] * 2 * 57.2958

S = {k: np.asarray(v) for k, v in series.items()}
summary = dict(label=label, tracks=str(tracks_path), frames=int(F), sampled=len(frames), step=step,
               bone_length_err_cm=D.bone_length_error(Wall[frames]),
               clavicle_shift_max_cm={s: float(bone['clav_shift_' + s].max()) for s in 'lr'},
               eye_min_cm={s: float(S['eye_min_' + s].min()) for s in 'lr'},
               eye_min_t={s: float(S['t'][np.argmin(S['eye_min_' + s])]) for s in 'lr'},
               eye_idle_cm={s: float(S['eye_min_' + s][0]) for s in 'lr'},
               pen_depth_max_cm=float(S['pen_depth'].max()), pen_depth_t=float(S['t'][np.argmax(S['pen_depth'])]),
               pen_part=str(S['pen_part'][np.argmax(S['pen_depth'])]), pen_region=str(S['pen_region'][np.argmax(S['pen_depth'])]),
               pen_count_max=int(S['pen_count'].max()), pen_depth_idle=float(S['pen_depth'][0]),
               frames_pen_over_05=int((S['pen_depth'] > .5).sum()), frames_pen_over_10=int((S['pen_depth'] > 1.0).sum()),
               radius_elbow_min_l=float(S['radius_min_elbow_l'].min()), radius_elbow_min_l_t=float(S['t'][np.argmin(S['radius_min_elbow_l'])]),
               radius_elbow_idle_l=float(S['radius_min_elbow_l'][0]),
               radius_fore_min_l=float(S['radius_min_fore_l'].min()), radius_fore_idle_l=float(S['radius_min_fore_l'][0]),
               radius_elbow_min_r=float(S['radius_min_elbow_r'].min()), radius_elbow_idle_r=float(S['radius_min_elbow_r'][0]),
               stretch_max_l=float(S['stretch_max_l'].max()), stretch_max_l_t=float(S['t'][np.argmax(S['stretch_max_l'])]),
               stretch_idle_l=float(S['stretch_max_l'][0]), stretch_p999_l=float(S['stretch_p99_l'].max()),
               compress_min_l=float(S['compress_min_l'].min()), stretch_max_r=float(S['stretch_max_r'].max()),
               hand_twist_l_range=[float(bone['hand_twist_l'].min()), float(bone['hand_twist_l'].max())],
               hand_twist_l_idle=float(bone['hand_twist_l'][0]),
               tw01_l_range=[float(bone['tw01_l'].min()), float(bone['tw01_l'].max())],
               tw02_l_range=[float(bone['tw02_l'].min()), float(bone['tw02_l'].max())],
               twist_speed_max_l=float(tw_speed.max()), twist_speed_t=float(np.argmax(tw_speed) / fps),
               det_elbow_min_l=float(S['det_elbow_min_l'].min()), det_elbow_min_l_t=float(S['t'][np.argmin(S['det_elbow_min_l'])]),
               det_elbow_med_min_l=float(S['det_elbow_med_l'].min()), det_elbow_idle_l=float(S['det_elbow_min_l'][0]),
               det_wrist_min_l=float(S['det_wrist_min_l'].min()), det_wrist_min_l_t=float(S['t'][np.argmin(S['det_wrist_min_l'])]),
               det_wrist_idle_l=float(S['det_wrist_min_l'][0]),
               det_elbow_min_r=float(S['det_elbow_min_r'].min()), det_wrist_min_r=float(S['det_wrist_min_r'].min()),
               elbow_roll_l_range=[float(bone['elbow_roll_l'].min()), float(bone['elbow_roll_l'].max())],
               elbow_roll_l_idle=float(bone['elbow_roll_l'][0]),
               elbow_roll_r_range=[float(bone['elbow_roll_r'].min()), float(bone['elbow_roll_r'].max())],
               clav_shift_change_cm={s: float(np.abs(bone['clav_shift_' + s] - bone['clav_shift_' + s][0]).max()) for s in 'lr'},
               elbow_l_range=[float(bone['elbow_l'].min()), float(bone['elbow_l'].max())],
               elbow_r_range=[float(bone['elbow_r'].min()), float(bone['elbow_r'].max())],
               jump_hand_max_cm=float(jump_hand.max()), jump_hand_t=float(np.argmax(jump_hand) / fps),
               jump_elbow_max_cm=float(jump_elbow.max()), jump_elbow_t=float(np.argmax(jump_elbow) / fps),
               garments={k: {m: (float(np.max(v)) if len(v) else 0.) for m, v in G.items()} | {m + '_idle': (float(v[0]) if len(v) else 0.) for m, v in G.items()} for k, G in gseries.items()},
               seconds=round(time.time() - t0, 1))
(OUT / (label + '.json')).write_text(json.dumps(summary, indent=1))
np.savez_compressed(OUT / (label + '.npz'), **{k: np.asarray(v) for k, v in series.items() if k not in ('eye_bone_l', 'pen_part', 'pen_region')},
                    **{'bone_' + k: v for k, v in bone.items()}, jump_hand=jump_hand, jump_elbow=jump_elbow,
                    **{'g_' + gk + '_' + m: np.asarray(v) for gk, G in gseries.items() for m, v in G.items()})
print('DIAG_DONE', json.dumps(summary, indent=1))
