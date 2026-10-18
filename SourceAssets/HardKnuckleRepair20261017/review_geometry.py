"""Targeted source/culling/coverage diagnosis requested for this glove repair."""
import json,hashlib
from pathlib import Path
import numpy as np
from geometry import arm_basis,ray_hits
O=Path(__file__).parent
rows=json.loads((O/'author_receipt.json').read_text());inventory=json.loads((O/'inventory.json').read_text())
report=[]
for row in rows:
    d=json.loads(Path(row['file']).read_text());meta=d['hardknuckle_repair']
    # The candidate consists of the exact original body plus the new cuffs.
    original={k:v for k,v in d.items() if k!='hardknuckle_repair'}
    for field in ('positions','weights'):original[field]=original[field][:meta['base_vertices']]
    for field in ('triangles','normals','uv','triangle_materials'):original[field]=original[field][:meta['base_faces']]
    assert hashlib.sha256(json.dumps(original,separators=(',',':')).encode()).hexdigest()==meta['original_sha256']
    pp=np.array(d['positions']);ff=np.array(d['triangles'])[meta['base_faces']:]
    qq=pp[ff];fn=np.cross(qq[:,1]-qq[:,0],qq[:,2]-qq[:,0]);nn=np.array(d['normals'])[meta['base_faces']:].mean(1)
    assert ((fn*nn).sum(1)<0).all(),row['profile']+' cuff front faces'
    checks=[]
    files=sorted({x['file'] for x in inventory if x['profile']==row['profile']})
    for file in files:
        s=json.loads(Path(file).read_text());sp=np.array(s['positions']);sf=np.array(s['triangles']);sm=np.array(s['triangle_materials'])
        for cuff in row['cuffs']:
            w,ax,e1,e2=arm_basis(s['bones'],cuff['side'])
            angles=np.linspace(0,2*np.pi,32,endpoint=False)
            dirs=[e1*np.cos(a)+e2*np.sin(a) for a in angles]
            origins=[w+ax*t for t in np.linspace(cuff['distal_t_cm']+.05,cuff['proximal_t_cm']+.15,9) for _ in dirs]
            directions=dirs*9
            gh=ray_hits(pp,d['triangles'],origins,directions,True)
            sh=ray_hits(sp,sf[sm!=2],origins,directions,True)
            missing=[i for i,(a,b) in enumerate(zip(gh,sh)) if a is None and b is None]
            checks.append(dict(skin=s['source'],side=cuff['side'],rays=len(origins),open_rays=len(missing)))
            if missing:raise RuntimeError('Wrist background opening '+row['profile']+' '+cuff['side']+' '+str(missing[:8]))
    report.append(dict(profile=row['profile'],sha256=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest(),original_glove_unchanged=True,cuff_winding_correct=True,checks=checks))
    print('GLOVE_REVIEW',row['profile'],flush=True)
(O/'geometry_review.json').write_text(json.dumps(dict(profiles=report,game_run=False),indent=2))
print('GLOVE_GEOMETRY_REVIEW_COMPLETE',len(report))
