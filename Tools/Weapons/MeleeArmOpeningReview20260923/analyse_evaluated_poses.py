import json,math
from pathlib import Path
import numpy as np
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'Saved/MeleeArmOpeningReview20260923'
def matrix(t):
    w,x,y,z=t['q'];m=np.eye(4)
    m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(t['s'])
    m[:3,3]=t['p'];return m
data=json.loads((OUT/'evaluated-poses.json').read_text());report={}
for family,clips in data.items():
    base=ROOT/'SourceAssets/MeleeArmOpening20260923'/family
    source=json.loads((base/'source.json').read_text());geo=json.loads((base/'geometry.json').read_text())
    inverse={n:np.linalg.inv(matrix(v)) for n,v in source['rest'].items()}
    rings=[]
    for r in geo['boundaries']:
        if not any('upperarm' in n for n,w in r['weights']):continue
        ids=r['vertices'];p=np.array([[*geo['vertices'][i],1] for i in ids]);groups={}
        for n in {n for i in ids for n in geo['weights'][i]}:
            groups[n]=(p@inverse[n].T,np.array([geo['weights'][i].get(n,0) for i in ids]))
        rings.append(groups)
    report[family]={}
    for clip,streams in clips.items():
        rows=[]
        for a,b in zip(streams['SOURCE'],streams['COMPRESSED']):
            row={'t':a['seconds'],'max_source_compressed_bone_cm':max(float(np.linalg.norm(np.array(a['world'][n]['p'])-b['world'][n]['p'])) for n in a['world'])}
            for label,pose in [('SOURCE',a['world']),('COMPRESSED',b['world'])]:
                for vfov in (75,82):
                    errors=[];tv=math.tan(math.radians(vfov*.5));th=tv*16/9
                    for groups in rings:
                        points=sum((local@matrix(pose[n]).T)[:,:3]*w[:,None] for n,(local,w) in groups.items())
                        x,d,z=points[:,0],-points[:,1],points[:,2]
                        planes=[d,th*d-x,th*d+x,tv*d+z,tv*d-z]
                        errors.append(min(float(np.max(v)) for v in planes))
                    row[f'{label}_v{vfov}_opening_frustum_cm']=max(errors)
            rows.append(row)
        report[family][clip]=rows
(OUT/'pose-analysis.json').write_text(json.dumps(report,indent=2))
for family,clips in report.items():
    for clip,rows in clips.items():
        print(family,clip,'max bone difference',max(r['max_source_compressed_bone_cm'] for r in rows),
            'opening source/comp 75',max(r['SOURCE_v75_opening_frustum_cm'] for r in rows),max(r['COMPRESSED_v75_opening_frustum_cm'] for r in rows))
