"""Compare the PKM arm weight layout against the accepted M4 master and a few
other profiles, using the authored JSON the V7 pipeline produced."""
import json
from pathlib import Path

import numpy as np

BASE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
WATCH = ['upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

out = {}
for profile in ['M4', 'PKM', 'AKM', 'SVD', 'M16']:
    path = BASE / 'Authored' / (profile + '.json')
    if not path.exists():
        continue
    d = json.loads(path.read_text(encoding='utf-8'))
    bones = list(d['bones'])
    pos = np.asarray(d['positions'], dtype=np.float64)
    wts = d['weights']
    idx = {n: bones.index(n) for n in bones if n in bones}
    E = 'lowerarm_l'
    W = 'hand_l'
    e = pos[:, idx[E]] if False else None
    # positions is per-bone?  fall back to the skeleton section
    skel = d.get('skeleton')
    out[profile] = {'keys': list(d.keys()),
                    'positions_shape': list(np.asarray(pos).shape),
                    'bones': len(bones),
                    'skeleton_type': type(skel).__name__,
                    'weights_type': type(wts).__name__,
                    'weights_len': len(wts) if hasattr(wts, '__len__') else None}
    if isinstance(wts, list) and wts:
        out[profile]['weight_entry'] = wts[0]
    if isinstance(skel, dict):
        out[profile]['skeleton_keys'] = list(skel.keys())[:12]

(BASE.parent.parent / 'PKMLowpoly20260922' / 'Elbow39' / 'authored_probe.json').write_text(
    json.dumps(out, indent=2, ensure_ascii=False)[:20000], encoding='utf-8')
print(json.dumps(out, indent=2, ensure_ascii=False)[:6000])