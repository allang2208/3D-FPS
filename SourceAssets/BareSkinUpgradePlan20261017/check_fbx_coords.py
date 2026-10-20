"""Read-only: do FBX import sources carry valid canonical skin coordinates in UV1-3?

Shared bare-skin parents decode RestPosition=(UV1.x,UV1.y,UV2.x), RestNormal=(UV2.y,UV3.x,UV3.y)
in UE space, and UE's FBX import stores V as 1-V. A source is valid when the UE-side decode is a
unit normal; 'raw' unit normals mean the writer forgot to pre-flip V (UE then sees a broken field).
"""
import json, sys
from pathlib import Path
import numpy as np
R = Path('D:/FPS3D/FPSGAME/SourceAssets'); sys.path.insert(0, str(R / 'BareHandAudit20261016'))
from fbx_bin import FBX

files = json.loads((R / 'BareHandAudit20261016/import_source_files.json').read_text())
rows = []
for f in files:
    p = Path(f)
    if not p.exists(): rows.append(dict(file=f, missing=True)); continue
    fbx = FBX(f); objects = next(n for n in fbx.roots if n.name == 'Objects')
    for g in objects.find_all('Geometry'):
        layers = {}
        for el in g.find_all('LayerElementUV'):
            idx = el.props[0].get(); uv = np.array(el.find('UV').props[0].get()).reshape(-1, 2)
            ref = el.find('ReferenceInformationType').props[0].get()
            ui = el.find('UVIndex'); ix = np.array(ui.props[0].get()) if ui is not None else None
            layers[idx] = uv[ix] if (ref == b'IndexToDirect' and ix is not None) else uv
        name = g.props[1].get().split(b'\x00')[0].decode('utf8', 'replace')
        if len(layers) < 4 or any(len(layers[i]) != len(layers[0]) for i in range(4)):
            rows.append(dict(file=p.relative_to(R).as_posix(), geometry=name, uv_layers=len(layers), canonical=False)); continue
        u2, u3 = layers[2], layers[3]
        n_ue = np.stack([1 - u2[:, 1], u3[:, 0], 1 - u3[:, 1]], 1)
        n_raw = np.stack([u2[:, 1], u3[:, 0], u3[:, 1]], 1)
        ok_ue = np.abs(np.linalg.norm(n_ue, axis=1) - 1) < .03; ok_raw = np.abs(np.linalg.norm(n_raw, axis=1) - 1) < .03
        any_ok = ok_ue | ok_raw; zero = np.all(np.abs(np.concatenate([layers[1], u2, u3], 1)) < 1e-6, axis=1)
        rows.append(dict(file=p.relative_to(R).as_posix(), geometry=name, uv_layers=len(layers), corners=len(u2),
                         ue_valid=round(float(ok_ue.mean()), 3), raw_valid_only=round(float((ok_raw & ~ok_ue).mean()), 3),
                         zero=round(float(zero.mean()), 3), neither=round(float((~any_ok & ~zero).mean()), 3)))
for r in rows: print(json.dumps(r, ensure_ascii=False))
(Path(__file__).parent / 'fbx_coords.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False))
