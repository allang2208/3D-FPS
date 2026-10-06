"""Read the current arm chain to choose the RSH-specific support pose."""
import json, sys, math
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent
S = O.parent
sys.path.insert(0, str(S / 'RSH12InspectGrip20261004'))
from grip_scene import load, pose

rig, data, _, meta = load()
profile = json.loads((S / 'RSH12Foregrips20261004/Profiles/angled.json').read_text())
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
for n in ('clavicle_l','upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l'):
    b = rig.data.bones[n]
    print('REST', n, 'parent', b.parent.name, 'position', list(b.matrix_local.translation), flush=True)
for kind in ('idle','aim','inspect','sprint','quickcombat','speed_0'):
    samples = data['clips'][kind]['samples']
    for sample in samples[:1] if kind in ('idle','aim') else (samples[0],samples[len(samples)//2],samples[-1]):
        p = pose(rig,data,profile,kind,sample)
        a,e,h = (p[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
        v = (h-e).normalized()
        desired = p['hand_l'].to_quaternion() @ rest['hand_l'].to_quaternion().inverted() @ (rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
        axis = (h-a).normalized()
        l1,l2,d = (e-a).length,(h-e).length,(h-a).length
        along = (l1*l1-l2*l2+d*d)/(2*d)
        natural = h-desired*l2-a
        pole = (natural-axis*natural.dot(axis)).normalized()
        best = a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
        print(json.dumps(dict(kind=kind,t=sample['time'],shoulder=list(a),elbow=list(e),wrist=list(h),neutral=list(desired),bend=math.degrees(v.angle(desired)),best_elbow=list(best),best_bend=math.degrees((h-best).angle(desired)),upper_length=l1,lower_length=l2)),flush=True)
