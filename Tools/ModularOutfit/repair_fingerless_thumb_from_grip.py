"""Blend only penetrating reload thumb joints toward the already-clear vertical grip."""
import json,math,copy
from pathlib import Path
import numpy as np
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';C=R/'FingerClearance';O=R/'ClearanceReview';ns={}
exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
baseline=O/'A762_skin_before_thumb_web.json';(R/'SkinCoverage/A762_review.json').write_bytes(baseline.read_bytes())
sd=ns['read'](baseline);gd=ns['read'](R/'Authored/A762.json');s=ns['prepare'](sd,True);g=ns['prepare'](gd)
idle=ns['read'](O/'A762__vertical_A_A762_vertical_idle_poses.json')['poses'][0]['bones'];thumbs=['thumb_01_l','thumb_02_l','thumb_03_l'];parents=['hand_l',*thumbs[:2]]
idle_q={n:Matrix((np.linalg.inv(ns['matrix'](idle[p]))@ns['matrix'](idle[n]))[:3,:3].tolist()).to_quaternion() for n,p in zip(thumbs,parents)}
def thumb_pose(original,alpha):
    out=copy.deepcopy(original)
    for n,p in zip(thumbs,parents):
        local=np.linalg.inv(ns['matrix'](original[p]))@ns['matrix'](original[n]);scale=np.linalg.norm(local[:3,:3],axis=0)
        q=Matrix((local[:3,:3]/scale).tolist()).to_quaternion().slerp(idle_q[n],alpha);local[:3,:3]=np.array(q.to_matrix())*scale
        m=ns['matrix'](out[p])@local;out[n]=dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
    return out
manifest=ns['read'](C/'manifest.json');records={x['asset']:x for x in manifest}
for file in sorted(O.glob('A762__vertical*reload*_poses.json')):
    d=ns['read'](file);cp=C/('A762__'+d['label']+'.json');c=ns['read'](cp);alphas=[];maxbefore=0.;remaining=0.
    for pose in d['poses']:
        before=pose['bones'];best=ns['measure'](s,g,ns['deform'](s,before),ns['deform'](g,before))['max_plane_cross_mm'];maxbefore=max(maxbefore,best);chosen=0.
        # Limit the score to the exposed thumb, so independent finger fixes do
        # not force extra thumb movement.
        hand=s.copy();used=np.array([sum(w for bn,w in sd['weights'][i].items() if bn in thumbs)>.25 for i in s['original_ids']]);hand['t']=s['t'][used[s['t']].any(1)]
        best=ns['measure'](hand,g,ns['deform'](s,before),ns['deform'](g,before))['max_plane_cross_mm']
        if best>.03:
            for a in np.linspace(.125,1,8):
                b=thumb_pose(before,float(a));score=ns['measure'](hand,g,ns['deform'](s,b),ns['deform'](g,b))['max_plane_cross_mm']
                if score<best:best=score;chosen=float(a)
                if score<=.03:break
        alphas.append(chosen);remaining=max(remaining,best)
    times=np.array(c['times']);values=np.array(alphas);envelope=values.copy()
    for i,a in enumerate(values):
        t=np.clip(1-abs(times-times[i])/.20,0,1);envelope=np.maximum(envelope,a*t*t*t*(10+t*(-15+6*t)))
    for n in thumbs:c['corrections'][n]=dict(angles=[],axes=[],axis=[0,0,1])
    for p,a in zip(d['poses'],envelope):
        b=thumb_pose(p['bones'],float(a))
        for n,parent in zip(thumbs,parents):
            before=np.linalg.inv(ns['matrix'](p['bones'][parent]))@ns['matrix'](p['bones'][n]);after=np.linalg.inv(ns['matrix'](b[parent]))@ns['matrix'](b[n])
            delta=np.linalg.inv(before[:3,:3])@after[:3,:3];q=Matrix(delta.tolist()).to_quaternion()
            if q.w<0:q.negate()
            c['corrections'][n]['angles'].append(math.degrees(q.angle));c['corrections'][n]['axes'].append(list(q.axis))
    c['remaining_sample_cross_mm']=remaining;c['max_angle']=max(max(v['angles']) for v in c['corrections'].values());c['thumb_contact_source']='vertical idle thumb, local rotations only'
    cp.write_text(json.dumps(c,indent=2));records[c['asset']].update(remaining_sample_cross_mm=remaining,max_angle=c['max_angle'],thumb_contact_source=c['thumb_contact_source'])
    print('THUMB_GRIP_REFERENCE',d['label'],round(maxbefore,4),round(remaining,5),max(alphas),flush=True)
(C/'manifest.json').write_text(json.dumps(list(records.values()),indent=2))
