"""Restore source corner normals; author only new neck shading, never move geometry."""
import gzip, json, math
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree

O=Path(__file__).resolve().parent
D=json.load(gzip.open(O/'inputs.json.gz','rt',encoding='utf-8'))
def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-20)
def arrays(lod):
    p=np.asarray(lod['positions'],dtype=np.float64)
    t=np.asarray(lod['triangles'],dtype=np.int64)
    ids=np.asarray(lod['triangle_ids'],dtype=np.int64)
    c=p[t[ids]]
    cross=np.cross(c[:,1]-c[:,0],c[:,2]-c[:,0])
    return p,t,ids,c,unit(cross),np.linalg.norm(cross,axis=1)*.5
def position_key(v):return tuple(np.rint(v*10000).astype(np.int64))
def triangle_key(c):return tuple(sorted(position_key(v) for v in c))

class SourceNormals:
    def __init__(self,lod,overrides=None):
        _,_,self.ids,self.c,self.face,self.area=arrays(lod)
        self.normals=np.array([lod['normals'][str(i)] for i in self.ids],dtype=np.float64)
        if overrides:
            for j,i in enumerate(self.ids):
                if str(i) in overrides:self.normals[j]=overrides[str(i)]
        self.centers=self.c.mean(axis=1)
        self.tree=cKDTree(self.centers)
        self.exact=defaultdict(list)
        for i,c in enumerate(self.c):self.exact[triangle_key(c)].append(i)
    def at_triangle(self,c,face,loose=False):
        for i in self.exact.get(triangle_key(c),[]):
            if np.dot(self.face[i],face)<.98:continue
            order=np.argmin(np.linalg.norm(c[:,None,:]-self.c[i][None,:,:],axis=2),axis=1)
            if np.max(np.linalg.norm(c-self.c[i][order],axis=1))<.001:
                return self.normals[i][order],True
        # Interpolate only on nearby source faces with a compatible orientation.
        # A tiny inward corner offset disambiguates hard-edge samples.
        samples=c*.999+c.mean(axis=0)*.001
        _,choices=self.tree.query(samples,k=24)
        result=[]
        for corner,choices_at_corner in zip(samples,choices):
            best=None
            for i in choices_at_corner:
                if self.area[i]<1e-12 or np.dot(self.face[i],face)<(.80 if loose else .98):continue
                a,b,z=self.c[i];v=b-a;w=z-a;d=corner-a
                vv=np.dot(v,v);vw=np.dot(v,w);ww=np.dot(w,w)
                det=vv*ww-vw*vw
                if det<1e-22:continue
                beta=(np.dot(d,v)*ww-np.dot(d,w)*vw)/det
                gamma=(np.dot(d,w)*vv-np.dot(d,v)*vw)/det
                weights=np.array([1-beta-gamma,beta,gamma])
                clamped=np.maximum(weights,0);clamped/=clamped.sum()
                point=clamped@self.c[i];distance=np.linalg.norm(point-corner)
                if best is None or distance<best[0]:best=(distance,unit(clamped@self.normals[i]))
            if best is None or best[0]>(.25 if loose else .025):return None,False
            result.append(best[1])
        return np.array(result),False

def authored_corners(lod,material=None):
    _,_,ids,c,face,area=arrays(lod)
    mats=np.asarray(lod['material_ids'])[ids]
    selected=np.ones(len(ids),dtype=bool) if material is None else mats==material
    out={str(ids[j]):lod['normals'][str(ids[j])] for j in np.flatnonzero(selected & (area<1e-12))}
    selected &= area>=1e-12
    by_point=defaultdict(list)
    for j in np.flatnonzero(selected):
        for corner in range(3):
            v=unit(c[j,(corner+1)%3]-c[j,corner]);w=unit(c[j,(corner+2)%3]-c[j,corner])
            angle=math.acos(float(np.clip(np.dot(v,w),-1,1)))
            by_point[position_key(c[j,corner])].append((j,corner,angle))
    threshold=math.cos(math.radians(38.))
    for entries in by_point.values():
        js=np.array([x[0] for x in entries]);normals=face[js]
        weights=np.array([x[2] for x in entries])*np.maximum(area[js],1e-14)**.5
        for j,corner,_ in entries:
            compatible=normals@face[j]>=threshold
            n=unit(np.sum(normals[compatible]*weights[compatible,None],axis=0))
            if np.linalg.norm(n)<.5:n=face[j]
            out.setdefault(str(ids[j]),[None,None,None])[corner]=n.tolist()
    return out

donor=SourceNormals(D['meshes']['standard']['lods'][0])
R={'complete':False,'geometry_positions_changed':False,'uv_changed':False,'materials':{},'meshes':{}}
patch={'meshes':{}}
front_reference=None
for key in ('skeleton_front','skeleton_seat'):
    row=D['meshes'][key];target=[];notes=[]
    for lod in row['lods']:
        _,_,ids,c,face,_=arrays(lod)
        normals=authored_corners(lod,0 if key=='skeleton_seat' else None)
        exact=interpolated=0
        if key=='skeleton_front':
            source=donor if lod['index']==0 else front_reference
            for j,ti in enumerate(ids):
                ns,matched=source.at_triangle(c[j],face[j],lod['index']>0)
                if ns is not None:
                    normals[str(ti)]=unit(ns).tolist()
                    exact+=int(matched);interpolated+=int(not matched)
            if lod['index']==0:front_reference=SourceNormals(lod,normals)
        # Source stock material corners are never included in the seat patch.
        target.append({'index':lod['index'],'normals':normals})
        notes.append({'lod':lod['index'],'authored_triangles':len(normals),'exact_source_triangles':exact,
                      'interpolated_source_triangles':interpolated,'local_corner_authoring':len(normals)-exact-interpolated})
        print('M24_CORNERS_AUTHORED',key,notes[-1],flush=True)
    patch['meshes'][key]={'path':row['path'],'source_sha256':row['sha256'],'lods':target}
    R['meshes'][key]=notes

# Restrain artificial edge polish now that the real bevel normals are restored.
for path,row in D['materials'].items():
    if '/StockMetalFinish20261031/' not in path:continue
    steel=path.split('.')[0].endswith('_steel')
    inner=path.split('.')[0].endswith('_interior')
    seat=path.split('.')[0].endswith('_seat')
    if inner:continue
    recipe={'Roughness':.30 if steel else .34,'EdgeHighlight':0. if seat else .018 if steel else .022,
            'GrainRoughness':.003,'MottleRoughness':0.,'MottleColor':0.,'ScratchAmount':0.,'EdgeWear':0.,
            'RainSurfaceResponse':1.,'Metallic':1.}
    R['materials'][path]={'source_sha256':row['sha256'],'scalar':recipe,
                          'color':[.082,.090,.100,1.] if steel else [.032,.035,.038,1.]}
R['complete']=True
with gzip.open(O/'corner_patch.json.gz','wt',encoding='utf-8') as f:json.dump(patch,f,separators=(',',':'))
(O/'authoring.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M24_SURFACE_REFINEMENT_AUTHORED',flush=True)
