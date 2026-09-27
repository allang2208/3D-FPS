"""Item-specific V7 coverage, retaining exposed digits and an opening underlap.
Only produce new sources; never remove faces from the shared naked hand assets.
"""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';REVIEW=R/'ClearanceReview'
OUT=R/'SkinCoverage';OUT.mkdir(exist_ok=True)
manifest=[]
for entry in json.loads((REVIEW/'mesh-manifest.json').read_text()):
    name=entry['profile'];skin=json.loads((REVIEW/(name+'_skin.json')).read_text());g=json.loads((R/'Authored'/(name+'.json')).read_text())
    gp=np.array(g['positions']);gt=np.array(g['triangles']);uv1=np.array(g['uv1']);uv2=np.array(g['uv2'])
    outer=(uv2[:,:,1]==0).all(1);indices=np.unique(gt[outer]);edge=np.zeros(len(gp))
    for k in range(3):edge[gt[outer,k]]=uv1[outer,k,1]
    sp=np.array(skin['positions']);st=np.array(skin['triangles']);distance,near=cKDTree(gp[indices]).query(sp)
    # 1.8 mm along-surface overlap beneath each leather opening preserves the
    # skin silhouette without leaving a second full palm to protrude through LODs.
    covered=(edge[indices[near]]>.18)&(distance<.60)
    delete=np.flatnonzero(covered[st].all(1)&(np.array(skin['triangle_materials'])==2))
    keep=np.ones(len(st),dtype=bool);keep[delete]=False
    candidate=dict(skin);candidate['triangles']=st[keep].tolist();candidate['triangle_materials']=np.array(skin['triangle_materials'])[keep].tolist()
    (OUT/(name+'_review.json')).write_text(json.dumps(candidate,separators=(',',':')))
    recipe=dict(profile=name,source=skin['path'],source_triangles=len(st),delete_triangles=delete.tolist(),underlap_cm=.18)
    (OUT/(name+'.json')).write_text(json.dumps(recipe,indent=2));manifest.append(recipe|{'delete_triangles':len(delete)})
    print('FINGERLESS_SKIN_COVERAGE',name,len(delete),flush=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
