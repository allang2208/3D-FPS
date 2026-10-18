import json,sys
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1]
sys.path.insert(0,str(R/'SourceAssets/LambGripV8_20261017'))
import pose_model as P
m=P.data['roasted_large_lamb'];_,obj,pose,_=P.solve(m,2.75,False)
def pack(t):
    q=t.to_quaternion();return [*t.translation,q.x,q.y,q.z,q.w]
names=[n for n in P.order if any(P.below(n,'hand_'+s) for s in ['l','r'])]
data=dict(hand_in_object={s:pack(obj.inverted()@pose['hand_'+s]) for s in ['l','r']},
    source_bind={n:pack(P.rest[n]) for n in names},source_pose={n:pack(pose[n]) for n in names})
(O/'native_grasp.json').write_text(json.dumps(data,indent=2))
print('LAMB_NATIVE_GRASP_EXPORTED')
