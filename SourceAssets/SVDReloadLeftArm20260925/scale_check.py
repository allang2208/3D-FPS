"""Scale/placement sanity check between native viewmodel arms and authored V7 geometry."""
import json
from pathlib import Path
import numpy as np

V7 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
V6 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BareArmsFamilyV6')
BASE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260924\OriginalShapeBareM4')


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


print('--- canonical / base authoring inputs ---')
for p in [BASE / 'M4_original.json', BASE / 'RefinedSkinV3' / 'M4_original.json',
          BASE / 'RefinedSkinV3' / 'hand_refit.json', BASE / 'BareUpperArmsV6' / 'M4_original.json']:
    if not p.exists():
        print(f'{p.name:24s} MISSING {p}')
        continue
    d = load(p)
    pos = np.asarray(d['positions'], dtype=float)
    print(f'{p.parent.name}/{p.name:24s} verts {len(pos):6d} min {np.round(pos.min(0),3)} '
          f'max {np.round(pos.max(0),3)} span {np.round(pos.max(0)-pos.min(0),3)}')

print('--- native source vs authored, same profile ---')
for n in ['M4', 'SVD', 'M16', 'PKM']:
    s = np.asarray(load(V6 / 'Sources' / f'{n}.json')['positions'], dtype=float)
    a = np.asarray(load(V7 / 'Authored' / f'{n}.json')['positions'], dtype=float)
    print(f'{n:5s} native span {np.round(s.max(0)-s.min(0),3)} min {np.round(s.min(0),3)}')
    print(f'      authored span {np.round(a.max(0)-a.min(0),3)} min {np.round(a.min(0),3)} '
          f'ratio {np.round((a.max(0)-a.min(0))/np.maximum(s.max(0)-s.min(0),1e-9),4)}')

print('--- canonical vs authored alignment (M4, index-wise) ---')
auth = load(V7 / 'Authored' / 'M4.json')
canon = np.asarray(auth['canonical_positions'], dtype=float)
pos = np.asarray(auth['positions'], dtype=float)
print(f'canonical span {np.round(canon.max(0)-canon.min(0),3)} min {np.round(canon.min(0),3)}')
print(f'authored  span {np.round(pos.max(0)-pos.min(0),3)} min {np.round(pos.min(0),3)}')
