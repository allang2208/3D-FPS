"""Read FULL skin weights from an arms FBX and list which bones actually own
vertices.

The workbench fold code collapses every bone outside `ArmBones` to a 0.01-scale
point at the clavicle midpoint. That is harmless ONLY if no vertex is weighted
to a non-arm bone. The install payload we inspected earlier covered just the
edited subset, so check the complete cluster data here.
"""
import sys
import collections
import numpy as np

from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Tools/AssetPipeline/FbxDiagnostics"))
from scan_body_fbx import parse_fbx

P = sys.argv[1] if len(sys.argv) > 1 else (
    PROJECT / "SourceAssets/DarkBow20260925/ArmsV4/Export/SK_Bow_BareArmsV7.fbx")

tree, _ = parse_fbx(P)
objs = [c for c in tree if c[0] == 'Objects'][0][2]
models = {int(m[1][0]): str(m[1][1]).split(chr(0))[0]
          for m in objs if m[0] == 'Model'}

# Deformer -> (type, bone model id)
deformers = {}
for d in [c for c in objs if c[0] == 'Deformer']:
    did = int(d[1][0])
    kind = None
    for e in d[2]:
        if e[0] == 'Type':
            kind = e[1]
    if kind not in ('Skin', 'Cluster'):
        continue
    deformers[did] = (kind, d)

clusters = [(did, v) for did, (k, v) in deformers.items() if k == 'Cluster']
print('clusters:', len(clusters))

counts = collections.Counter()
tot = 0
for did, node in clusters:
    bone = None
    idx = None
    wts = None
    for e in node[2]:
        if e[0] == 'Indexes':
            idx = np.asarray(e[1][0], dtype=np.int64)
        elif e[0] == 'Weights':
            wts = np.asarray(e[1][0], dtype=float)
        elif e[0] == 'Model':
            bone = int(e[2][0]) if False else None
    # the bone is referenced through a "Model" connection, handled below
    counts[did] = len(idx) if idx is not None else 0
    tot += counts[did]

# connections: C "OO", child, parent
conn = [c for c in tree if c[0] == 'Connections']
links = conn[0][1] if conn else []
bone_of = {}
for a, b in links:
    if a[0] == 'OO' and b[0] == 'OO':
        child, parent = int(a[1]), int(b[1])
        if parent in deformers:
            bone_of[parent] = child

print('\n%-24s %8s %10s' % ('bone', 'verts', 'weight_sum'))
rows = []
for did, node in clusters:
    idx = None
    wts = None
    for e in node[2]:
        if e[0] == 'Indexes':
            idx = np.asarray(e[1][0], dtype=np.int64)
        elif e[0] == 'Weights':
            wts = np.asarray(e[1][0], dtype=float)
    if idx is None:
        continue
    bone = bone_of.get(did)
    name = models.get(bone, '?%s' % bone)
    rows.append((name, len(idx), float(wts.sum()) if wts is not None else 0.0))

rows.sort(key=lambda r: -r[1])
for name, n, s in rows:
    print('%-24s %8d %10.1f' % (name, n, s))

print('\ntotal clustered vert-entries:', sum(r[1] for r in rows))

ARM = ('clavicle', 'upperarm', 'lowerarm', 'hand', 'thumb', 'index',
       'middle', 'ring', 'pinky')
def is_arm(n):
    return any(k in n.lower() for k in ARM)

non_arm = [r for r in rows if not is_arm(r[0])]
print('\nNON-ARM bones carrying weight: %d' % len(non_arm))
for name, n, s in non_arm:
    print('   %-24s %8d verts  weight_sum %.1f' % (name, n, s))
