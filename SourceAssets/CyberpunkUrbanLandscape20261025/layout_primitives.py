"""Author clipped ground, connected park walks and deterministic plant placements."""
from pathlib import Path
import sys,json,math,random,heapq,collections
R=Path(__file__).resolve().parent;P=R.parents[1]
sys.path.insert(0,str(R/'PythonDeps'))
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,triangulate,nearest_points
D=json.loads((P/'SourceAssets/CyberpunkUrbanLandscapePlan20261025/design.json').read_text(encoding='utf8'))
I=json.loads((R/'inputs_riverfront.json').read_text(encoding='utf8'));OLD=P/'SourceAssets/CyberpunkApartmentRebuild20261022'
M={v['key']:v for v in I['meshes'].values() if 'key' in v}
def world(p,z=5):return [(-p[0]+10)*1.25,(p[1]-615)*1.25,(z-90)*1.25]
def rotate(p,q):
    x,y,z=p;a,b,c,w=q;t=[2*(b*z-c*y),2*(c*x-a*z),2*(a*y-b*x)]
    return [x+w*t[0]+b*t[2]-c*t[1],y+w*t[1]+c*t[0]-a*t[2],z+w*t[2]+a*t[1]-b*t[0]]
def bounds(c):
    from itertools import product
    t=c['transform'];ps=[[v+t['p'][j] for j,v in enumerate(rotate([p[j]*t['s'][j] for j in range(3)],t['q']))] for p in product(*zip(c['min'],c['max']))]
    return [min(p[j] for p in ps)/100 for j in (0,1)]+[max(p[j] for p in ps)/100 for j in (0,1)]
land=unary_union([Polygon(x['points']) for x in D['land']]).buffer(-1)
building_shapes=[box(b['rect'][0],b['rect'][1],b['rect'][0]+b['rect'][2],b['rect'][1]+b['rect'][3]) for b in D['buildings']]
for label,row in I['actors'].items():
    if label.startswith('AP7_BayLandmark_'):
        for c in row['components']:building_shapes.append(box(*bounds(c)))
buildings=unary_union(building_shapes)
road=LineString(D['road']);road_exclusion=road.buffer(20)
crossings={r['station']:r['point'] for r in D['crossings']}
base_obs=[buildings.buffer(3),road_exclusion]
# Keep the existing frontage slabs and approaches, including their full widths.
rows=json.loads((P/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings']
v18=json.loads((OLD/'RefinementV18/assembly.json').read_text())
def route_station(i,offset=0):
    pts=D['road'];p=pts[i];a=pts[max(0,i-1)];b=pts[min(len(pts)-1,i+1)];dx=b[0]-a[0];dy=b[1]-a[1];l=math.hypot(dx,dy)
    # World X was reflected: inland is the right-hand normal of this world path.
    return [p[0]+dy/l*offset,p[1]-dx/l*offset]
legacy_shrubs=[]
for l in v18['lobbies']:
    b=rows[l['building_index']];x,y=l['source_center'];w=min(27,b['width']*.62)
    corners=[world([x-w/2,y-14.45]),world([x+w/2,y])];base_obs.append(box(min(c[0] for c in corners),min(c[1] for c in corners),max(c[0] for c in corners),max(c[1] for c in corners)).buffer(1))
    a=route_station(l['road_station'],(45-26)*1.25);end=world([x,y-14.45]);base_obs.append(LineString([a,end[:2]]).buffer(4.1))
    for sign in (-1,1):
        for dx in (-.9,0,.9):legacy_shrubs.append(world([x+sign*(w*.5-3)+dx,y-10],6.65))
for p in D['lookouts']:base_obs.append(Point(p).buffer(17))
obstacles=unary_union(base_obs)
free_land=land.difference(obstacles)
rng=random.Random(251026)
out=dict(stage='authored_layout',units='UE world metres',zones=[],plants=[],fixtures=[],source_meshes=M,seed=251026,tests_run=False)

def surfaces(geo):
    return [[list(p) for p in t.exterior.coords[:-1]] for t in triangulate(geo) if geo.covers(t.representative_point()) and t.intersection(geo).area>t.area*.99999]
def addplant(key,p,height,zone,group='Park',yaw=None,container=False):
    m=M[key];h=(m['max'][2]-m['min'][2])/100;s=height/h
    # Preserve the source pivot's X/Y. Only its lowest root/soil contact meets Z.
    out['plants'].append(dict(mesh=key,zone=zone,group=group,p=[p[0],p[1],p[2]-m['min'][2]/100*s],yaw=rng.uniform(0,360) if yaw is None else yaw,scale=s,height=height,root=list(p)))
def addfixture(kind,p,zone,yaw=0,scale=1):out['fixtures'].append(dict(kind=kind,p=list(p),zone=zone,yaw=yaw,scale=scale))
def find_path(start,end,allowed):
    step=4.0;minx,miny,maxx,maxy=allowed.bounds
    def node(p):return (round((p[0]-minx)/step),round((p[1]-miny)/step))
    def pos(k):return [minx+k[0]*step,miny+k[1]*step]
    valid={}
    def okay(k):
        if k not in valid:valid[k]=allowed.covers(Point(pos(k)))
        return valid[k]
    def closest(p):
        k=node(p)
        if okay(k):return k
        for r in range(1,20):
            options=[(k[0]+a,k[1]+b) for a in range(-r,r+1) for b in range(-r,r+1) if abs(a)==r or abs(b)==r]
            options=[q for q in options if okay(q)]
            if options:return min(options,key=lambda q:math.dist(pos(q),p))
        raise RuntimeError('No path endpoint inside supported land')
    a,b=closest(start),closest(end);q=[(0,a)];cost={a:0};prev={}
    while q:
        _,v=heapq.heappop(q)
        if v==b:
            chain=[v]
            while v in prev:v=prev[v];chain.append(v)
            return LineString([start]+[pos(k) for k in reversed(chain)]+[end]).simplify(1,preserve_topology=True)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
            n=(v[0]+dx,v[1]+dy)
            if not okay(n) or not allowed.covers(LineString([pos(v),pos(n)])):continue
            c=cost[v]+math.hypot(dx,dy)
            if c<cost.get(n,1e30):cost[n]=c;prev[n]=v;heapq.heappush(q,(c+math.dist(n,b),n))
    raise RuntimeError('No connected park approach')
