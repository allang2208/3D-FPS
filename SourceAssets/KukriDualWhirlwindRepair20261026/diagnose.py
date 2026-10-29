"""Scoped pose diagnostics for the requested dual-whirlwind repair."""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('author',OUT/'author.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
report={}
for label,data in a.base.rig.DATA.items():
    b=a.c.Body(data);src=json.loads((OUT/(label+'-actions.json')).read_text())
    parts=[np.asarray(src['clips'][r]['frames']) for r in a.ROLES]
    f=np.concatenate([parts[0],parts[1][1:],parts[2][1:]])
    pos,q=b.world(f);n=len(f)
    diff=(R.from_quat(f[:-1,:,3:7].reshape(-1,4)).inv()*R.from_quat(f[1:,:,3:7].reshape(-1,4))).magnitude().reshape(n-1,-1)*180/np.pi
    peak=diff.max(0);row={'evidence':'authored local curves, not runtime output'};report[label]=row
    row['largest_adjacent_rotations']=[{'bone':b.names[i],'degrees':float(peak[i]),'seconds':float(np.argmax(diff[:,i])/120)} for i in np.argsort(peak)[-5:][::-1]]
    row['seam_translation_cm']=[float(np.max(np.linalg.norm(parts[i][-1,:,:3]-parts[i+1][0,:,:3],axis=1))) for i in range(2)]
    row['seam_rotation_degrees']=[float(np.max((R.from_quat(parts[i][-1,:,3:7]).inv()*R.from_quat(parts[i+1][0,:,3:7])).magnitude())*180/np.pi) for i in range(2)]
    for side,sign in [('l',1),('r',-1)]:
        foot,ball,hand,upper,lower=[b.ix[k+'_'+side] for k in ('foot','ball','hand','upperarm','lowerarm')]
        loop=pos[60:146];vec=loop[:,ball]-loop[:,foot];yaw=np.degrees(np.arctan2(sign*vec[:,0],vec[:,1]))
        wrist=(R.from_quat(b.ref[hand,3:7]).inv()*R.from_quat(f[:,hand,3:7])).magnitude()*180/np.pi
        ref=R.from_quat(b.ref[upper,3:7]);cur=R.from_quat(f[:,upper,3:7]);axis=a.c.unit(b.ref[lower,:3])
        swing=a.c.align(np.tile(ref.apply(axis),(n,1)),cur.apply(np.tile(axis,(n,1))))
        twist=np.sum((ref.inv()*swing.inv()*cur).as_rotvec()*axis,axis=1)*180/np.pi
        row[side]={'toe_out_degrees':[float(yaw.min()),float(yaw.max())],
            'foot_side_clearance_cm':float((sign*loop[:,foot,0]).min()),
            'wrist_reference_max_degrees':float(wrist.max()),'wrist_steady_max_degrees':float(wrist[84:146].max()),
            'upperarm_axial_max_degrees':float(np.max(np.abs(twist))),
            'upperarm_axial_steady_degrees':[float(twist[84:146].min()),float(twist[84:146].max())]}
    print(label,json.dumps(row),flush=True)
(OUT/'authored-pose-diagnostics.json').write_text(json.dumps(report,indent=2))
