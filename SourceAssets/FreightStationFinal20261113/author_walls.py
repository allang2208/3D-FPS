"""Retain source outlines and base materials; replace only the repetitive cast finish."""
from pathlib import Path
from collections import defaultdict
import json,math,random
import numpy as np
import shapely as sh
from shapely.geometry import Polygon,box
R=Path(__file__).resolve().parent
S=R.parent/'FreightStationSurfaces20261113'
env={'__file__':str(S/'panel_layout.py')}
exec(compile((S/'panel_layout.py').read_text('utf8').split('for row in inventory:')[0],'source_planes','exec'),env)
meshes={};regions={};stats=defaultdict(int)
def polys(shape):
    if shape.is_empty:return []
    if shape.geom_type=='Polygon':return [shape]
    return [p for a in getattr(shape,'geoms',[]) for p in polys(a)]
def make(row,portal=False):
    kind=env['kind_for'](row['mesh'].split('.')[-1])
    if not kind:return
    ts,slots=env['input_mesh'](row)
    normals=-np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);mag=np.linalg.norm(normals,axis=1)
    normals/=np.maximum(mag[:,None],1e-12);center=ts.mean(1);planes=defaultdict(list)
    for i in np.flatnonzero((np.maximum(abs(normals[:,0]),abs(normals[:,1]))>.9999)&(mag>1)):
        if slots is not None and slots[i]!=0:continue
        ax=int(abs(normals[i,1])>abs(normals[i,0]));side=int(np.sign(normals[i,ax]));p=round(float(center[i,ax]),1)
        if env['allowed'](kind,ax,side,p,*center[i]):
            poly=Polygon(np.round(ts[i][:,[1-ax,2]],2))
            if poly.area>.3:planes[ax,side,p].append(poly)
    for (ax,side,p),triangles in planes.items():
        shape=sh.union_all(triangles,grid_size=.025)
        if portal:
            if ax!=0 or abs(p-10946)>1:continue
            shape=shape.intersection(box(-1e5,0,1e5,159.4))
        if kind=='Workshop' and ax==0 and abs(p-8317)<1:shape=shape.difference(box(-550,-5,-114,324))
        if kind in ('Hall','Link') and not portal:
            if kind=='Hall' and ax==0 and abs(p-10946)<1:shape=shape.difference(box(-1e5,0,1e5,159.4))
            else:shape=shape.intersection(box(-1e5,159.4,1e5,2000))
        if kind=='Pier':shape=shape.intersection(box(-1e5,.5,1e5,734))
        if kind=='Hall' and ax==0 and abs(p-6174)<.1 and side==1:shape=shape.difference(box(-3036,159.4,-1558,1170))
        if kind=='Hall' and ax==1 and abs(p+3036)<.1 and side==1:shape=shape.difference(box(6174,159.4,7820,737))
        if shape.is_empty:continue
        a,z0,b,z1=shape.bounds
        key=f'{"PortalBase" if portal else kind}_{"X" if ax==0 else "Y"}_{str(p).replace("-","N").replace(".","p")}_{"P" if side>0 else "N"}'
        origin=[0.,0.,0.];origin[ax]=p;origin[1-ax]=a
        dst=dict(origin=origin,v=[],uv=[],f=[]);name='SM_Finish_'+key
        rng=random.Random(env['seed'](key));cuts=[a]
        # Stop ends correspond to large pours; slender piers stay continuous.
        width=365 if kind=='Hall' else (235 if kind in ('Workshop','Link') else 320)
        if kind=='Pier':width=10000
        while cuts[-1]<b:cuts.append(min(b,cuts[-1]+width*rng.uniform(.83,1.19)))
        count=0
        for j,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
            if kind=='Pier':levels=[z0,z1]
            else:
                levels=[z0]
                height=(296 if kind=='Hall' else 211)*rng.uniform(.91,1.12)
                while levels[-1]+height<z1-65:
                    levels.append(levels[-1]+height);height=(354 if kind=='Hall' else 243)*rng.uniform(.87,1.14)
                levels.append(z1)
            for k,(low,high) in enumerate(zip(levels,levels[1:])):
                inner=shape.intersection(box(lo+.17,low+.16,hi-.17,high-.16))
                depth=.74+rng.uniform(-.08,.08)
                if kind=='Pier':depth=.66
                if kind=='Workshop' and z0<1 and high<100:depth=2.65
                for part in polys(inner):
                    if part.area<12:continue
                    front=part.buffer(-.14,join_style='mitre')
                    if front.is_empty:continue
                    count+=1
                    for surface,isfront in [(front,True),(part.difference(front),False)]:
                        for tri in sh.get_parts(sh.constrained_delaunay_triangles(surface)):
                            if tri.area<.0002:continue
                            pts=list(tri.exterior.coords)[:3];cross=(pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])
                            if cross*side*(1 if ax==0 else -1)<0:pts.reverse()
                            indices=[]
                            for h,z in pts:
                                d=depth if isfront or front.boundary.distance(sh.Point(h,z))<.008 else .07
                                q=[0.,0.,z];q[ax]=side*d;q[1-ax]=h-a
                                indices.append(len(dst['v']));dst['v'].append(q);dst['uv'].append([(h-a)/(b-a),(z-z0)/(z1-z0)])
                            dst['f'].append(indices)
        if dst['f']:
            meshes[name]=dst
            regions[name]=dict(kind=kind,axis=ax,side=side,plane=p,lo=a,hi=b,z0=z0,z1=z1,origin=origin,seed=env['seed'](key),pours=count)
            stats[kind]+=count
for row in env['inventory']:
    if row['label'].startswith(('StationLine_AbandonedTransitStation_','StationLine_WarehouseStationLink_','StationWorkshop_0_')):make(row)
    if row['label']=='StationLine_AbandonedTransitStation_5':make(row,True)
(R/'panels.json').write_text(json.dumps(meshes,separators=(',',':')),'utf8')
(R/'wall-plan.json').write_text(json.dumps(regions,indent=1),'utf8')
print(dict(planes=len(meshes),pours=dict(stats),triangles=sum(len(m['f']) for m in meshes.values())))
