"""Register cast courses to the visible source planes, retaining recesses, windows and tile skirting."""
from collections import defaultdict
from pathlib import Path
import gzip, json, math, random, zlib
import numpy as np
import shapely as sh
from shapely.geometry import Polygon,box
R=Path(__file__).resolve().parent
ORIGIN=np.array([7760,-1400,0.])
inventory=json.loads((R/'done-01.json').read_text('utf8'))
meshes={}
stats=defaultdict(lambda:[0,0.])
def components(shape):
    if shape.is_empty:return []
    if shape.geom_type=='Polygon':return [shape]
    return [p for x in getattr(shape,'geoms',[]) for p in components(x)]
def seed(*key):
    return zlib.crc32('/'.join(map(str,key)).encode())
def input_mesh(row):
    name=row['mesh'].split('.')[-1]
    f=R/'Geometry'/(name+'.json.gz')
    if not f.exists():f=R.parent/'FreightStationUnifiedPatina20261111/Geometry'/f.name
    data=json.load(gzip.open(f))
    v=np.array(data['vertices'])*row['s']; angle=math.radians(row['rot'][2]);c,s=math.cos(angle),math.sin(angle)
    v[:,:2]=v[:,:2]@np.array([[c,s],[-s,c]])
    return (v+row['p'])[np.array(data['indices']).reshape(-1,3)],data.get('slots')
def kind_for(name):
    return {'SM_Station_Walls':'Hall','SM_SW_Walls':'Workshop','SM_Station_Ribs':'Pier',
    'SM_RS_Transit_Shell':'Link','SM_Station_Floors':'Pit','SM_Station_TunnelShell':'Tunnel','SM_Station_TunnelSeals':'Seal'}.get(name)
def allowed(kind,ax,side,p,x,y,z):
    if kind=='Hall':
        if ax==1:return (abs(p-236)<1 and side<0) or (abs(p+3036)<1 and side>0) or (min(abs(p+1184),abs(p+1616))<1 and ((p<-1400)==(side>0))) or (abs(p+3336)<1 and side>0)
        return ((abs(p-6174)<1 and side>0) or (abs(p-10946)<1 and side<0) or (abs(p-5874)<1 and side>0) or (abs(p-7969)<1 and side>0) or (abs(p-8401)<1 and side<0))
    if kind=='Workshop':
        return (ax==0 and min(abs(p-t) for t in [7303,7317,8303,8317])<1) or (ax==1 and min(abs(p-t) for t in [-557,-543,143,157])<1)
    if kind=='Pier':
        return z<736 and ((ax==0 and -3037<y<237) or (ax==1 and ((y< -1400)==(side>0)) and -3036<y<236))
    if kind=='Link':return ax==1 and abs(abs(p+1400)-154)<1 and ((y< -1400)==(side>0))
    if kind=='Pit':return ((ax==1 and abs(abs(p+1400)-525)<1 and ((y<-1400)==(side>0))) or (ax==0 and abs(p-7210)<1 and side>0)) and z<0
    if kind=='Seal':return ax==0 and side<0 and abs(p-11553)<1
    if kind=='Tunnel':
        if ax!=1:return False
        return any(abs(abs(p-cy)-242)<1 and ((p<cy)==(side>0)) for cy in [-1665,-1135])
    return False
