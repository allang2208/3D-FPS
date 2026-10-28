"""Contact check of the dual-kukri clips on the real meshes: kukri vs kukri, and each kukri vs the OTHER arm's skin.

python -I contact_dual.py [DualIdle DualWalk DualRun] [--step=N]
Poses come from author_clips.py (same sampling as the bake); the skin is posed and skinned in Blender
(render_idle.py --skin, V7 FrostArms, the in-game skeleton/bind) and the kukri is a voxel SDF (kukri_sdf.py, 0.1 cm).
Negative = inside.  A kukri's own fist is the accepted grip and is not checked here.
Writes Work/contact_<clip>.json with per-frame minima and the deepest bone.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_clips as A  # noqa: E402
import kukri_sdf as S  # noqa: E402
from dual_rig import DualRig  # noqa: E402
from quick_view import BLENDER  # noqa: E402


def poses_for(D, name, step):
    spec = A.CLIPS[name]
    base = A.load(spec['keys'])
    n = int(round(spec['length'] * A.FPS))
    out = {}
    for i in range(0, n, step):
        world, Kr, Kl, _ = A.pose_at(D, spec, i / A.FPS, base)
        out['%s_%04d' % (name, i)] = (world, Kr, Kl)
    return out


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(A.CLIPS)
    step = next((int(a.split('=')[1]) for a in sys.argv if a.startswith('--step=')), 6)
    D = DualRig()
    work = P / 'Work' / 'contact'
    work.mkdir(parents=True, exist_ok=True)
    for name in names:
        poses = poses_for(D, name, step)
        pj = work / (name + '.json')
        pj.write_text(json.dumps(dict(poses={k: dict(bones={b: t.pack() for b, t in w.items()}, kukri_r=Kr.pack(), kukri_l=Kl.pack())
                                             for k, (w, Kr, Kl) in poses.items()})), encoding='utf-8')
        res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_idle.py'), '--', str(pj), str(work),
                              '--skin', '--norender'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if res.stdout.count('DUAL_PREVIEW') < len(poses):
            print(res.stdout[-2000:], res.stderr[-2000:])
            sys.exit(1)
        rows = []
        for k, (w, Kr, Kl) in poses.items():
            z = np.load(work / (k + '_skin.npz'))
            names_ = [str(s) for s in z['names']]
            bone = np.array([names_[b] if b >= 0 else '' for b in z['bone']])
            side_r = np.char.endswith(bone, '_r')
            side_l = np.char.endswith(bone, '_l')
            dL, iL = S.points_gap(z['X'][side_r], Kl)    # left kukri vs right arm skin
            dR, iR = S.points_gap(z['X'][side_l], Kr)    # right kukri vs left arm skin
            rows.append(dict(frame=k, t=round(int(k.split('_')[-1]) / A.FPS, 3),
                             kukri_kukri=round(min(S.kukri_gap(Kl, Kr), S.kukri_gap(Kr, Kl)), 2),
                             left_kukri_vs_right_arm=round(float(dL.min()), 2), at=str(bone[side_r][iL]),
                             right_kukri_vs_left_arm=round(float(dR.min()), 2), at_l=str(bone[side_l][iR])))
        (P / 'Work' / ('contact_%s.json' % name)).write_text(json.dumps(rows, indent=1), encoding='utf-8')
        worst = {key: min(rows, key=lambda r: r[key]) for key in ('kukri_kukri', 'left_kukri_vs_right_arm', 'right_kukri_vs_left_arm')}
        print(name, json.dumps({k: (v[k], v['t'], v.get('at') if 'right_arm' in k else v.get('at_l') if 'left_arm' in k else None)
                                for k, v in worst.items()}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
