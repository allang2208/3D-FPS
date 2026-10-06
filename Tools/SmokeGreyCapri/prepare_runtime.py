"""Assemble native exposed calf and the tucked high-boot garment variant."""
import copy,json
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
R=Path('D:/FPS3D/FPSGAME/SourceAssets/SmokeGreyCapri20261004')
garment=json.loads((R/'Jason_SmokeGreyCapri_Garment.json').read_text())
calf=json.loads((R/'native_calf.json').read_text())
standard=copy.deepcopy(garment);start=len(standard['positions']);count=0;lookup={}
def interpolate(a,b,t):
    w={}
    for key,fac in [(a,1-t),(b,t)]:
        for bi,x in key['w']:w[bi]=w.get(bi,0)+x*fac
    return dict(p=a['p']*(1-t)+b['p']*t,n=a['n']*(1-t)+b['n']*t,uv=a['uv']*(1-t)+b['uv']*t,w=list(w.items()))
for fi,face in enumerate(calf['triangles']):
    polygon=[dict(p=np.array(calf['positions'][vi]),n=np.array(calf['normals'][fi][ci]),uv=np.array(calf['uv'][fi][ci]),w=calf['weights'][vi]) for ci,vi in enumerate(face)]
    clipped=[]
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        inside_a=a['p'][2]<=33.;inside_b=b['p'][2]<=33.
        if inside_a:clipped.append(a)
        if inside_a!=inside_b:clipped.append(interpolate(a,b,(33.-a['p'][2])/(b['p'][2]-a['p'][2])))
    for k in range(1,len(clipped)-1):
        tri=[clipped[0],clipped[k],clipped[k+1]];indices=[]
        for v in tri:
            key=tuple(np.round(v['p'],7))
            if key not in lookup:
                lookup[key]=len(standard['positions']);standard['positions'].append(v['p'].tolist())
                total=sum(w for _,w in v['w']);standard['weights'].append([[int(bi),float(w/total)] for bi,w in v['w']])
            indices.append(lookup[key])
        if len(set(indices))!=3:continue
        standard['triangles'].append(indices);standard['uv'].append([v['uv'].tolist() for v in tri])
        standard['normals'].append([(v['n']/max(np.linalg.norm(v['n']),1e-12)).tolist() for v in tri])
        standard['triangle_materials'].append(5);count+=1
standard['parts'].append(dict(name='Native_ExposedCalves',first_vertex=start,vertices=len(standard['positions'])-start,triangles=count,material=5))
standard['contract']+='; original native skin UV/weights below 33cm overlaps hem internally; no floating closed calf cap'
(R/'Jason_SmokeGreyCapri.json').write_text(json.dumps(standard,separators=(',',':')),encoding='utf-8')

# Complete cross-section deformation keeps seams and cloth thickness apart.
high=copy.deepcopy(garment);original=np.array(high['positions'])
def profile(z):
    levels=[4,8,12,18,24,30,36,40]
    fields=[[14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],
            [4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35],[5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85]]
    cx,cy,rx,ry=[np.interp(z,levels,x) for x in fields];return cx,cy,rx-.66,ry-.66
cx,cy,rx,ry=profile(original[:,2]);sign=np.where(original[:,0]>=0,1.,-1.)
rad=np.sqrt(((original[:,0]-sign*cx)/rx)**2+((original[:,1]-cy)/ry)**2)
grid=np.arange(0,48.5,.5);env=[]
for z in grid:
    near=rad[np.abs(original[:,2]-z)<1.15];env.append(float(max(1.,near.max())) if len(near) else 1.)
env=gaussian_filter1d(maximum_filter1d(np.array(env),size=7),1.)
def deform(points):
    out=points.copy();z=points[:,2];sg=np.where(points[:,0]>=0,1.,-1.);cx,cy,_,_=profile(z)
    t=np.clip((43-z)/5,0,1);t=t*t*(3-2*t);scale=1+(np.minimum(1,.96/np.interp(z,grid,env))-1)*t
    out[:,0]=sg*cx+(points[:,0]-sg*cx)*scale;out[:,1]=cy+(points[:,1]-cy)*scale;return out
high['positions']=deform(original).tolist();eps=.002;jac=np.empty((len(original),3,3))
for axis in range(3):
    delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(original+delta)-deform(original-delta))/(2*eps)
normal_matrix=np.transpose(np.linalg.inv(jac),(0,2,1));faces=np.array(high['triangles'],int)
ns=np.einsum('fcij,fcj->fci',normal_matrix[faces],np.array(high['normals']));ns/=np.maximum(np.linalg.norm(ns,axis=2,keepdims=True),1e-12)
high['normals']=ns.tolist();high['contract']+='; high boots tuck; fully covered calf skin omitted'
(R/'Jason_SmokeGreyCapri_HighBootsFit.json').write_text(json.dumps(high,separators=(',',':')),encoding='utf-8')
(R/'fit_construction.json').write_text(json.dumps(dict(standard='garment plus native exposed calf',short_boots='standard garment; calf stays native inside shaft',high_boots='tucked hem; no hidden calf draw section',pants_covers=[8,10,12,14,16],native_calf_triangles=count,runtime_tested=False),indent=2),encoding='utf-8')
print('CAPRI_RUNTIME_GEOMETRY_PREPARED',count,flush=True)
