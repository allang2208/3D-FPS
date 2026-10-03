"""Compare authored V7 bare-arm geometry/weights against the native pre-bake source.

Read-only analysis of the authoring JSON. Looks for vertices whose skin weights no
longer match the native reference mesh, or whose position moved far from the native
arm surface - the two ways a "baked default" viewmodel can explode under animation.
"""
import json, sys
from pathlib import Path
import numpy as np

V7 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
V6 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BareArmsFamilyV6')


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def spread(positions, weights, bones):
    """Weighted distance from each vertex to the bones that drive it (reference pose)."""
    out = np.zeros(len(positions))
    for i, w in enumerate(weights):
        p = positions[i]
        total = 0.0
        for name, value in w.items():
            b = bones.get(name)
            if not b:
                return None
            total += value * float(np.linalg.norm(p - np.asarray(b['position'], dtype=float)))
        out[i] = total
    return out


for profile in sys.argv[1:] or ['SVD']:
    src = load(V6 / 'Sources' / f'{profile}.json')
    auth = load(V7 / 'Authored' / f'{profile}.json')
    bones = src['bones']
    native = np.asarray(src['positions'], dtype=float)
    authored = np.asarray(auth['positions'], dtype=float)
    nw = src['weights']
    aw = auth['weights']
    print(f'==== {profile} native {len(native)} authored {len(authored)} '
          f'tri {len(src["triangles"])}->{len(auth["triangles"])} bones {len(bones)}')
    print('   source keys', sorted(src.keys()))
    if len(native) == len(authored):
        delta = np.linalg.norm(authored - native, axis=1) * 1000
        print(f'   authored vs native vertex delta mm: mean {delta.mean():.3f} '
              f'p99 {np.percentile(delta,99):.3f} max {delta.max():.3f} '
              f'over5mm {int((delta>5).sum())} over20mm {int((delta>20).sum())}')
        same = sum(1 for a, b in zip(nw, aw) if a == b)
        print(f'   identical weight dicts {same}/{len(nw)}')
        diff = [(i, nw[i], aw[i]) for i in range(len(nw)) if nw[i] != aw[i]]
        print(f'   differing weight vertices {len(diff)}')
        for i, a, b in diff[:6]:
            print(f'     v{i} native={a} authored={b}')
    sa = spread(authored, aw, bones)
    if sa is not None:
        print(f'   authored weight spread cm: mean {sa.mean()*100:.2f} '
              f'p99 {np.percentile(sa,99)*100:.2f} max {sa.max()*100:.2f} '
              f'over8cm {int((sa>0.08).sum())} over15cm {int((sa>0.15).sum())}')
        worst = np.argsort(-sa)[:8]
        for i in worst:
            print(f'     worst v{i} spread {sa[i]*100:.1f}cm pos '
                  f'{np.round(authored[i]*100,1)} weights {aw[i]}')
    sn = spread(native, nw, bones)
    if sn is not None:
        print(f'   native weight spread cm: mean {sn.mean()*100:.2f} '
              f'p99 {np.percentile(sn,99)*100:.2f} max {sn.max()*100:.2f} '
              f'over8cm {int((sn>0.08).sum())} over15cm {int((sn>0.15).sum())}')
