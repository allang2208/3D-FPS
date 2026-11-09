from pathlib import Path
import pickle,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parent;project=root.parents[2]
with (project/'Saved/M249ReloadReview/geometry.pkl').open('rb') as f:d=pickle.load(f)
v=np.array(d['vertices']);lookup=dict(zip(d['used'],d['names']))
dominant=np.array([lookup[max(row,key=lambda x:x[1])[0]] for row in d['weights']])
bind={}
for n,t in zip(d['names'],d['bind']):
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(t[3:7]).as_matrix()*t[7:];m[:3,3]=t[:3];bind[n]=m
def local(n):return (np.c_[v[dominant==n],np.ones(np.sum(dominant==n))]@np.linalg.inv(bind[n]).T)[:,:3]
def vector(p):return 'FVector('+','.join('%.10g'%x for x in p)+')'
centers=[];low=[];high=[]
for prefix in ('','New_'):
 centers.append([local(prefix+'PKM_Belt_%02d'%i).mean(0) for i in range(9)])
 box=local(prefix+'PKM_Box');low.append(box.min(0)-.0015);high.append(box.max(0)+.0015)
text='#pragma once\n#include "CoreMinimal.h"\n// Generated from saved M249 LOD0 centroids in each native bone frame.\nnamespace M249BeltLayout {\n'
text+='inline const FVector Centers[2][9]={\n'+',\n'.join('{'+','.join(vector(p) for p in row)+'}' for row in centers)+'};\n'
text+='inline const FVector BoxMin[2]={'+','.join(vector(p) for p in low)+'};\n'
text+='inline const FVector BoxMax[2]={'+','.join(vector(p) for p in high)+'};\n}\n'
(project/'Source/FPSGAME/Weapons/M249BeltLayout.h').write_text(text)
print('M249_BELT_LAYOUT',len(centers),len(centers[0]))
