"""Remove the short right-wrist fold overshoot between adjacent clear reload poses."""
import json,numpy as np,math
from pathlib import Path
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';ns={}
exec((P/'Tools/ModularOutfit/solve_fingerless_thumb_cuff_clearance.py').read_text().split('files=')[0],ns)
mx=ns['ns']['matrix'];d=json.loads((R/'ClearanceAfter/A762__base_reload_empty_poses.json').read_text());gd=json.loads((R/'ClearanceAfter/A762_glove.json').read_text());ids={b['index']:n for n,b in gd['bones'].items()};parents={n:ids.get(b['parent']) for n,b in gd['bones'].items()};related=[]
for n in parents:
    bn=n
    while bn in parents:
        if bn=='hand_r':related.append(n);break
        bn=parents[bn]
def local(i):
    bones=d['poses'][i]['bones'];return Matrix((np.linalg.inv(mx(bones['lowerarm_r']))@mx(bones['hand_r']))[:3,:3].tolist()).to_quaternion()
for start,end,blend in [(43,46,a) for a in (.1,.2,.3,.4,.5,.6,.75,1.)]:
    worst=0.;angle=0.
    for i in range(start+1,end):
        bones=d['poses'][i]['bones'];q=local(i).slerp(local(start).slerp(local(end),(i-start)/(end-start)),blend);old=mx(bones['hand_r']);new=old.copy();new[:3,:3]=mx(bones['lowerarm_r'])[:3,:3]@np.asarray(q.to_matrix());delta=new@np.linalg.inv(old);changed=dict(bones)
        for n in related:
            m=delta@mx(bones[n]);changed[n]=dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
        worst=max(worst,ns['evaluate'](changed));qa=math.degrees(local(i).rotation_difference(q).angle);angle=max(angle,min(qa,360-qa))
    print('WRIST_CURVE_PROBE',start,end,blend,worst,angle,flush=True)
