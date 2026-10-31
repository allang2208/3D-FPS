"""Author visible park pockets immediately behind the riverfront building row.
Footprint sightlines are placement constraints, not gameplay / visual acceptance.
"""
from pathlib import Path
import runpy,json,math,random,collections
R=Path(__file__).resolve().parent
globals().update({k:v for k,v in runpy.run_path(str(R/'layout_primitives.py')).items() if not k.startswith('__')})
from shapely.geometry import MultiPoint
from shapely.prepared import prep
old=json.loads((R/'Revisions/BeforeRiverfront20261026/layout.json').read_text(encoding='utf8'))
view=json.loads((R/'riverfront_view.json').read_text(encoding='utf8'));eye=view['eye_metres'][:2]
rng=random.Random(261026)
out.update(revision='riverfront_gaps_20261026',seed=261026,view_origin=view,layout_intent='Fill first-row gaps and the first rear planting band visible from the apartment',zones=[],plants=[],fixtures=[])
out['previous_zone_centers']={z['id']:z['center'] for z in old['zones']}

# Perspective shadow wedges prevent placing new crown centres directly behind
# tall facades. Existing land and footprints still define the support area.
wedges=[]
for shape in building_shapes:
    coords=list(shape.exterior.coords)[:-1];far=[]
    for x,y in coords:
        dx,dy=x-eye[0],y-eye[1];dist=math.hypot(dx,dy);far.append((eye[0]+dx/dist*20000,eye[1]+dy/dist*20000))
    wedges.append(MultiPoint(coords+far).convex_hull)
visible=land.difference(unary_union(wedges));visible_prep=prep(visible)
quay=unary_union([Polygon(z['points']) for z in D['land'] if z['id'].startswith('QUAY')]).buffer(-2)
band=quay.intersection(road.buffer(255)).difference(road.buffer(60)).intersection(box(-1650,500,2850,2400))
band=band.difference(obstacles).buffer(-1).buffer(0)
chosen=[]
def choose_center(desired,radius,region=band,spacing=150):
    safe=region.buffer(-radius)
    for p in chosen:safe=safe.difference(Point(p).buffer(spacing))
    available=safe.intersection(visible.buffer(-2))
    if available.is_empty:raise RuntimeError('No supported visible focal pocket near '+str(desired))
    p=nearest_points(available,Point(desired))[0];chosen.append([p.x,p.y]);return [p.x,p.y]
centers={'P1':choose_center([260,845],28),'P2':choose_center([1470,855],18),'P3':choose_center([-590,1320],31)}
regions={z:Point(c).buffer(94 if z=='P1' else 84).intersection(band) for z,c in centers.items()}
parks=unary_union(list(regions.values()))
regions['P5']=band.intersection(box(650,500,2850,2400)).difference(parks)
regions['P6']=band.intersection(box(-1650,500,650,2400)).difference(parks)
for z,desired in [('P5',[1950,1000]),('P6',[-940,1610])]:centers[z]=choose_center(desired,20,regions[z],70)

all_occupied=[];vegetation_jobs=[];circulation=[]
for zid in ('P1','P2','P3','P5','P6'):
    region=regions[zid];center=centers[zid];zbase=-106.25
    if zid in ('P1','P2','P3'):
        station=min(range(len(D['road'])),key=lambda i:math.dist(D['road'][i],center));entry=route_station(station,24)
        allowed=quay.difference(buildings.buffer(6)).difference(road.buffer(18)).buffer(-2)
        route=find_path(entry,center,allowed)
        paths=region.buffer(-12).boundary.buffer(3).union(Point(center).buffer(24 if zid!='P3' else 29)).union(route.buffer(3.5)).intersection(quay.difference(buildings.buffer(3))).difference(road.buffer(18));anchors=[center]
    else:
        axis=road.offset_curve(-150);paths=axis.buffer(3.5).intersection(region);anchors=[center]
        if zid=='P5':
            for desired in ([2500,1170],[1050,900]):anchors.append(choose_center(desired,16,region,65))
        for p in anchors:
            link=LineString([p,nearest_points(axis,Point(p))[0]])
            paths=paths.union(Point(p).buffer(19)).union(link.buffer(3.5)).intersection(region)
    core=[]
    for p in anchors:
        if zid in ('P1','P2','P5'):
            kind='Fountain' if zid=='P1' else 'Pool';addfixture(kind,[*p,zbase+.2],zid,scale=1 if zid!='P5' else 1.4);core.append(Point(p).buffer(14 if zid=='P1' else 8))
        elif zid=='P3':addfixture('Terraces',[*p,zbase+.2],zid);core.append(box(p[0]-19,p[1]-22,p[0]+19,p[1]+11))
        else:addfixture('Lookout',[*p,zbase+.2],zid);core.append(box(p[0]-7,p[1]-9,p[0]+9,p[1]+6))
        rr=19 if zid=='P1' else (13 if zid in ('P2','P5') else 30)
        for angle in range(0,360,60):
            a=math.radians(angle);q=[p[0]+math.cos(a)*rr,p[1]+math.sin(a)*rr]
            if region.covers(Point(q).buffer(2)):addfixture('Bench',[*q,zbase+.2],zid,angle+90);paths=paths.union(Point(q).buffer(2.2))
    paths=paths.difference(unary_union(circulation));circulation.append(paths)
    lawns=region.difference(paths).difference(unary_union(core))
    vegetation_jobs.append((zid,region,center,lawns))
    polys=[p for p in getattr(region,'geoms',[region]) if p.geom_type=='Polygon']
    out['zones'].append(dict(id=zid,origin=[*center,zbase],center=center,z=zbase,paving_triangles=surfaces(paths),lawn_triangles=surfaces(lawns),boundary=[list(p) for p in max(polys,key=lambda x:x.area).exterior.coords],boundaries=[[list(p) for p in poly.exterior.coords] for poly in polys],water_radius=13 if zid=='P1' else 5.2,anchors=anchors,area_m2=round(region.area,1),road_setback_band_m=[60,255]))

