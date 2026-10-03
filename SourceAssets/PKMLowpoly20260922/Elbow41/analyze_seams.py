"""Where is the V7 arm mesh actually joined?

Finds the open (boundary) edges of the mesh, groups them into seams, and reports
for each seam which bones drive it and which arm it belongs to.  A visible tear
under one pose but not another is normally an open join between two pieces whose
skinning differs across the join.
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow41'
E39 = ROOT / 'Elbow39'

d = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
V = d['verts'].astype(np.float64)
T = d['tris'].astype(np.int64)
WIDX, WVAL = d['w_idx'], d['w_val'].astype(np.float64)
BONES = list(d['bones'])

print('verts %d  tris %d  bones %d  max influences %d'
      % (len(V), len(T), len(BONES), WIDX.shape[1]))

# vertex -> dominant bone weights
wsum = np.zeros((len(V), len(BONES)))
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    act = (idx >= 0) & (w > 0)
    np.add.at(wsum, (np.where(act)[0], idx[act]), w[act])

# edge -> triangle count
count = defaultdict(int)
for a, b, c in T:
    for u, v in ((a, b), (b, c), (c, a)):
        count[(min(u, v), max(u, v))] += 1
boundary = [e for e, n in count.items() if n == 1]
print('edges %d  boundary(open) edges %d' % (len(count), len(boundary)))

# group boundary edges into connected chains
parent = {}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry:
        parent[rx] = ry


for e in boundary:
    for v in e:
        parent.setdefault(v, v)
for u, v in boundary:
    union(u, v)

groups = defaultdict(list)
for e in boundary:
    groups[find(e[0])].append(e)

seams = []
for root, edges in groups.items():
    vs = sorted({v for e in edges for v in e})
    P = V[vs]
    w = wsum[vs]
    top = np.argsort(-w.sum(axis=0))[:6]
    seams.append({
        'vertices': len(vs),
        'edges': len(edges),
        'centroid': [round(float(x), 4) for x in P.mean(axis=0)],
        'extent': [round(float(x), 4) for x in (P.max(axis=0) - P.min(axis=0))],
        'bones': [[BONES[i], round(float(w[:, i].mean()), 3)] for i in top
                  if w[:, i].mean() > 0.01],
    })
seams.sort(key=lambda s: -s['vertices'])

print('\nseam groups (open-edge loops): %d' % len(seams))
for i, s in enumerate(seams[:18]):
    print('  #%-2d verts %4d edges %4d  centroid %-28s extent %-26s bones %s'
          % (i, s['vertices'], s['edges'], s['centroid'], s['extent'],
             ', '.join('%s %.2f' % (b, v) for b, v in s['bones'][:4])))

# loose parts
adj = defaultdict(set)
for a, b, c in T:
    adj[a].update((b, c))
    adj[b].update((a, c))
    adj[c].update((a, b))
seen = np.zeros(len(V), bool)
parts = []
for s in range(len(V)):
    if seen[s]:
        continue
    stack, comp = [s], []
    seen[s] = True
    while stack:
        x = stack.pop()
        comp.append(x)
        for y in adj[x]:
            if not seen[y]:
                seen[y] = True
                stack.append(y)
    parts.append(comp)
print('\nloose parts: %d' % len(parts))
for p in sorted(parts, key=len, reverse=True)[:12]:
    P = V[p]
    w = wsum[p]
    top = np.argsort(-w.sum(axis=0))[:3]
    print('  verts %5d  bbox min %-26s max %-26s bones %s'
          % (len(p), [round(float(x), 3) for x in P.min(axis=0)],
             [round(float(x), 3) for x in P.max(axis=0)],
             ', '.join('%s %.2f' % (BONES[i], w[:, i].mean()) for i in top)))

(HERE / 'seam_report.json').write_text(json.dumps(
    {'seams': seams, 'loose_parts': [len(p) for p in parts]}, indent=2,
    ensure_ascii=False), encoding='utf-8')
print('\nSEAM_DONE')