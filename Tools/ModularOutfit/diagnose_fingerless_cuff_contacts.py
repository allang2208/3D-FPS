import json
import numpy as np
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';A=R/'ClearanceAfter';O=R/'ClearanceReview';ns={}
exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
for name,part,label in [('PKM','skin','base_idle'),('PKM','skin','base_reload'),('A762','glove','base_reload_empty')]:
    sd=ns['read'](A/(name+'_shirt.json'));gd=ns['read'](A/(name+'_'+part+'.json'))
    p=np.asarray(sd['positions']);t=np.asarray(sd['triangles']);center=p[t].mean(1);distance=np.minimum.reduce([np.linalg.norm(center-np.asarray(sd['bones']['hand_'+side]['position']),axis=1) for side in ('l','r')]);sd['triangles']=t[distance<12].tolist()
    if part=='skin':gd['triangles']=[t for t,m in zip(gd['triangles'],gd['triangle_materials']) if m==4]
    s=ns['prepare'](sd);g=ns['prepare'](gd);d=ns['read'](O/(name+'__'+label+'_poses.json'));worst=None
    for i,p in enumerate(d['poses']):
        m=ns['measure'](s,g,ns['deform'](s,p['bones']),ns['deform'](g,p['bones']))
        if not worst or m['max_plane_cross_mm']>worst[0]:worst=(m['max_plane_cross_mm'],i,m['worst_pair'])
    depth,pi,pair=worst;print('CUFF_DIAG',name,part,label,depth,pi,pair,flush=True)
    for d,prep,fi in [(sd,s,pair[0]),(gd,g,pair[1])]:
        print('CONTACT_VERTICES',[(d['positions'][prep['original_ids'][v]],d['weights'][prep['original_ids'][v]]) for v in prep['t'][fi]],flush=True)
