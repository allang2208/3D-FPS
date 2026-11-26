"""Review whole saved wall assemblies: 3D footprint support, road clearance and joints."""
import json,math
import numpy as np
from shapely.geometry import MultiPoint,Point,LineString
from wall_support_geometry import ROOT,load_mesh,rotate_vertices
from layout_geometry import house_paths

source=ROOT/'SourceAssets/TemperateHillsVillage'
out=source/'WallReview20261114'
plan=json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit=json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
rows=[dict(instance=inst,group=group['name']) for group in plan['yard_walls'] for inst in group['native_instances']]
meshes={}
def slice_points(q,f,height):
    t=q[f];result=[]
    for a,b in ((0,1),(1,2),(2,0)):
        va,vb=t[:,a],t[:,b]
        ok=((va[:,2]<=height)&(vb[:,2]>=height))|((vb[:,2]<=height)&(va[:,2]>=height))
        ok&=abs(vb[:,2]-va[:,2])>1.e-7
        a,b=va[ok],vb[ok]
        if len(a):result.append(a+(b-a)*((height-a[:,2])/(b[:,2]-a[:,2]))[:,None])
    return np.concatenate(result) if result else np.empty((0,3))
paths=[(r['name'],LineString(np.array(r['points'])*100),r['width']*50) for r in plan['roads']]
paths += [('door_'+str(i),LineString(np.array(p)*100),width*50) for i,(p,width) in enumerate(house_paths(plan,kit))]
data=[]
for index,row in enumerate(rows):
    inst=row['instance'];name=inst['mesh'].split('.')[-1]
    if name not in meshes:meshes[name]=load_mesh(name)
    v,f=meshes[name];q=rotate_vertices(v*np.array(inst['scale']),inst['rot'])+np.array(inst['pos'])
    contact=slice_points(q,f,0);above=q[q[:,2]>0]
    base=MultiPoint(contact[:,:2]).convex_hull
    footprint=MultiPoint(above[:,:2]).convex_hull
    t=q[f];norm=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);area=np.linalg.norm(norm,axis=1)
    center=t.mean(axis=1);mask=center[:,2]>0
    surface_center=(center[mask]*area[mask,None]).sum(axis=0)/area[mask].sum()
    center_margin=base.boundary.distance(Point(surface_center[:2]))*(1 if base.covers(Point(surface_center[:2])) else -1)
    nearest=min((footprint.distance(line)-half,name) for name,line,half in paths)
    slices=[MultiPoint(slice_points(q,f,h)[:,:2]).convex_hull for h in (20,50,80)]
    result=dict(index=index,group=row['group'],mesh=name,base_area_cm2=round(base.area,2),
        base_to_footprint_ratio=round(base.area/footprint.area,4),surface_center_margin_cm=round(center_margin,2),
        nearest_route=nearest[1],route_edge_clearance_cm=round(nearest[0],2))
    data.append((result,footprint,base,slices,q,f))
overlaps=[]
for i,a in enumerate(data):
    for j,b in enumerate(data[:i]):
        ratio=0;area=0
        for x,y in zip(a[3],b[3]):
            if x.area<1 or y.area<1:continue
            intersect=x.intersection(y).area
            ratio=max(ratio,intersect/min(x.area,y.area));area=max(area,intersect)
        if ratio>.12:
            overlaps.append(dict(a=j,b=i,ratio=round(ratio,3),area_cm2=round(area,1)))
overlaps.sort(key=lambda r:-r['ratio'])
report=dict(count=len(rows),unsupported_centers=[r[0] for r in data if r[0]['surface_center_margin_cm']<=0],
    route_intrusions=[r[0] for r in data if r[0]['route_edge_clearance_cm']<0],
    min_route_clearance_cm=min(r[0]['route_edge_clearance_cm'] for r in data),
    minimum_base_to_footprint=min(r[0]['base_to_footprint_ratio'] for r in data),
    min_center_support_margin_cm=min(r[0]['surface_center_margin_cm'] for r in data),
    overlaps=overlaps,rows=[r[0] for r in data],
    method='Ground-plane triangle intersections in XY; surface-area center screens support. Joint convex-slice overlaps are candidates requiring visual review, not confirmed solid intersections.')
(out/'deep-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('rows','overlaps')},ensure_ascii=False))
print('OVERLAP_CANDIDATES',json.dumps(overlaps[:12]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(15,10))
for name,line,half in paths:
    p=line.buffer(half)
    ax.fill(*np.array(p.exterior.coords).T/100,color='#d9c6a1',alpha=.8)
for result,footprint,base,_,q,f in data:
    ax.fill(*np.array(footprint.exterior.coords).T/100,color='#657064',alpha=.8)
    ax.plot(*np.array(base.exterior.coords).T/100,color='#174b30',linewidth=.35)
    c=footprint.centroid;ax.text(c.x/100,c.y/100,str(result['index']),fontsize=5)
ax.set_aspect('equal');ax.set_title('Saved wall footprints, ground-contact hulls and reserved routes (m)')
fig.savefig(out/'wall-footprints.png',dpi=160)