def layer(row,portal=False):
    kind=kind_for(row['mesh'].split('.')[-1])
    if not kind:return
    ts,slots=input_mesh(row)
    area=-np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);mag=np.linalg.norm(area,axis=1)
    n=area/np.maximum(1e-12,mag[:,None]);center=ts.mean(1)
    planes=defaultdict(list)
    for i in np.flatnonzero((np.maximum(abs(n[:,0]),abs(n[:,1]))>.9999)&(mag>1.) ):
        if slots is not None and slots[i]!=0:continue
        ax=int(abs(n[i,1])>abs(n[i,0]));side=int(np.sign(n[i,ax]));p=round(float(center[i,ax]),1)
        if allowed(kind,ax,side,p,*center[i]):
            h=1-ax;poly=Polygon(np.round(ts[i][:,[h,2]],2))
            if poly.area>.3:planes[ax,side,p].append(poly)
    for (ax,side,p),triangles in planes.items():
        shape=sh.union_all(triangles,grid_size=.025)
        if portal:
            if ax!=0 or abs(p-10946)>1:continue
            shape=shape.intersection(box(-1e5,0,1e5,159.4))
        if kind=='Workshop' and ax==0 and abs(p-8317)<1:
            shape=shape.difference(box(-550,-5,-114,324))
        if kind in ('Hall','Link') and not portal:
            # Tile tops sit at 159 cm. Lower masonry remains visible only in the rail cutting.
            if kind=='Hall' and ax==0 and abs(p-10946)<1:
                shape=shape.difference(box(-1e5,0,1e5,159.4))
            else:shape=shape.intersection(box(-1e5,159.4,1e5,2000))
        if kind=='Pier':shape=shape.intersection(box(-1e5,.5,1e5,734))
        if shape.is_empty:continue
        a,z0,b,z1=shape.bounds
        base=-180 if kind in ('Tunnel','Seal','Pit') else 0
        # Dado, main cast courses and bridge-height sections follow different form heights.
        levels=[base]
        if kind=='Workshop':levels.extend([85.8,199.7])
        elif kind in ('Hall','Link'):levels.extend([159.4,272.6])
        else:levels.append(base+107)
        while levels[-1]<z1:levels.append(levels[-1]+116.4)
        for j,(za,zb) in enumerate(zip(levels,levels[1:])):
            if zb<=z0 or za>=z1:continue
            row_rng=random.Random(seed(kind,ax,side,p,j))
            width=(141 if kind=='Workshop' else 166) if kind!='Pier' else 152
            offset=row_rng.uniform(0,width)
            start=math.floor((a-offset)/width)*width+offset
            cuts=[start]
            while cuts[-1]<b:cuts.append(cuts[-1]+width*row_rng.uniform(.88,1.16))
            for k,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
                rng=random.Random(seed(kind,ax,side,p,j,k))
                plinth=kind=='Workshop' and j==0
                footprint=box(lo+.32,za+.30,hi-.32,zb-.30)
                if rng.random()<(.16 if kind in ('Pit','Workshop') else .1):
                    # Clip a short, irregular chip out of one vertical arris.
                    zc=rng.uniform(za+8,zb-10); sz=rng.uniform(2.8,8.3);d=rng.uniform(.9,2.8)
                    footprint=footprint.difference(Polygon([(lo-1,zc-sz),(lo+.8,zc-sz*.81),(lo+d,zc-sz*.33),(lo+d*.70,zc+.8),(lo+d*.92,zc+sz*.38),(lo+.45,zc+sz),(lo-1,zc+sz)]))
                parts=components(shape.intersection(footprint))
                for part in parts:
                    if part.area<12:continue
                    sector=math.floor((part.centroid.x-(5800 if ax==1 else -3450))/1200)
                    meshname=f'SM_Finish_{"PortalBase" if portal else kind}_{"X" if ax==0 else "Y"}{sector+1}'
                    depth=rng.uniform(.70,1.05) if not plinth else 2.65
                    if kind=='Pier':depth=.66
                    # Pull the front slightly inward to reveal the real seam and a bevel.
                    for front in components(part.buffer(-.21,join_style='mitre')):
                        if front.area<6:continue
                        dst=meshes.setdefault(meshname,dict(v=[],uv=[],f=[],origin=None))
                        if dst['origin'] is None:
                            dst['origin']=[round(p if ax==0 else part.centroid.x),round(part.centroid.x if ax==0 else p),round(front.centroid.y)]
                        donor_col=rng.randrange(3);donor_row=rng.randrange(2)
                        xi=([-548,-402,-265,-116] if donor_row==0 else [-548,-429,-278,-116])
                        ylo,yhi=xi[donor_col:donor_col+2]
                        zlo,zhi=(86.8,200.) if donor_row==0 else (200.,319.55)
                        hidx=1-ax; surface=side*(1 if ax==0 else -1)
                        def vertex(h,z,d):
                            q=[0.,0.,z];q[ax]=p+side*d;q[hidx]=h
                            dst['v'].append([round(t-o,3) for t,o in zip(q,dst['origin'])])
                            u0=np.clip((h-lo)/(hi-lo),0,1); u0=u0 if surface>0 else 1-u0
                            v0=np.clip((z-za)/(zb-za),0,1)
                            dst['uv'].append([round((ylo+1.45+(yhi-ylo-2.9)*u0+548)/432,6), round((zlo+1.3+(zhi-zlo-2.6)*v0-86.8)/232.75,6)])
                            return len(dst['v'])-1
                        def face(coords,d,sign):
                            pts=list(coords)[:3]
                            cross=(pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])
                            if cross*sign<0:pts.reverse()
                            dst['f'].append([vertex(h,z,d) for h,z in pts])
                        for t in sh.get_parts(sh.constrained_delaunay_triangles(front)):
                            face(t.exterior.coords,depth,surface)
                        bevel=part.difference(front)
                        for t in sh.get_parts(sh.constrained_delaunay_triangles(bevel)):
                            if t.area<.0001:continue
                            pts=list(t.exterior.coords)[:3]
                            if ((pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0]))*surface<0:pts.reverse()
                            dst['f'].append([vertex(h,z,depth if front.boundary.distance(sh.Point(h,z))<.012 else .07) for h,z in pts])
                        stats[kind][0]+=1;stats[kind][1]+=front.area/10000
for row in inventory:
    if row['label'].startswith(('StationLine_AbandonedTransitStation_','StationLine_WarehouseStationLink_','StationWorkshop_0_')):layer(row)
    if row['label']=='StationLine_AbandonedTransitStation_5':layer(row,portal=True)
(R/'panels.json').write_text(json.dumps(meshes,separators=(',',':')),'utf8')
(R/'wall-sections.json').write_text(json.dumps(dict(areas=stats,locations={k:v['origin'] for k,v in meshes.items()}),indent=1),'utf8')
print({k:[v[0],round(v[1])] for k,v in stats.items()})
