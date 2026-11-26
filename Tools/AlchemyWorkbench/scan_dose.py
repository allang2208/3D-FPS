import sys, numpy as np
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Tools/AssetPipeline/FbxDiagnostics"))
from scan_body_fbx import parse_fbx

def kids(nodes, name):
    return [c for c in nodes if len(c) > 0 and c[0] == name]

FILES = [
    ('DOSE_FIXED',  PROJECT / r'SourceAssets\PotionWorkbenchDesign20261015\SeamFix20261017\Fixed\RuntimeV2\SM_AlchemyDose_LOD0.fbx'),
    ('DOSE_BEFORE', PROJECT / r'SourceAssets\PotionWorkbenchDesign20261015\SeamFix20261017\Before\FBX\RuntimeV2\SM_AlchemyDose_LOD0.fbx'),
    ('FILL_FIXED',  PROJECT / r'SourceAssets\PotionWorkbenchDesign20261015\SeamFix20261017\Fixed\RuntimeV2\SM_AlchemyDoseFill_LOD0.fbx'),
    ('FILL_BEFORE', PROJECT / r'SourceAssets\PotionWorkbenchDesign20261015\SeamFix20261017\Before\FBX\RuntimeV2\SM_AlchemyDoseFill_LOD0.fbx'),
]

for tag, path in FILES:
    try:
        tree, ver = parse_fbx(path)
    except Exception as e:
        print(tag, 'parse fail', e)
        continue
    top = [n[0] for n in tree]
    objs = kids(tree, 'Objects')
    print('===', tag, 'ver', ver, 'top', top[:8])
    if not objs:
        continue
    for g in kids(objs[0][2], 'Geometry'):
        nm = g[1][0] if g[1] else '?'
        vv = kids(g[2] if isinstance(g[2], list) else g, 'Vertices')
        vv = vv or kids(g[2], 'Vertices')
        verts_node = None
        for c in g[2]:
            if c[0] == 'Vertices':
                verts_node = c
        if verts_node is None:
            continue
        verts = np.asarray(verts_node[1][0]).reshape(-1, 3)
        print(nm, 'verts', len(verts), 'min', verts.min(0).round(1), 'max', verts.max(0).round(1))
        cen = np.median(verts, axis=0)
        d = np.linalg.norm(verts - cen, axis=1)
        order = np.argsort(d)[-8:]
        for i in order:
            print('   outlier', int(i), verts[i].round(2), 'd', round(float(d[i]), 1))
        # also list any vertex with |z| or |x| or |y| far from body
        lo, hi = verts.min(0), verts.max(0)
        mid = (lo + hi) / 2
        span = hi - lo
        far = np.abs(verts - mid) > span * 1.0
        if far.any():
            idx = np.where(far.any(axis=1))[0]
            print('   farcount', len(idx))