all_paths=unary_union(circulation)
for row in old['plants']:
    if row['zone']=='P4':
        m=M[row['mesh']];radius=max(m['max'][0]-m['min'][0],m['max'][1]-m['min'][1])/200*row['scale'];all_occupied.append((row['p'][:2],radius))
for job_index,(zid,region,center,lawns) in enumerate(vegetation_jobs):
    zbase=-106.25;lawns=lawns.difference(all_paths);paths=circulation[job_index]
    zone=next(z for z in out['zones'] if z['id']==zid);zone['lawn_triangles']=surfaces(lawns)
    plantable=lawns.buffer(-1.5);minx,miny,maxx,maxy=plantable.bounds
    target={'P1':48,'P2':42,'P3':42,'P5':240,'P6':230}[zid];candidates=[]
    for attempt in range(target*140):
        q=[rng.uniform(minx,maxx),rng.uniform(miny,maxy)]
        if visible_prep.covers(Point(q)) and plantable.covers(Point(q).buffer(5)):candidates.append(q)
    candidates.sort(key=lambda q:road.distance(Point(q))*.8+math.dist(q,center)*.06)
    occupied=[]
    for q in candidates:
        key='TreeA' if len(occupied)%4 else 'TreeB';height=rng.uniform(18,25 if zid in ('P1','P2','P3') else 28)
        m=M[key];scale=height/((m['max'][2]-m['min'][2])/100);radius=max(m['max'][0]-m['min'][0],m['max'][1]-m['min'][1])/200*scale
        if not plantable.covers(Point(q).buffer(radius+.7)):continue
        if any(math.dist(q,p)<(radius+r)*.92 for p,r in all_occupied):continue
        if not visible.covers(Point(q).buffer(min(2.5,radius*.3))):continue
        addplant(key,[*q,zbase+.12],height,zid,'RiverfrontGaps');occupied.append((q,radius));all_occupied.append((q,radius))
        if len(occupied)>=target:break
    edge=lawns.intersection(paths.buffer(9)).difference(paths.buffer(1)).intersection(visible)
    low_target={'P1':100,'P2':90,'P3':90,'P5':180,'P6':180}[zid];low=[]
    for attempt in range(low_target*200):
        q=[rng.uniform(minx,maxx),rng.uniform(miny,maxy)]
        if not edge.covers(Point(q).buffer(1.2)):continue
        if any(math.dist(q,p)<2.2 for p in low):continue
        if any(math.dist(q,p)<2 for p,_ in all_occupied):continue
        key=['Shrub','Shrub','GroundA','GroundB','Grass','Flower'][len(low)%6];height={'Shrub':2.2,'GroundA':.55,'GroundB':.3,'Grass':.65,'Flower':.7}[key]*rng.uniform(.88,1.15)
        addplant(key,[*q,zbase+.12],height,zid,'VisibleBorders');low.append(q)
        if len(low)==low_target:break

# Preserve the street furniture and roots already fitted to retained planters.
out['plants'].extend(p for p in old['plants'] if p['zone']=='P4')
out['fixtures'].extend(p for p in old['fixtures'] if p['zone']=='P4')
out['counts']=dict(plants=len(out['plants']),by_zone=dict(collections.Counter(p['zone'] for p in out['plants'])),by_mesh=dict(collections.Counter(p['mesh'] for p in out['plants'])),fixtures=len(out['fixtures']))
out['relocation']=dict(source='user screenshot 2026-10-26',retired_far_land_zones=['P5','P6'],focus='same quay behind first riverfront building row',camera_scope='balcony anchor and source footprint sightlines',acceptance='not run',visible_gap_trees=sum(p['group']=='RiverfrontGaps' for p in out['plants']),near_road_offset_metres=[60,255])
(R/'layout.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('RIVERFRONT_LAYOUT_AUTHORED',out['counts'],out['relocation'],flush=True)
print('RIVERFRONT_FOCAL_CENTERS',centers,flush=True)
