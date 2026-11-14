from pathlib import Path
import json
import numpy as np
R=Path(__file__).resolve().parent
p=json.loads((R/'tile-plan.json').read_text('utf8'));samplers={}
uvs=json.loads((R/'tile-uv.json').read_text('utf8'))
for key,donor in p['donors'].items():
    pts=np.array(donor['corners']);u0,z0=donor['bounds'][:2]
    mat=np.column_stack((pts[:,0]-u0,pts[:,1]-z0,np.ones(3)))
    uv=np.array(uvs[key]);uv[:,1]=1-uv[:,1]
    samplers[key]=np.linalg.solve(mat,uv)
data=dict(v=[],uv=[],f=[],origin=[6174,-3036,0])
for patch in p['patches']:
    ax=patch['axis'];h=1-ax;u0,z0,u1,z1=patch['rect'];i=len(data['v'])
    for u,z in [(u0,z0),(u1,z0),(u1,z1),(u0,z1)]:
        point=[0,0,z];point[ax]=patch['plane']+.24-data['origin'][ax];point[h]=u-data['origin'][h]
        data['v'].append(point);data['uv'].append((np.array([u-u0,z-z0,1])@samplers[str(patch['donor'])]).tolist())
    order=[i,i+1,i+2,i+3] if ax==0 else [i+3,i+2,i+1,i]
    data['f'].extend([[order[0],order[1],order[2]],[order[0],order[2],order[3]]])
(R/'repairs.json').write_text(json.dumps({'SM_CeramicRepairs':data}),'utf8')
