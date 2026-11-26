import sys, os, glob, numpy as np
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Tools/AssetPipeline/FbxDiagnostics"))
from scan_body_fbx import parse_fbx

def kids(nodes, name):
    return [c for c in nodes if len(c) > 0 and c[0] == name]

def scan(path):
    try:
        tree, ver = parse_fbx(path)
    except Exception as e:
        return [(None, 'parse-fail:%s' % e)]
    objs = kids(tree, 'Objects')
    if not objs:
        return [(None, 'no-objects')]
    out = []
    geos = kids(objs[0][2], 'Geometry')
    # vertex id -> position handled inside geometry: LayerElementVertexID optional
    for g in geos:
        gid = g[1][0] if g[1] else None
        vnodes = [c for c in g[2] if c[0] == 'Vertices']
        if not vnodes:
            continue
        verts = np.asarray(vnodes[0][1][0]).reshape(-1, 3)
        n = len(verts)
        lo, hi = verts.min(0), verts.max(0)
        span = (hi - lo)
        mid = (hi + lo) / 2
        # outlier = vertex outside bounding box expanded 15% in any axis
        lim = np.maximum(np.abs(lo - mid), np.abs(hi - mid))
        r = np.abs(verts - mid) / np.maximum(lim, 1e-6)
        out.append((os.path.basename(path), n, lo.round(1), hi.round(1),
                    int(np.sum(np.max(r, 1) > 1.15)), float(np.max(r))))
    return out

files = []
for pat in [r'SourceAssets\PotionWorkbenchDesign20261015\SeamFix20261017\Fixed\**\*.fbx',
            r'SourceAssets\PotionWorkbenchDesign20261015\RuntimeV2\Authored\*.fbx',
            r'SourceAssets\PotionWorkbenchDesign20261015\IntegrationV1\**\*.fbx']:
    files += glob.glob(str(PROJECT / pat), recursive=True)
files = sorted(set(files))
for f in files:
    for r in scan(f):
        print(r)
