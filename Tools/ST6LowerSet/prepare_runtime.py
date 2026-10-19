"""Prepare matching cuff variants and restore only the skin exposed above the boots."""
import json,copy
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018'
def write(name,d):(R/(name+'.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def append_patch(dst,patch,material,name):
    names={b['name']:b['index'] for b in dst['bones']};remap={b['index']:names[b['name']] for b in patch['bones']}
    start=len(dst['positions']);dst['positions'].extend(patch['positions']);dst['weights'].extend([[[remap[i],w] for i,w in ws] for ws in patch['weights']])
    for key in ('uv','normals'):dst[key].extend(patch[key])
    dst['triangles'].extend([[v+start for v in face] for face in patch['triangles']]);dst['triangle_materials'].extend([material]*len(patch['triangles']))
    dst['parts'].append(dict(name=name,first_vertex=start,vertices=len(patch['positions']),triangles=len(patch['triangles']),material=material))
waist=json.loads((P/'SourceAssets/SmokeGreyCapri20261004/native_waist.json').read_text())
pants=json.loads((R/'Jason_ST6Trousers_Garment.json').read_text());standard=copy.deepcopy(pants);append_patch(standard,waist,6,'Native_WaistCoverage');write('Jason_ST6Trousers',standard)
boot=json.loads((R/'boot_profile.json').read_text())
def fit(kind):
    q=np.array(pants['positions']);z=q[:,2];grid=np.arange(0,48.5,.5)
    def field(z):
        if kind=='HighBootsFit':
            levels=[4,8,12,18,24,30,36,40];values=[[14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],[4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35],[5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85]]
        elif kind=='ShortBootsFit':
            levels=[4,8,12,18,22,27];values=[[14.8,14.8,14.65,14.1,13.9,13.5],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8],[4.1,4.1,3.9,4.4,4.8,5.5],[4.9,4.9,4.8,5.2,5.6,6.4]]
        else:levels=boot['levels'];values=np.array(boot['fields']).T
        a=[np.interp(z,levels,row) for row in values];a[2]-=.55;a[3]-=.55;return a
    cx,cy,rx,ry=field(z);sign=np.where(q[:,0]>=0,1.,-1.);rad=np.sqrt(((q[:,0]-sign*cx)/rx)**2+((q[:,1]-cy)/ry)**2)
    envelope=np.array([max(1.,rad[abs(z-level)<1.2].max()) if np.any(abs(z-level)<1.2) else 1. for level in grid]);envelope=gaussian_filter1d(maximum_filter1d(envelope,size=7),1.)
    top={'HighBootsFit':43,'ShortBootsFit':28,'ST6BootsFit':33}[kind]
    def deform(points):
        out=points.copy();h=points[:,2];sg=np.where(points[:,0]>=0,1.,-1.);cx,cy,_,_=field(h)
        w=np.clip((top-h)/5,0,1);w=w*w*(3-2*w);scale=1+(np.minimum(1,.96/np.interp(h,grid,envelope))-1)*w
        out[:,0]=sg*cx+(points[:,0]-sg*cx)*scale;out[:,1]=cy+(points[:,1]-cy)*scale;return out
    d=copy.deepcopy(pants);d['positions']=deform(q).tolist();eps=.002;jac=np.empty((len(q),3,3))
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(q+delta)-deform(q-delta))/(2*eps)
    f=np.array(d['triangles']);n=np.einsum('fcij,fcj->fci',np.transpose(np.linalg.inv(jac),(0,2,1))[f],np.array(d['normals']));n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12);d['normals']=n.tolist()
    d['contract']+='; '+kind+' paired cross-section tuck, trim spacing preserved';append_patch(d,waist,6,'Native_WaistCoverage');write('Jason_ST6Trousers_'+kind,d)
for kind in ('ShortBootsFit','HighBootsFit','ST6BootsFit'):fit(kind)

body=json.loads((P/'SourceAssets/ST6Reset20261017/Read/Jason.json').read_text());boots=json.loads((R/'Jason_ST6Boots_Garment.json').read_text());native_ids={b['name']:b['index'] for b in boots['bones']}
patch=dict(positions=[],weights=[],triangles=[],uv=[],normals=[],bones=boots['bones']);lookup={}
def mix(a,b,t):
    w={k:a['w'].get(k,0)*(1-t)+b['w'].get(k,0)*t for k in a['w'].keys()|b['w'].keys()}
    return dict(p=a['p']*(1-t)+b['p']*t,n=a['n']*(1-t)+b['n']*t,uv=a['uv']*(1-t)+b['uv']*t,w=w)
for fi,face in enumerate(body['triangles']):
    if body['triangle_materials'][fi]!=16:continue
    poly=[dict(p=np.array(body['positions'][v]),n=np.array(body['normals'][fi][j]),uv=np.array(body['uv'][fi][j]),w=body['weights'][v]) for j,v in enumerate(face)]
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=a['p'][2]>=27;ib=b['p'][2]>=27
        if ia:out.append(a)
        if ia!=ib:out.append(mix(a,b,(27-a['p'][2])/(b['p'][2]-a['p'][2])))
    for j in range(1,len(out)-1):
        tri=[out[0],out[j],out[j+1]];indices=[]
        for v in tri:
            key=tuple(np.round(v['p'],6))
            if key not in lookup:
                lookup[key]=len(patch['positions']);patch['positions'].append(v['p'].tolist());total=sum(v['w'].values());patch['weights'].append([[native_ids[k],w/total] for k,w in v['w'].items()])
            indices.append(lookup[key])
        if len(set(indices))<3:continue
        patch['triangles'].append(indices);patch['uv'].append([v['uv'].tolist() for v in tri]);patch['normals'].append([(v['n']/max(np.linalg.norm(v['n']),1e-12)).tolist() for v in tri])
append_patch(boots,patch,6,'Native_CalfAboveBoot');write('Jason_ST6Boots',boots)
print('ST6_RUNTIME_VARIANTS_PREPARED',flush=True)
