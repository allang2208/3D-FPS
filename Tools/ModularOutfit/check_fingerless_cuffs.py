"""Check the saved sweater cuff against the new glove in actual saved poses."""
import json
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';O=R/'ClearanceReview';A=R/'ClearanceAfter';ns={}
exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
rows=[]
for name in ('M4','PKM','A762'):
    shirt=ns['read'](A/(name+'_shirt.json'));gp=ns['read'](A/(name+'_glove.json'));p=np.asarray(shirt['positions']);t=np.asarray(shirt['triangles']);centers=p[t].mean(1)
    nearest=np.minimum.reduce([np.linalg.norm(centers-np.asarray(shirt['bones']['hand_'+side]['position']),axis=1) for side in ('l','r')]);shirt['triangles']=t[nearest<12].tolist()
    s=ns['prepare'](shirt);g=ns['prepare'](gp)
    for f in sorted(A.glob(name+'__*_poses.json')):
        d=ns['read'](f);label=d['label'];values=[]
        for pose in d['poses']:
            result=ns['measure'](s,g,ns['deform'](s,pose['bones']),ns['deform'](g,pose['bones']));values.append(result['max_plane_cross_mm'])
        rows.append(dict(profile=name,clip=label,samples=len(values),max_cross_mm=max(values)));print('CUFF_CLEARANCE',name,label,round(max(values),6),flush=True)
(A/'cuff-check.json').write_text(json.dumps(rows,indent=2))
skin=ns['read'](A/'PKM_skin.json');skin['triangles']=[t for t,m in zip(skin['triangles'],skin['triangle_materials']) if m==4]
if skin['triangles']:
    wrist=ns['prepare'](skin);shirt=ns['read'](A/'PKM_shirt.json');p=np.asarray(shirt['positions']);t=np.asarray(shirt['triangles']);center=p[t].mean(1);shirt['triangles']=t[np.linalg.norm(center-np.asarray(shirt['bones']['hand_r']['position']),axis=1)<12].tolist();sleeve=ns['prepare'](shirt);checks=[]
    for label in ('base_idle','base_reload','base_reload_empty'):
        poses=ns['read'](O/('PKM__'+label+'_poses.json'))['poses'];worst=max(ns['measure'](sleeve,wrist,ns['deform'](sleeve,p['bones']),ns['deform'](wrist,p['bones']))['max_plane_cross_mm'] for p in poses)
        checks.append(dict(clip=label,max_cross_mm=worst));print('EXPOSED_WRIST_CLEARANCE',label,worst,flush=True)
    (A/'exposed-wrist-check.json').write_text(json.dumps(checks,indent=2))
