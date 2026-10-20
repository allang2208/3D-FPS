"""Offline: worst frames of one pose-source group with every installed corrective (mesh payload + JC_Pose payload):
pinholes per side, where the folded faces are (dominant bone), and what an untangle at that frame can reach.
python analyze_worst.py batch1 SK_LMG201_Cover10 [top]"""
import sys, json, collections
import numpy as np
BATCH, SUB = sys.argv[1], sys.argv[2]; TOP = int(sys.argv[3]) if len(sys.argv) > 3 else 8
# importing pose_examples runs its generation for the meshes matching argv[2:]; '__none__' matches nothing
# (R3c: with "SK_x 2" the '2' matched every path and missing payloads were generated as a side effect)
sys.argv = ['pose_examples.py', BATCH, '__none__']
import pose_examples as pe
from rollout import R, load_snapshot

plan = pe.plan
entry = next(e for e in plan['meshes'] if SUB in e['mesh'])
srcs = tuple(entry.get('pose_sources') or [entry['pose_source']])
leader = load_snapshot(plan['viewmodels'][srcs[0]])['bones']
ms = pe.MeshState(entry['mesh'], leader)
import os
pp = json.loads((R / 'Work' / (BATCH + os.environ.get('V9R_POSE_SUB', '_pose')) / (ms.key + '.json')).read_text())
X = np.array(ms.p['positions'])
for name, rows in pp['morphs'].items():
    d = np.zeros_like(ms.P)
    for row in rows:
        v = ms.vid[row[0]]; d[ms.w[v]] = np.array(row[1:4]) - X[v]
    ms.names.append(name); ms.S = np.concatenate([ms.S, d[None]], axis=0)
    s = name.split('_')[2].lower(); ms.driver.poses[s].append((name, [pe.pose_value(x) for x in name.split('_')[3:11]]))
frames = pe.frames_of(srcs)
rows = []
for fr in frames:
    for s in 'lr':
        if s not in ms.driver.sides: continue
        rows.append((ms.count(fr['pose'], s), s, fr))
rows.sort(key=lambda x: -x[0])
dom = np.argmax(ms.rig.Wval, axis=1); dom_bone = np.array([ms.rig.used[i] for i in ms.rig.Widx[np.arange(len(dom)), dom]])
print('group', '|'.join(srcs), 'examples', {s: len(ms.driver.poses[s]) for s in 'lr'}, 'frames', len(frames))
for n, s, fr in rows[:TOP]:
    Xp, A = ms.posed(fr['pose']); bad = ms.rig.inverted(Xp, ms.face_side[s])
    regions = collections.Counter(dom_bone[ms.rig.TW[bad]].ravel().tolist()).most_common(4)
    mask = (ms.rig.side == s).astype(float)
    corr, g = ms.rig.fold_guard(Xp, np.zeros_like(ms.P), mask)
    rest = np.linalg.solve(A, corr[:, :, None])[:, :, 0]; mag = np.linalg.norm(rest, axis=1)
    sig = [round(x) for x in ms.driver.signature(fr['pose'], s)]
    w = ms.driver.weights(fr['pose']); top_ex = sorted(((v, k) for k, v in w.items() if k.startswith('JC_Pose_' + s.upper())), reverse=True)[:2]
    print('%3d %s %-45s f%-3d sig %s | %s | untangle %d->%d, rest max %.2f cm (>0.5: %d verts) | ex %s' % (
        n, s, fr['clip'].split('/')[-1][:45], fr['fi'], sig, regions, g['folds_before'], g['folds_left'], mag.max(), int((mag > .5).sum()),
        [(round(v, 2), k[10:]) for v, k in top_ex]))
