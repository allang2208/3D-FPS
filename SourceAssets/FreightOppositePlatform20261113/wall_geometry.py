"""Clip only the station finish over the two photographed planes. Register new pour sections to the original outline."""
from pathlib import Path
import json,gzip,math
import numpy as np
import shapely as sh
from shapely.geometry import Polygon,box
R=Path(__file__).resolve().parent;S=R.parent/'FreightStationSurfaces20261113'
sectors={'Return':dict(axis=0,plane=6174.,lo=-3036.,hi=-1558.,bottom=159.4,top=1170.),
         'Pipe':dict(axis=1,plane=-3036.,lo=6174.,hi=7820.,bottom=159.4,top=737.)}
prior=json.loads((S/'panels.json').read_text('utf8'));meshes={};changes={}
def blank(origin):return dict(origin=origin,v=[],f=[],uv=[])
def append(group,points):
    start=len(group['v'])
    for p in points:group['v'].append([round(float(k),4) for k in p[:3]]);group['uv'].append([round(float(k),7) for k in p[3:]])
    for i in range(1,len(points)-1):group['f'].append([start,start+i,start+i+1])
def clip(poly,axis,edge,above):
    pts=[]
    if not poly:return []
    for a,b in zip(poly,poly[1:]+poly[:1]):
        va=a[axis]-edge;vb=b[axis]-edge
        if (va>=0)==above:pts.append(a)
        if va*vb<0:pts.append(a+(b-a)*(va/(va-vb)))
    return pts
for n,data in prior.items():
    if 'Finish_Hall_' not in n:continue
    maskcount=0;origin=np.array(data['origin']);dest=blank(data['origin'])
    vertices=np.column_stack((np.array(data['v']),np.array(data['uv'])))
    for f in data['f']:
        pts=list(vertices[f]);rest=[pts]
        for s in sectors.values():
            ax=s['axis'];h=1-ax
            if max(abs(p[ax]+origin[ax]-s['plane']) for p in pts)>1.5:continue
            limit0=s['lo']-origin[h];limit1=s['hi']-origin[h]
            if max(p[h] for p in pts)<limit0 or min(p[h] for p in pts)>limit1:continue
            maskcount+=1
            rest=[p for p in [clip(pts,h,limit0,False),clip(pts,h,limit1,True)] if len(p)>2]
            break
        for poly in rest:append(dest,poly)
    if maskcount:
        key='SM_Trim_'+n[10:];changes[n]=key if dest['f'] else None
        if dest['f']:meshes[key]=dest
inventory=json.loads((S/'done-01.json').read_text('utf8'))
src=next(a for a in inventory if a['label']=='StationLine_AbandonedTransitStation_5')
f=R.parent/'FreightStationUnifiedPatina20261111/Geometry/SM_Station_Walls.json.gz'
g=json.load(gzip.open(f));tri=(np.array(g['vertices'])+src['p'])[np.array(g['indices']).reshape(-1,3)]
def polygons(shape):
    if shape.is_empty:return
    if shape.geom_type=='Polygon':yield shape
    else:
        for child in getattr(shape,'geoms',[]):yield from polygons(child)
# Vertical stop ends mark separate casting/repair campaigns; only some bays have an intermediate horizontal joint.
design={'Return':[(-3036,[159.4,417,714,1180]),(-2702,[159.4,417,714,1180]),(-2280,[159.4,528,1180]),(-1877,[159.4,396,765,1180])],
        'Pipe':[(6174,[159.4,417,737]),(6556,[159.4,417,737]),(6995,[159.4,515,737]),(7468,[159.4,352,737])]}
counts={}
for key,s in sectors.items():
    ax=s['axis'];h=1-ax;p=s['plane'];lo=s['lo'];hi=s['hi'];bottom=s['bottom'];top=s['top']
    pick=tri[np.max(abs(tri[:,:,ax]-p),axis=1)<.08]
    shape=sh.union_all([Polygon(t[:,[h,2]]) for t in pick if Polygon(t[:,[h,2]]).area>.1],grid_size=.015).intersection(box(lo,bottom,hi,top))
    origin=[0.,0.,0.];origin[ax]=p;origin[h]=lo
    dest=blank(origin);count=0
    bays=design[key]
    for i,(a,levels) in enumerate(bays):
        b=bays[i+1][0] if i+1<len(bays) else hi
        for row,(low,high) in enumerate(zip(levels,levels[1:])):
            footprint=shape.intersection(box(a+.19,low+.18,b-.19,high-.18))
            depth=.66+(.10*math.sin(3.14*i+row*4.54))
            for poly in polygons(footprint):
                front=poly.buffer(-.15,join_style='mitre')
                if front.is_empty or front.area<1:continue
                count+=1
                for group,isfront in [(front,True),(poly.difference(front),False)]:
                    for t in sh.get_parts(sh.constrained_delaunay_triangles(group)):
                        if t.area<.0002:continue
                        pts=list(t.exterior.coords)[:3]
                        cross=(pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])
                        if cross*(1 if ax==0 else -1)<0:pts.reverse()
                        corners=[]
                        for u,z in pts:
                            pos=[0.,0.,z];pos[h]=u-lo;pos[ax]=depth if isfront or front.boundary.distance(sh.Point(u,z))<.008 else .08
                            corners.append([*pos,(u-lo)/(hi-lo),(z-bottom)/(top-bottom)])
                        append(dest,corners)
    meshes['SM_Form_'+key]=dest;counts[key]=count
(R/'panels.json').write_text(json.dumps(meshes,separators=(',',':')),'utf8')
(R/'wall-plan.json').write_text(json.dumps(dict(replace=changes,origins={k:v['origin'] for k,v in meshes.items()},sections=sectors,counts=counts),indent=1),'utf8')
print(changes,counts)
