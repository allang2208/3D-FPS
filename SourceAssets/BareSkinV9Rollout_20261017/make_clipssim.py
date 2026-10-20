"""ClipsSim/: the true clip data (ClipsTrue, data-model reader) with the forearm twist redistribution that
anim_fix_raw.py will write already applied -> correctives and pose examples can be authored offline now
and match the animations once they are imported."""
import json
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
from twist_fix import SideTwist

OUT = R / 'ClipsSim'; OUT.mkdir(exist_ok=True)
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text()); tplan = json.loads((R / 'Work' / b / 'twist_plan.json').read_text())
    for ps, vm in plan['viewmodels'].items():
        f = R / 'ClipsTrue' / (ps + '.json')
        if not f.exists(): continue
        cd = json.loads(f.read_text()); bones = cd['bones']; bi = {x: i for i, x in enumerate(bones)}; ref = load_snapshot(vm)['bones']; n = 0
        for path, sides in tplan.get(ps, {}).items():
            c = cd['clips'].get(path)
            if not c or 'frames' not in c: continue
            for s in sides:
                st = SideTwist(ref, s); L = bi['lowerarm_' + s]; H = bi['hand_' + s]
                qL = [Rot.from_quat(fr[L][3:]) for fr in c['frames']]; qH = [Rot.from_quat(fr[H][3:]) for fr in c['frames']]
                for bone, rots in st.twist_locals(st.hand_rolls(qL, qH)).items():
                    if bone not in bi: continue
                    for fi, fr in enumerate(c['frames']): fr[bi[bone]] = fr[bi[bone]][:3] + list((qL[fi] * rots[fi]).as_quat())
            n += 1
        (OUT / (ps + '.json')).write_text(json.dumps(cd, separators=(',', ':')))
        print(b, ps, 'twist applied to', n, 'clips')
