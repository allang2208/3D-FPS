"""Author the kukri whirlwind clip "Whirlwind" (one-handed spin, 63/30 s) from whirl_keys.json (fit_whirl.py).

Original design on the sword whirlwind's contract (no reference video).  The runtime owns the -720 deg turn; the clip is
the arms only, on the author phases of fit_whirl.py (ready 15/30, spin 32/30, recover 16/30 s).  The right arm follows the
fitted keys (spline as in author_kukri_clips).  The free left arm (LEFT_KEYS, explicit left arm as in the quick melee,
kukri_rig.left_hand_explicit) comes up while the body coils and stays as a guard fist at the lower left through both
turns, pulsing in and out with the pass and the second drive, then drops below the frame in the recovery.  (A first
pass spread it out to the left edge, palm down and open: in the frame it read as a hand reaching to grab.)

Run:  python author_kukri_whirlwind.py [--preview] [--left]
Output: Clips/Whirlwind.json + its summary in clips.json; --preview renders 15 Hz frames and Work/whirl/sheet_whirl_*.jpg.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

import author_kukri_clips as AC
from author_kukri_quick import LeftArm, FIST_LOCAL
from kmath import mesh_to_cam, qrot

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'whirl'
DATA = json.loads((P / 'whirl_keys.json').read_text('utf-8'))
LENGTH = DATA['length']
READY, SPIN, RECOVER = DATA['ready'], DATA['spin'], DATA['recover']
SPIN_END = READY + SPIN
# t (author s), fist centre (camera cm; None = the hanging rest), elbow pole, palm direction (camera), flex, dev, open.
LEFT_KEYS = [
    (0.000, None, None, None, 0.0, 0.0, 0.0),
    (0.100, None, None, None, 0.0, 0.0, 0.0),
    (0.300, (26.0, -15.0, -18.0), (8.0, -46.0, -40.0), (0.30, 0.70, -0.65), 5.0, 5.0, 0.0),      # comes up low (-0.43, 0.9)
    (READY, (25.0, -14.0, -14.5), (8.0, -46.0, -36.0), (0.10, 0.95, -0.30), 8.0, 4.0, 0.0),      # guard fist (-0.41, 0.76)
    (0.760, (25.5, -13.0, -13.5), (8.0, -46.0, -35.0), (0.10, 0.95, -0.30), 8.0, 4.0, 0.0),
    (1.023, (24.0, -15.0, -15.5), (8.0, -46.0, -37.0), (0.15, 0.93, -0.33), 10.0, 4.0, 0.0),     # pulls in with the pass
    (1.204, (26.0, -12.5, -13.0), (8.0, -46.0, -35.0), (0.10, 0.95, -0.30), 8.0, 4.0, 0.0),      # and goes with the drive
    (1.480, (24.0, -16.0, -19.0), (8.0, -46.0, -40.0), (0.25, 0.85, -0.45), 5.0, 4.0, 0.0),
    (1.680, (21.0, -20.0, -28.0), (6.0, -44.0, -46.0), (0.40, 0.60, -0.70), 0.0, 5.0, 0.0),     # below the frame
    (1.880, None, None, None, 0.0, 0.0, 0.0),
    (LENGTH, None, None, None, 0.0, 0.0, 0.0),
]


def clip_whirl(D):
    from fit_reference import Fitter
    F = Fitter(D.R)
    keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(DATA['keys'])]
    keys.append(dict(t=LENGTH, hold=True, x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))
    left = LeftArm(D.R, LEFT_KEYS, LENGTH)

    def sample(t):
        x = np.array(AC.spline(keys, t, ('x',))['x'], float)
        W, phi, psi, du, de, C = F.unpack(x)
        L, Larm = left.sample(t)
        return dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                    de=float(de), C=np.array(C, float), L=L, LA=Larm)
    return dict(length=LENGTH, loop=False, kind='arm', sample=sample, contact=(READY, SPIN_END), preview_step=1 / 15)


def left_report(R):
    from kukri_rig import ndc
    left = LeftArm(R, LEFT_KEYS, LENGTH)
    K = R.hand_rel.inverse() * R.base['hand_r']
    for i in range(0, 64, 3):
        t = i / 30
        L, Larm = left.sample(t)
        world, d = R.pose(K, left_target_cam=tuple(L), left_arm=Larm)
        l = d['left']
        S, E, W = (mesh_to_cam(world[n].p) for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
        bend = math.degrees(math.acos(np.dot((E - S) / np.linalg.norm(E - S), (W - E) / np.linalg.norm(W - E))))
        print('  t %.3f reach %.2f bend %5.1f skin twist %6.1f wrist %5.1f | elbow ndc %s fist ndc %s twist key %.1f' % (
            t, l['reach'], bend, l['twist_deg'], l['wrist_deg'], np.round(ndc(E), 2),
            np.round(ndc(mesh_to_cam(world['hand_l'].p + qrot(world['hand_l'].q, FIST_LOCAL))), 2), Larm['twist']))


def main():
    if '--left' in sys.argv:
        from kukri_rig import KukriRig
        left_report(KukriRig())
        return
    AC.CLIPS['Whirlwind'] = clip_whirl
    preview = '--preview' in sys.argv
    summary, previews = AC.author(['Whirlwind'], preview)
    clips_path = P / 'clips.json'
    meta = json.loads(clips_path.read_text('utf-8'))
    meta.setdefault('clips', {}).update({k: dict(v, source='author_kukri_whirlwind.py') for k, v in summary.items()})
    clips_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    if previews:
        from preview_tools import write_poses, render, sheet
        WORK.mkdir(parents=True, exist_ok=True)
        write_poses(previews, WORK / 'whirl_previews.json')
        for line in render(WORK / 'whirl_previews.json', WORK / 'previews', 480):
            if 'KUKRI_PREVIEW' not in line:
                print(line)
        names = sorted(previews, key=lambda n: int(n.split('_')[1]))
        for s in range(0, len(names), 12):
            sheet(WORK / 'previews', names[s:s + 12], WORK / ('sheet_whirl_%d.jpg' % (s // 12)), cols=4)


if __name__ == '__main__':
    main()
