"""Author clipped ground, connected park walks and deterministic plant placements."""
from pathlib import Path
import sys,json,math,random,heapq,collections
R=Path(__file__).resolve().parent;P=R.parents[1]
sys.path.insert(0,str(R/'PythonDeps'))
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,triangulate,nearest_points
D=json.loads((P/'SourceAssets/CyberpunkUrbanLandscapePlan20261025/design.json').read_text(encoding='utf8'))
I=json.loads((R/'inputs.json').read_text());OLD=P/'SourceAssets/CyberpunkApartmentRebuild20261022'
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

for zd in [z for z in D['zones'] if z['id']!='P4']:
    zid=zd['id'];zbase=-106.25 if zid in ('P1','P2','P3') else -107.5
    region=Polygon(zd['polygon']).intersection(free_land).buffer(-1.5).buffer(0)
    safe=region.buffer(-31 if zid=='P3' else -25)
    desired=Point(zd['center']);center=desired if safe.covers(desired) else nearest_points(safe,desired)[0]
    center=[center.x,center.y];water_r={'P1':13,'P2':5.2,'P3':0,'P5':8,'P6':0}[zid]
    # Paths are clipped to real support and routed around occupied ground.
    if zid in ('P1','P2','P3'):
        ring=region.buffer(-18).boundary.buffer(2.5)
        station={'P1':71,'P2':18,'P3':124}[zid];entry=route_station(station,22)
        # Existing approach slabs remain valid public walking surfaces.
        allowed=land.difference(buildings.buffer(6)).difference(road.buffer(18)).buffer(-3)
        route=find_path(entry,center,allowed)
        paths=ring.union(route.buffer(3,join_style=1)).union(Point(center).buffer(water_r+7 if water_r else 26))
        paths=paths.intersection(land.difference(buildings.buffer(3))).difference(road.buffer(18))
        core_shapes=Point(center).buffer(water_r+3) if water_r else box(center[0]-19,center[1]-22,center[0]+19,center[1]+22)
        anchors=[center]
    else:
        minx,miny,maxx,maxy=region.bounds
        if zid=='P5':
            anchors=[world([x,2960])[:2] for x in (-1700,-700,350)]
            axis=LineString([[minx+10,(miny+maxy)/2],[maxx-10,(miny+maxy)/2]])
        else:
            anchors=[center];axis=LineString([[minx+15,miny+35],[center[0],center[1]],[maxx-15,maxy-35]])
        paths=axis.buffer(3).intersection(region)
        for p in anchors:paths=paths.union(Point(p).buffer(18).intersection(region))
        core_shapes=unary_union([Point(p).buffer(12) for p in anchors])
    lawns=region.difference(paths).difference(core_shapes)
    footprint=Point(center).buffer(water_r+1) if water_r else box(center[0]-19,center[1]-22,center[0]+19,center[1]+22)
    # The continuous slab supports the sealed basin / raised deck; its top is
    # below the fixture floor, never coplanar with the water or terrace surface.
    paving=paths
    zone=dict(id=zid,origin=[center[0],center[1],zbase],center=center,z=zbase,paving_triangles=surfaces(paving),lawn_triangles=surfaces(lawns),boundary=[list(p) for p in max(list(region.geoms),key=lambda g:g.area).exterior.coords] if region.geom_type=='MultiPolygon' else [list(p) for p in region.exterior.coords],water_radius=water_r,anchors=anchors)
    out['zones'].append(zone)
    # Ornament is concentrated at usable path edges; no fixtures are placed on paths.
    for ai,p in enumerate(anchors):
        if zid in ('P1','P2','P5'):addfixture('Fountain' if zid=='P1' else 'Pool',[p[0],p[1],zbase+.2],zid,scale=1 if zid=='P1' else (1 if zid=='P2' else 1.4))
        for angle in range(0,360,60):
            rr=water_r+6 if zid in ('P1','P2') else 22
            a=math.radians(angle);q=[p[0]+math.cos(a)*rr,p[1]+math.sin(a)*rr,zbase+.2]
            if region.covers(Point(q).buffer(2)) and not footprint.contains(Point(q)):
                addfixture('Bench',q,zid,angle+90)
    if zid=='P3':addfixture('Terraces',[*center,zbase+.2],zid)
    if zid=='P6':addfixture('Lookout',[*center,zbase+.2],zid)
    count={'P1':70,'P2':70,'P3':60,'P5':60,'P6':30}[zid]
    occupied=[];plantable=lawns.buffer(-3)
    minx,miny,maxx,maxy=plantable.bounds
    if zid in ('P5','P6'):
        # Clusters have a shared centre and varied crowns; broad gaps remain between them.
        cluster_centers=[]
        for attempt in range(count*150):
            q=[rng.uniform(minx,maxx),rng.uniform(miny,maxy)]
            if not plantable.covers(Point(q).buffer(14)):continue
            if any(math.dist(q,c)<45 for c in cluster_centers):continue
            cluster_centers.append(q)
            if len(cluster_centers)==count:break
        for ci,c in enumerate(cluster_centers):
            for j in range(9 if zid=='P5' else 7):
                a=j*2.399963;rr=0 if j==0 else 10+3.4*math.sqrt(j)
                q=[c[0]+math.cos(a)*rr,c[1]+math.sin(a)*rr]
                key='TreeA' if (j+ci)%3 else 'TreeB';height=rng.uniform(12,19);m=M[key];s=height/((m['max'][2]-m['min'][2])/100);radius=max(m['max'][0]-m['min'][0],m['max'][1]-m['min'][1])/200*s
                if not plantable.covers(Point(q).buffer(radius)):continue
                if any(math.dist(q,p)<(radius+r)*.72 for p,r in occupied):continue
                addplant(key,[*q,zbase+.12],height,zid,f'Cluster{ci:02}');occupied.append((q,radius))
        zone['cluster_centers']=cluster_centers
    else:
        for attempt in range(count*250):
            q=[rng.uniform(minx,maxx),rng.uniform(miny,maxy)];key='TreeA' if len(occupied)%3 else 'TreeB';height=rng.uniform(9,14.5);m=M[key];s=height/((m['max'][2]-m['min'][2])/100);radius=max(m['max'][0]-m['min'][0],m['max'][1]-m['min'][1])/200*s
            if not plantable.covers(Point(q).buffer(radius+1)):continue
            if any(math.dist(q,p)<radius+r+1 for p,r in occupied):continue
            addplant(key,[*q,zbase+.12],height,zid);occupied.append((q,radius))
            if len(occupied)==count:break
    # Low understorey is restricted to edge bands rather than a uniform grass carpet.
    edge=lawns.intersection(paths.buffer(9)).difference(paths.buffer(.8)).difference(core_shapes.buffer(1))
    low_count={'P1':180,'P2':160,'P3':160,'P5':220,'P6':100}[zid]
    accepted=[]
    for attempt in range(low_count*100):
        q=[rng.uniform(minx,maxx),rng.uniform(miny,maxy)]
        if not edge.covers(Point(q).buffer(.65)):continue
        if any(math.dist(q,p)<1.5 for p in accepted):continue
        if any(math.dist(q,p)<1.3 for p,_ in occupied):continue
        key=['Shrub','GroundA','GroundB','Grass','Flower'][len(accepted)%5]
        height={'Shrub':1.15,'GroundA':.38,'GroundB':.14,'Grass':.45,'Flower':.5}[key]*rng.uniform(.8,1.2)
        addplant(key,[*q,zbase+.12],height,zid,'Edge');accepted.append(q)
        if len(accepted)==low_count:break
    zone['area_m2']=round(region.area,1)

