"""Check all sampled poses with the complete set of proposed finger deltas applied."""
import json,math,os
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');ns={};exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';O=R/'ClearanceReview';C=R/'FingerClearance';DEST=C/'CorrectedPoses';DEST.mkdir(exist_ok=True)
def rot(axis,angle):
    x,y,z=axis;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]]);a=math.radians(angle);return np.eye(3)+math.sin(a)*K+(1-math.cos(a))*K@K
results=[]
for name in ('PKM','A762','M4'):
    sd=ns['read'](R/'SkinCoverage'/(name+'_review.json'));gd=ns['read'](R/'Authored'/(name+'.json'));s=ns['prepare'](sd,True);g=ns['prepare'](gd)
    for f in sorted(O.glob(name+'__*_poses.json')):
        if os.environ.get('FINGERLESS_CHECK_LABEL') and os.environ['FINGERLESS_CHECK_LABEL'] not in f.name:continue
        d=ns['read'](f);cp=C/(name+'__'+d['label']+'.json');c=ns['read'](cp) if cp.exists() else None;worst=None;rows=[]
        for i,p in enumerate(d['poses']):
            bones=p['bones']
            if c:
                for bn,correction in c['corrections'].items():
                    angle=correction['angles'][i];axis=correction.get('axes',[correction['axis']]*len(c['times']))[i]
                    before=ns['matrix'](bones[bn]);after=before.copy();after[:3,:3]=before[:3,:3]@rot(axis,angle);delta=after@np.linalg.inv(before)
                    prefix,seg,side=bn.split('_');related=[prefix+f'_{j:02d}_'+side for j in range(int(seg),4)]
                    for child in related:
                        m=delta@ns['matrix'](bones[child]);bones[child]=dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
            sp=ns['deform'](s,bones);gp=ns['deform'](g,bones);result=ns['measure'](s,g,sp,gp);rows.append(dict(time=p['time'],depth_mm=result['max_plane_cross_mm'],crossings=result['triangle_pairs']))
            if worst is None or result['max_plane_cross_mm']>worst['depth_mm']:
                worst=dict(time=p['time'],depth_mm=result['max_plane_cross_mm'],pair=result['worst_pair'])
                if result['worst_pair']:
                    a,b=result['worst_pair'];worst['skin_weights']=[sd['weights'][s['original_ids'][v]] for v in s['t'][a]];worst['glove_weights']=[gd['weights'][g['original_ids'][v]] for v in g['t'][b]]
        (DEST/f.name).write_text(json.dumps(d,separators=(',',':')))
        row=dict(profile=name,label=d['label'],asset=d['asset'],worst=worst,samples=rows);results.append(row)
        print('CORRECTED_CONTACT',name,d['label'],round(worst['depth_mm'],5),flush=True)
        (C/'corrected-check.json').write_text(json.dumps(results,indent=2))
