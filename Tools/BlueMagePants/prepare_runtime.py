"""Shoe-specific tailoring and complete calf underlayers for the approved V2."""
from common import *
import copy
import numpy as np
from scipy.ndimage import maximum_filter1d,gaussian_filter1d

pants=read(R/'Authored/Jason_BlueMagePants_Garment.json')
waist=read(P/'SourceAssets/SmokeGreyCapri20261004/native_waist.json')
boot=read(P/'SourceAssets/ST6LowerSet20261018/boot_profile.json')

def append_waist(d):
    names={b['name']:b['index'] for b in d['bones']};remap={b['index']:names[b['name']] for b in waist['bones']};start=len(d['positions'])
    d['positions'].extend(waist['positions']);d['weights'].extend([[[remap[i],w] for i,w in ws] for ws in waist['weights']])
    for key in ('uv','normals'):d[key].extend(waist[key])
    d['triangles'].extend([[v+start for v in f] for f in waist['triangles']]);d['triangle_materials'].extend([7]*len(waist['triangles']))
    d['parts'].append(dict(name='Native_WaistCoverage',first_vertex=start,vertices=len(waist['positions']),triangles=len(waist['triangles']),material=7))

def fit(kind):
    q=np.array(pants['positions']);z=q[:,2];grid=np.arange(0,48.5,.5)
    def field(h):
        if kind=='HighBootsFit':
            levels=[4,8,12,18,24,30,36,40];values=[[14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],[4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35],[5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85]]
        elif kind=='ShortBootsFit':
            levels=[4,8,12,18,22,27];values=[[14.8,14.8,14.65,14.1,13.9,13.5],[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8],[4.1,4.1,3.9,4.4,4.8,5.5],[4.9,4.9,4.8,5.2,5.6,6.4]]
        else:levels=boot['levels'];values=np.array(boot['fields']).T
        a=[np.interp(h,levels,row) for row in values];a[2]-=.55;a[3]-=.55;return a
    cx,cy,rx,ry=field(z);sg=np.where(q[:,0]>=0,1.,-1.);rad=np.sqrt(((q[:,0]-sg*cx)/rx)**2+((q[:,1]-cy)/ry)**2)
    envelope=np.array([max(1.,rad[abs(z-level)<1.2].max()) if np.any(abs(z-level)<1.2) else 1. for level in grid]);envelope=gaussian_filter1d(maximum_filter1d(envelope,size=7),1.)
    top={'HighBootsFit':43,'ShortBootsFit':28,'ST6BootsFit':33}[kind]
    def deform(points):
        out=points.copy();h=points[:,2];sg=np.where(points[:,0]>=0,1.,-1.);cx,cy,_,_=field(h);w=np.clip((top-h)/5,0,1);w=w*w*(3-2*w);s=1+(np.minimum(1,.96/np.interp(h,grid,envelope))-1)*w
        out[:,0]=sg*cx+(points[:,0]-sg*cx)*s;out[:,1]=cy+(points[:,1]-cy)*s;return out
    d=copy.deepcopy(pants);d['positions']=deform(q).tolist();eps=.002;jac=np.empty((len(q),3,3))
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(q+delta)-deform(q-delta))/(2*eps)
    f=np.array(d['triangles']);n=np.einsum('fcij,fcj->fci',np.transpose(np.linalg.inv(jac),(0,2,1))[f],np.array(d['normals']));n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12);d['normals']=n.tolist();d['contract']+='; '+kind+' lower-leg tuck, V2 seat and thigh preserved';return d

def underlayer(d):
    cut=max(b['position'][2] for b in d['bones'] if b['name'] in ('calf_l','calf_r'))+2.
    out={k:copy.deepcopy(d[k]) for k in ('source','skeleton','bones','material_slots')};out.update(positions=[],weights=[],triangles=[],normals=[],uv=[],triangle_materials=[],parts=[],contract='Mage suit trousers robe inner layer: complete calf retained through knee plus 2cm; original full trousers unchanged')
    points=np.array(d['positions']);lookup={}
    def vertex(k,p,w):
        if k not in lookup:lookup[k]=len(out['positions']);out['positions'].append(p.tolist());out['weights'].append(w)
        return lookup[k]
    for fi,face in enumerate(d['triangles']):
        poly=[]
        for ci,vi in enumerate(face):
            p=points[vi];uv=np.array(d['uv'][fi][ci]);n=np.array(d['normals'][fi][ci]);ni=(ci+1)%3;vj=face[ni];inside=p[2]<=cut
            if inside:poly.append((vertex(('v',vi),p,d['weights'][vi]),uv,n))
            if inside!=(points[vj,2]<=cut):
                t=(cut-p[2])/(points[vj,2]-p[2]);q=p+(points[vj]-p)*t;a,b=dict(d['weights'][vi]),dict(d['weights'][vj]);w=sorted(((i,a.get(i,0)*(1-t)+b.get(i,0)*t) for i in a.keys()|b.keys()),key=lambda x:-x[1])[:8];total=sum(v for _,v in w);w=[[i,v/total] for i,v in w if v>1e-8];nn=n+(np.array(d['normals'][fi][ni])-n)*t;nn/=max(np.linalg.norm(nn),1e-12)
                poly.append((vertex(('e',*sorted((vi,vj))),q,w),uv+(np.array(d['uv'][fi][ni])-uv)*t,nn))
        for j in range(1,len(poly)-1):
            tri=[poly[0],poly[j],poly[j+1]];out['triangles'].append([v[0] for v in tri]);out['uv'].append([v[1].tolist() for v in tri]);out['normals'].append([v[2].tolist() for v in tri]);out['triangle_materials'].append(d['triangle_materials'][fi])
    return out,cut

rows=[]
for name in VARIANTS:
    d=copy.deepcopy(pants) if name==VARIANTS[0] else fit(name.rsplit('_',1)[1]);append_waist(d);write(R/'Authored'/(name+'.json'),d)
    inner,cut=underlayer(d);write(R/'Authored'/(name+'_RobeInner.json'),inner);rows.append(dict(name=name,full_triangles=len(d['triangles']),inner_triangles=len(inner['triangles']),inner_cut_cm=cut))
write(R/'runtime_preparation.json',dict(rows=rows,runtime_tested=False));print('MAGE_PANTS_RUNTIME_SOURCES_SAVED',flush=True)