# Road tree roots retain their original planter contact; source pivots are compensated.
for i in range(2,len(D['road'])-2,3):
    for side in (9,44):
        p=route_station(i,(side-26)*1.25);key='TreeA' if (i+side)%2 else 'TreeB'
        addplant(key,[*p,(5.75-90)*1.25],rng.uniform(9.5,12.2),'P4','RoadTrees')
for p in legacy_shrubs:addplant('Shrub',p,1.1,'P4','RetainedPlanters')
# The lookouts have rotated local planters on their existing deck.
for i in (12,33,57,78,108,132):
    p=route_station(i,(4-26)*1.25);a=D['road'][max(i-1,0)];b=D['road'][min(i+1,len(D['road'])-1)];l=math.dist(a,b);t=[(b[0]-a[0])/l,(b[1]-a[1])/l];n=[t[1],-t[0]]
    for side in (-1,1):
        for d in (-.6,0,.6):q=[p[0]+t[0]*(side*10.2+d)*1.25+n[0]*(-.4)*1.25,p[1]+t[1]*(side*10.2+d)*1.25+n[1]*(-.4)*1.25,(6.7-90)*1.25];addplant('Shrub',q,1.2,'P4','RetainedPlanters')
# Six street-corner pockets share the same planted / built exclusion geometry.
plant_clearance=[]
for row in out['plants']:
    m=M[row['mesh']];radius=max(m['max'][0]-m['min'][0],m['max'][1]-m['min'][1])/200*row['scale']
    plant_clearance.append(Point(row['p'][:2]).buffer(radius+1))
pocket_land=free_land.difference(unary_union(plant_clearance))
pocket_taken=[]
for j,i in enumerate((18,36,60,81,105,124)):
    p=route_station(i,38);candidate=Point(p).buffer(50)
    spot=pocket_land.intersection(candidate).difference(unary_union(pocket_taken)).buffer(-7)
    if spot.is_empty:continue
    p=nearest_points(spot,Point(p))[0];q=[p.x,p.y,-106.05];pocket_taken.append(p.buffer(10))
    yaw=15+j*17;a=math.radians(yaw)
    def pocket(x,y,z=0):return [q[0]+x*math.cos(a)-y*math.sin(a),q[1]+x*math.sin(a)+y*math.cos(a),q[2]+z]
    addfixture('Shelter',q,'P4',yaw=yaw)
    for side in (-1,1):
        addfixture('Planter',pocket(side*4.5,0),'P4',yaw=yaw)
        addplant('Shrub',pocket(side*4.5,0,.48),.9,'P4','StreetPockets')
    addfixture('Wayfinding',pocket(3.8,3),'P4',yaw=yaw)
    addfixture('Bin',pocket(-3.8,2.8),'P4')
out['counts']=dict(plants=len(out['plants']),by_zone=dict(collections.Counter(p['zone'] for p in out['plants'])),by_mesh=dict(collections.Counter(p['mesh'] for p in out['plants'])),fixtures=len(out['fixtures']))
(R/'layout.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('URBAN_LAYOUT_AUTHORED',out['counts'])
