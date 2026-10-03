"""Compare the per-profile arm bind poses and authored geometry across profiles."""
import json
from pathlib import Path
import numpy as np

V7 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
V6 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BareArmsFamilyV6')
NAMES = ['M4', 'SVD', 'AKM', 'M16', 'PKM', 'A762', 'M1911', 'RuneSword', 'Axe']


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


sources = {n: load(V6 / 'Sources' / f'{n}.json') for n in NAMES}
authored = {n: load(V7 / 'Authored' / f'{n}.json') for n in NAMES}

print('--- raw ranges (native source) ---')
for n in NAMES:
    p = np.asarray(sources[n]['positions'], dtype=float)
    print(f'{n:10s} verts {len(p):6d} tri {len(sources[n]["triangles"]):6d} '
          f'pos min {np.round(p.min(0),3)} max {np.round(p.max(0),3)}')

print('--- authored positions identical to another profile? ---')
ref = {n: np.asarray(authored[n]['positions'], dtype=float) for n in NAMES}
for n in NAMES:
    same = [m for m in NAMES if m != n and ref[m].shape == ref[n].shape
            and np.allclose(ref[m], ref[n], atol=1e-9)]
    print(f'{n:10s} identical geometry to: {same}')

print('--- bind bone positions per profile (cm if metres) ---')
BONES = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'hand_r',
         'index_01_l', 'thumb_01_l']
for b in BONES:
    row = []
    for n in NAMES:
        bone = sources[n]['bones'].get(b)
        row.append('n/a' if not bone else str(np.round(np.asarray(bone['position'], dtype=float), 4)))
    print(f'{b:14s} ' + ' | '.join(f'{n}:{v}' for n, v in zip(NAMES, row)))

print('--- authored positions vs native reference positions for the same profile ---')
for n in NAMES:
    a = np.asarray(authored[n]['positions'], dtype=float)
    s = np.asarray(sources[n]['positions'], dtype=float)
    if a.shape == s.shape:
        d = np.linalg.norm(a - s, axis=1)
        print(f'{n:10s} equal-shape delta: mean {d.mean():.4f} max {d.max():.4f}')
    else:
        print(f'{n:10s} shapes differ authored {a.shape} native {s.shape}')
