"""Bake deformed meshes for a few clip times into an npz for preview renders.

python -X utf8 export_frames.py <tracks.json.gz> <out.npz> <outfit> t1 t2 ...
outfit: bare | chainmail_black | sweater_fingerless | default
Positions are UE component cm; cameras follow the runtime cloth-reload anchor.
"""
import sys, json
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import diag_lib as D

tracks_path, out, outfit = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
opts = [a for a in sys.argv[4:] if a.startswith('--')]
times = [float(x) for x in sys.argv[4:] if not x.startswith('--')]
duration = 6.2
ret = 5.45
hidden_old, new_vis = 2.53, 2.915
for o in opts:
    k, v = o[2:].split('=')
    if k == 'duration': duration = float(v)
    if k == 'return': ret = float(v)
    if k == 'old_hidden': hidden_old = float(v)
    if k == 'new_visible': new_vis = float(v)
tracks = D.load_tracks(tracks_path)
F = len(tracks['hand_l'])
fr = np.clip(np.round(np.array(times) * 120).astype(int), 0, F - 1)
W = D.worlds(tracks, fr)
body = D.Body()
groups = {}
for part, sel in body.parts.items():
    groups.setdefault(body.group(part), []).append(sel)
meshes = {}
tri_all = body.tris[~np.isin(body.tri_mat, body.ARM_MATS)]
for g, sels in groups.items():
    if g == 'magazine':
        continue
    vid = np.unique(np.concatenate(sels))
    mask = np.zeros(len(body.pos), bool)
    mask[vid] = True
    tri = tri_all[mask[tri_all].all(1)]
    sk = D.Skin(body.pos[vid], (body.bi[vid], body.bw[vid]))
    meshes[g] = (sk, np.searchsorted(vid, tri))
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json')
garment_files = {
    'chainmail': D.SA / 'ChainmailReloadFit20260929/LMG201_saved.json',
    'sweater': D.SA / 'FieldSweaterKnit20260929/Authored/LMG201.json',
    'sleeves': D.SA / 'ModularOutfit20260925/FittedSleevesV1/Authored/PKM.json',
    'gloves': D.SA / 'ModularOutfit20260925/FittedFieldGlovesV1/Authored/PKM.json',
    'black': D.SA / 'BlackLeatherDetail20260928/StitchWearV4/Authored/PKM.json',
    'fingerless': D.SA / 'ModularOutfit20260927/TailoredFingerlessV1/Authored/PKM.json',
}
wear = {'bare': [], 'chainmail_black': ['chainmail', 'black'], 'sweater_fingerless': ['sweater', 'fingerless'],
        'default': ['sleeves', 'gloves']}[outfit]
covered = set()
if any(w in ('chainmail', 'sweater', 'sleeves') for w in wear): covered |= {0, 1}
if any(w in ('black', 'gloves') for w in wear): covered |= {2}
skin_tris = skin.tris[~np.isin(np.asarray(skin.mats), list(covered))]
if 'fingerless' in wear:
    # fingerless recipe keeps exposed skin; approximate with full hand skin under the glove
    skin_tris = skin.tris[~np.isin(np.asarray(skin.mats), [0, 1])]
meshes['skin'] = (skin, skin_tris)
for w in wear:
    g = D.load_json_mesh(garment_files[w])
    meshes[w] = (g, g.tris)
data = {'times': np.array(times), 'names': np.array(list(meshes))}
for k, (sk, tri) in meshes.items():
    data['tri_' + k] = tri.astype(np.int32)
    data['pos_' + k] = np.stack([sk.pose(W[i]) for i in range(len(fr))]).astype(np.float32)
vis = []
cams = []
for t in times:
    vis.append([t < hidden_old if k == 'old_feed' else t >= new_vis if k == 'new_feed' else True for k in meshes])
    e, f, r, u = D.camera(D.framing_alpha(t, duration, ret))
    cams.append(e)
data['visible'] = np.array(vis)
data['eye'] = np.array(cams)
np.savez_compressed(out, **data)
print('EXPORTED', out, list(meshes), fr.tolist())
