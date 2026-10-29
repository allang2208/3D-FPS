"""Scoped pose/continuity review requested for this sprint attack revision."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a

out={}
for label,data in a.base.rig.DATA.items():
    b=a.c.Body(data)
    f=np.asarray(json.loads((a.OUT/(label+'-actions.json')).read_text())['clips']['Dash']['frames'])
    b.idle=f[0];p,q=b.world(f);joints={}
    for name in ['clavicle_r','upperarm_r','lowerarm_r','hand_r','upperarm_l','lowerarm_l','hand_l']:
        i=b.ix[name];rot=R.from_quat(f[:,i,3:7])
        delta=np.degrees((rot[1:]*rot[:-1].inv()).magnitude());k=int(delta.argmax())
        joints[name]=dict(maximum_local_deg_per_frame=float(delta[k]),time=(k+1)/120,
            maximum_position_cm_per_frame=float(np.linalg.norm(np.diff(p[:,i],axis=0),axis=1).max()))
    rep=json.loads((a.OUT/'authoring.json').read_text())['bodies'][label]
    hi=b.ix['hand_r'];mp,mr=a.base.native.blade_mount(b);hr=R.from_quat(q[:,hi]);br=hr*mr
    model=json.loads((a.ROOT/'SourceAssets/Kukri20261020/model.json').read_text())
    bounds=model['bounds_cm'];pts=np.array([[x,y,z] for x in np.linspace(*bounds['x'],3) for y in np.linspace(*bounds['y'],2) for z in np.linspace(1.,bounds['z'][1],20)])
    blade=np.array([p[k,hi]+hr[k].apply(mp)+br[k].apply(pts) for k in range(len(f))])
    h=b.ix['head'];headq=R.from_quat(q[:,h])*R.from_quat(b.tq[h]).inv()
    centre=p[:,h]+headq.apply(np.tile([0.,1.5,9.],(len(f),1)))*(b.scale/94.)
    clearance=np.array([np.linalg.norm(headq[k].inv().apply(blade[k]-centre[k])/([12.,14.,16.]*np.array(b.scale/94.)),axis=1).min() for k in range(len(f))])
    out[label]=dict(joints=joints,legs=rep['after']['legs'],
        beta_range=[min(rep['elbow_plane_degrees']),max(rep['elbow_plane_degrees'])],
        bank_range=[min(rep['forearm_bank_degrees']),max(rep['forearm_bank_degrees'])],
        blade_head_proxy_minimum=float(clearance.min()),blade_head_proxy_minimum_time=float(np.argmin(clearance)/120.),
        bone_lengths_preserved=bool(np.allclose(f[:,:,:3][:,[b.ix[n] for n in ('lowerarm_r','hand_r','lowerarm_l','hand_l','calf_r','foot_r','calf_l','foot_l')]],f[0,:,:3][[b.ix[n] for n in ('lowerarm_r','hand_r','lowerarm_l','hand_l','calf_r','foot_r','calf_l','foot_l')]])),
        runtime_tested=False,rendered=False)
    print(label,json.dumps(dict(joints=joints,beta=out[label]['beta_range'],bank=out[label]['bank_range'],head_proxy=out[label]['blade_head_proxy_minimum'],
        wrist_span=rep['after']['wrist_chop_vertical_span_cm'],tip_span=rep['after']['tip_chop_vertical_span_cm'],
        cut_blade_direction=rep['after']['keyframes'][4]['blade_tip_direction'])))
(a.OUT/'joint-review.json').write_text(json.dumps(out,indent=2))
