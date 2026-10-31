"""Deterministic production repairs in world metres. No editor/game execution."""
from pathlib import Path
import json,sys,copy,math,collections,itertools
R=Path(__file__).resolve().parent;P=R.parent;A=P/'Audit'
sys.path.insert(0,str(A/'pythonlib'))
import numpy as np,shapely
from shapely.geometry import Point,Polygon,LineString,MultiPoint,box
from shapely.ops import unary_union,nearest_points
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull,cKDTree,HalfspaceIntersection
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
BASE='/Game/NativeNearBank20261028/Repair'
GROUND=-108.57;ROAD_Z=GROUND+.20
S=json.loads((A/'saved_scene.json').read_text());B=S['meshes']
M=json.loads((R/'source_publish_manifest.json').read_text());RAW=json.loads((P/'native_manifest.json').read_text())
CFG=json.loads((P/'native_inputs.json').read_text());D=json.loads((R/'source_legacy_layout.json').read_text())
F=json.loads((A/'findings.json').read_text())
report={};jobs=[];new_rows=[]
def mat(t):return Rotation.from_quat(t['q']).as_matrix()*np.array(t['s'])[None,:]
def world(v,t):return (np.array(v)@mat(t).T+np.array(t['p']))/100
def footprint(mesh,t):
    b=B[mesh];v=world(list(itertools.product(*zip(b['min'],b['max']))),t)
    return MultiPoint(v[:,:2]).convex_hull,float(v[:,2].min()),float(v[:,2].max())
def parts(g):return list(g.geoms) if hasattr(g,'geoms') else [g]
def tr(p):return dict(p=[float(x)*100 for x in p],q=[0,0,0,1],s=[1,1,1])
def row_for(mesh,material,transforms,**kwargs):
    return dict(actor='NBPCG_Repair',component=mesh.rsplit('/',1)[-1],mesh=mesh+'.'+mesh.rsplit('/',1)[-1],materials=[material],transforms=transforms,custom_stride=0,**kwargs)
ASPHALT='/CitySamplePCG/Materials/Roads/M_Asphalt_Master_Inst.M_Asphalt_Master_Inst'
HIDDEN_MAT='/Game/Props/CyberpunkNearBank20261028/Materials/M_NB_Asphalt.M_NB_Asphalt'

# Two attached buildings are scaled as a single block, keeping every module,
# rooftop assembly and texture attribute together. North edge/ground stay fixed.
envelopes=json.loads((A/'building_envelopes.json').read_text())
secondary=[x['building'] for x in envelopes if 145<(x['min'][0]+x['max'][0])/2<295 and -501<(x['min'][1]+x['max'][1])/2<-395]
BLOCKS=[dict(actors=['Building_4','Building_5'],bounds=[310,-501,466,-395],anchor=[387.9104202626816,-398.896455078125,-108.57],scale=.875),dict(actors=secondary,bounds=[145,-501,295,-395],anchor=[220,-398.896455078125,-108.57],scale=.90)]
def in_block(p,b):return b['bounds'][0]<=p[0]<=b['bounds'][2] and b['bounds'][1]<=p[1]<=b['bounds'][3]
def resize_point(p,b):return np.array(b['anchor'])+(np.array(p)-b['anchor'])*b['scale']
changed_buildings=changed_roof_details=0
for row in M['rows']:
    for t in row['transforms']:
        p=np.array(t['p'])/100
        for b in BLOCKS:
            owned=row['actor'] in b['actors']
            roof=row['actor']=='NBPCG_Production' and in_block(p,b) and p[2]>GROUND+5
            if owned or roof:
                t['p']=(resize_point(p,b)*100).tolist();t['s']=[float(x)*b['scale'] for x in t['s']]
                changed_buildings+=owned;changed_roof_details+=roof;break
report['building_group_scale']=dict(blocks=BLOCKS,building_instances=changed_buildings,roof_detail_instances=changed_roof_details)
surfaces={}
for name in ['BuildingPads','RoofSurfaces']:
    path=f'/Game/NativeNearBank20261028/Meshes/{name}.{name}';b=B[path]
    v=np.asarray(b['vertices'],dtype=float)/100
    changed=0
    for block in BLOCKS:
        lo=block['bounds'];mask=(v[:,0]>=lo[0])&(v[:,0]<=lo[2])&(v[:,1]>=lo[1])&(v[:,1]<=lo[3]);changed+=int(mask.sum())
        anchor=np.array(block['anchor']);v[mask]=anchor+(v[mask]-anchor)*block['scale']
    surfaces[name]=(v,np.array(b['triangles'],dtype=int))
    jobs.append(dict(kind='edit_vertices',asset=path,vertices_cm=(v*100).tolist(),changed_vertices=changed))
pad_v,pad_t=surfaces['BuildingPads'];pads=unary_union(shapely.polygons(pad_v[pad_t][:,:,:2]))
park=shapely.from_wkb((A/'park.wkb').read_bytes())
walk=shapely.from_wkb((A/'sidewalk.wkb').read_bytes())
lane=shapely.from_wkb((A/'lane.wkb').read_bytes())
oldroad=shapely.from_wkb((A/'road.wkb').read_bytes())
junctions=shapely.from_wkb((A/'junction.wkb').read_bytes())
keep=next(x for x in CFG['inputs'] if x['tag']=='NBPCG_Exclusion');keep=Polygon(np.array(keep['points'])[:,:2]/100)
guides=[];cores=[];corridors=[];parking_candidates=[]
for x in CFG['inputs']:
    if x['tag'] not in ['NBPCG_Local','NBPCG_Collector','NBPCG_Artery']:continue
    pts=np.array(x['points'])[:,:2]/100
    if x['closed']:pts=np.vstack([pts,pts[0]])
    l=LineString(pts);kind=x['tag'].split('_')[-1].lower();width=CFG['road_width_cm'][kind]/100
    guides.append(l);cores.append(l.buffer({'local':3.0,'collector':6.0,'artery':8.0}[kind],join_style=1));corridors.append(l.buffer(width/2,join_style=1))
    for d in np.arange(8,l.length-8,7.5):
        p=np.array(l.interpolate(d).coords[0]);v=np.array(l.interpolate(d+.1).coords[0])-np.array(l.interpolate(d-.1).coords[0]);v/=np.linalg.norm(v);normal=np.array([-v[1],v[0]])
        for side in [-1,1]:
            xy=p+normal*side*(width/2-2.6);yaw=math.atan2(v[1],v[0])+(math.pi if side>0 else 0)
            parking_candidates.append(dict(p=[*list(xy*100),ROAD_Z*100],q=[0,0,math.sin(yaw/2),math.cos(yaw/2)],s=[1,1,1]))
guide=unary_union(guides);core=unary_union(cores)
road=unary_union([oldroad,*corridors]).difference(keep)
report['repaired_building_pad_road_overlap_m2']=pads.intersection(road).area
if report['repaired_building_pad_road_overlap_m2']>.01:
    print('PAD_OVERLAP',report['repaired_building_pad_road_overlap_m2'],'old road',pads.intersection(oldroad).area,'pieces',[(g.area,g.bounds) for g in parts(pads.intersection(road)) if g.area>.01],flush=True)
    raise RuntimeError('Building retreat still intersects road')

# Relocate legacy trees into actual park ground, preserving species/scale/count.
bad={(x['actor'],x['component'],x['index']) for x in F['retained_furnishing_conflicts'] if x['tree']}
legacy=[];native_tree_positions=[]
for row in S['rows']:
    if row['native'] and 'BlackAlder' in row['mesh']:
        native_tree_positions += [np.array(t['p'])[:2]/100 for t in row['transforms']]
    if row['actor'].startswith('NB28_Cell') and any(k in row['mesh'] for k in ['Tree','Aspen']):
        for i,t in enumerate(row['transforms']):legacy.append(dict(row=row,index=i,t=copy.deepcopy(t),bad=(row['actor'],row['component'],i) in bad))
occupied=native_tree_positions+[np.array(x['t']['p'])[:2]/100 for x in legacy if not x['bad']]
inside=park.buffer(-6);shapely.prepare(inside)
lo=inside.bounds;candidates=[]
for j,y in enumerate(np.arange(lo[1]+2,lo[3],7.5)):
    for x in np.arange(lo[0]+2+(j%2)*3.75,lo[2],7.5):
        if shapely.contains_xy(inside,x,y):candidates.append(np.array([x,y]))
candidates=np.array(candidates);moves=[]
layout_pos=np.array([x['p'][:2] for x in D['plants']]);layout_tree=cKDTree(layout_pos)
park_z=next(np.asarray(b['vertices'])[:,2].max()/100 for p,b in B.items() if '/Meshes/ParkGround.' in p)
for item in legacy:
    if not item['bad']:continue
    old=np.array(item['t']['p'])/100
    target=None
    for idx in np.argsort(np.linalg.norm(candidates-old[:2],axis=1)):
        p=candidates[idx]
        if min(np.linalg.norm(p-q) for q in occupied)>=8.0:target=p;break
    if target is None:raise RuntimeError('Insufficient safe park tree positions')
    new=np.array([*target,park_z-.10]);occupied.append(target)
    dist,index=layout_tree.query(old[:2])
    if dist>.005 or D['plants'][int(index)]['mesh']!='TreeB':raise RuntimeError('Legacy layout differs from formal snapshot')
    D['plants'][int(index)]['p']=new.tolist();item['t']['p']=(new*100).tolist()
    moves.append(dict(actor=item['row']['actor'],component=item['row']['component'],index=item['index'],old_cm=(old*100).tolist(),new_cm=(new*100).tolist(),layout_index=int(index)))
report['legacy_tree_moves']=moves

# Remove coincident wall copies and road-only fixtures on disconnected outer edges.
seen=set();dedup=0;removed=collections.Counter()
for row in M['rows']:
    output=[];mesh=row['mesh']
    for t in row['transforms']:
        if 'SM_StreetLamp_A_Pole_Large' in mesh and np.linalg.norm(np.array(t['p'][:2])-[46185.592903357596,-49904.443989009014])<.1:
            removed[mesh]+=1;continue
        key=(mesh,tuple(row['materials']),tuple(round(x,2) for x in t['p']),tuple(round(x,4) for x in t['q']),tuple(round(x,4) for x in t['s']),tuple(t.get('custom',[])))
        if key in seen:dedup+=1;continue
        seen.add(key)
        if any(k in mesh for k in ['Parking_Meter','Road_Sign','SM_Painted_Parking_Line']) and Point(np.array(t['p'])[:2]/100).distance(road)>8:
            removed[mesh]+=1;continue
        if 'SM_Painted_Parking_Line' in mesh:t['p'][2]=(ROAD_Z+.003)*100
        output.append(t)
    row['transforms']=output
report['duplicate_instances_removed']=dedup;report['disconnected_parking_fixtures_removed']=dict(removed)
levelled=0
for row in M['rows']:
    mesh=row['mesh']
    if 'SM_Lane_Car_' in mesh or 'SM_Lane_Divider_' in mesh:
        for t in row['transforms']:
            top=ROAD_Z+(0.04 if 'SM_Lane_Divider_' in mesh else 0)
            t['p'][2]=top*100-B[mesh]['max'][2]*t['s'][2];levelled+=1
    elif 'SM_White_Line' in mesh or 'SM_Yellow_Line' in mesh:
        for t in row['transforms']:t['p'][2]=(ROAD_Z+.004)*100
report['road_tiles_levelled']=levelled

# Static street props use their real lower geometry for mutual clearance.
obstacles=[]
for row in M['rows']:
    mesh=row['mesh']
    if not any(k in mesh for k in ['StreetLamp','Parking_Meter','Road_Sign','Hydrant','Mailbox','BlackAlder']):continue
    b=B[mesh]
    if 'vertices' in b:
        vv=np.array(b['vertices']);vv=vv[(vv[:,2]>=b['min'][2]-.1)&(vv[:,2]<=b['min'][2]+300)]
    else:vv=None
    for t in row['transforms']:
        if 'BlackAlder' in mesh:g=Point(np.array(t['p'])[:2]/100).buffer(.4)
        elif vv is not None and len(vv)>2:g=MultiPoint(world(vv,t)[:,:2]).convex_hull
        else:g=footprint(mesh,t)[0]
        obstacles.append(g.buffer(.25))
obstacles += [Point(np.array(x['t']['p'])[:2]/100).buffer(.45) for x in legacy]
obstacles.append(pads.buffer(.5));obstacle_tree=shapely.STRtree(obstacles)
forbidden=unary_union([walk.buffer(.04),core,junctions.buffer(6),keep.buffer(1)])
parking_domain=road.buffer(3).difference(forbidden).difference(pads.buffer(.5))
shapely.prepare(parking_domain)
pool=[t for row in RAW['rows'] if '/Vehicle/' in row['mesh'] for t in row['transforms'] if Point(np.array(t['p'])[:2]/100).distance(road)<6]
pool_points=np.array([t['p'][:2] for t in pool])/100
vehicle_rows=[row for row in M['rows'] if '/Vehicle/' in row['mesh']]
vehicles=[(row,i,copy.deepcopy(t)) for row in vehicle_rows for i,t in enumerate(row['transforms'])]
car_grid=collections.defaultdict(list);placed=[];pending=[];car_changes=[]
def space_free(poly):
    for hit in obstacle_tree.query(poly,predicate='intersects'):
        if poly.intersection(obstacles[hit]).area>1e-6:return False
    b=poly.bounds
    for ix in range(math.floor((b[0]-2)/10),math.floor((b[2]+2)/10)+1):
        for iy in range(math.floor((b[1]-2)/10),math.floor((b[3]+2)/10)+1):
            if any(poly.distance(q)<1.1 for q in car_grid[(ix,iy)]):return False
    return True
def commit_car(poly):
    b=poly.bounds
    for ix in range(math.floor(b[0]/10),math.floor(b[2]/10)+1):
        for iy in range(math.floor(b[1]/10),math.floor(b[3]/10)+1):car_grid[(ix,iy)].append(poly)
def try_pose(mesh,source):
    p=np.array(source['p'])[:2]/100;near=np.array(nearest_points(Point(p),guide)[1].coords[0]);delta=near-p
    n=delta/max(np.linalg.norm(delta),.001);tangent=np.array([-n[1],n[0]])
    for inward in [0,.4,.8,1.2,1.6,2.0,2.4,2.8,3.2,3.6,4.0]:
        for along in [0,-.75,.75,-1.5,1.5]:
            t=copy.deepcopy(source);xy=p+n*inward+tangent*along;t['p'][:2]=(xy*100).tolist()
            poly,z0,z1=footprint(mesh,t)
            if not parking_domain.covers(poly.buffer(.10)):continue
            if not space_free(poly):continue
            t['p'][2]+=(ROAD_Z-z0)*100
            commit_car(poly);return t,poly
    return None
for row,index,old in vehicles:
    found=try_pose(row['mesh'],old)
    if found:
        row['transforms'][index]=found[0];placed.append((row,index,found[0],found[1]));car_changes.append(dict(mesh=row['mesh'],old=old,new=found[0]))
    else:pending.append((row,index,old))
print('PARKING_INITIAL',len(placed),'pending',len(pending),flush=True)
removed_cars=[];exhausted=set();remove_indexes=collections.defaultdict(set)
valid_slots={}
for mesh in {r['mesh'] for r,_,_ in pending}:
    slots=[]
    for source in parking_candidates:
        poly,z0,z1=footprint(mesh,source)
        if parking_domain.covers(poly.buffer(.10)) and not len(obstacle_tree.query(poly,predicate='intersects')):
            t=copy.deepcopy(source);t['p'][2]+=(ROAD_Z-z0)*100;slots.append((t,poly))
    valid_slots[mesh]=slots
print('SAFE_PARKING_SLOTS',{k.rsplit('/',1)[-1]:len(v) for k,v in valid_slots.items()},flush=True)
for row,index,old in pending:
    if row['mesh'] in exhausted:
        removed_cars.append(dict(mesh=row['mesh'],old=old));remove_indexes[id(row)].add(index);continue
    slots=valid_slots[row['mesh']];order=sorted(range(len(slots)),key=lambda i:sum((slots[i][0]['p'][j]-old['p'][j])**2 for j in [0,1]));found=None
    for ci in order:
        t,poly=slots[ci]
        if space_free(poly):
            found=(copy.deepcopy(t),poly);commit_car(poly);break
    if not found:
        exhausted.add(row['mesh']);removed_cars.append(dict(mesh=row['mesh'],old=old));remove_indexes[id(row)].add(index);continue
    row['transforms'][index]=found[0];placed.append((row,index,found[0],found[1]));car_changes.append(dict(mesh=row['mesh'],old=old,new=found[0]))
report['parked_vehicles']=len(placed);report['vehicles_relocated_xy']=sum(np.linalg.norm(np.array(x['new']['p'])[:2]-x['old']['p'][:2])>.1 for x in car_changes)
for row in vehicle_rows:row['transforms']=[t for i,t in enumerate(row['transforms']) if i not in remove_indexes[id(row)]]
report['vehicles_removed_no_safe_parking_space']=len(removed_cars)
(R/'removed_cars.json').write_text(json.dumps(removed_cars,separators=(',',':')))
report['car_clearance_cm']=dict(street_props=25,other_vehicles=110,walk=14)
(R/'vehicle_moves.json').write_text(json.dumps(car_changes,separators=(',',':')))
print('REPAIRED_LAYOUT',len(placed),'cars',len(moves),'trees',dedup,'duplicates',flush=True)

# Small generated meshes are saved in spatial cells. Source high-detail visuals
# remain intact; hidden collision meshes use bounded static geometry.
def add_mesh(name,verts,triangles,origin,material=HIDDEN_MAT,hidden=True,collision=True):
    mesh=BASE+('/Collision/' if hidden else '/Meshes/')+name
    vv=np.asarray(verts);tt=np.asarray(triangles,dtype=int)
    if not len(tt):return
    jobs.append(dict(kind='create',asset=mesh,vertices_cm=((vv-np.array(origin))*100).tolist(),triangles=tt.tolist(),collision=collision,hidden=hidden,material=material))
    new_rows.append(row_for(mesh,material,[tr(origin)],collision_only=hidden))
def planar(g,z):
    v=[];t=[]
    for poly in parts(shapely.make_valid(g)):
        if poly.geom_type!='Polygon' or poly.area<.00005:continue
        triangles=shapely.constrained_delaunay_triangles(poly)
        for tri in triangles.geoms:
            coords=np.asarray(tri.exterior.coords)[:3];base=len(v)
            if np.cross(np.r_[coords[1]-coords[0],0],np.r_[coords[2]-coords[0],0])[2]<0:coords=coords[[0,2,1]]
            v.extend([[p[0],p[1],z] for p in coords]);t.append([base,base+1,base+2])
    return np.array(v),np.array(t,dtype=int)
def planar_cells(name,g,z,hidden=False):
    g=shapely.set_precision(shapely.make_valid(g),.005)
    for cx in range(-3,3):
        for cy in range(-3,1):
            tile=g.intersection(box(cx*200,cy*200,(cx+1)*200,(cy+1)*200))
            if tile.area<.001:continue
            v,t=planar(tile,z);add_mesh(f'{name}_{cx+20}_{cy+20}',v,t,[(cx+.5)*200,(cy+.5)*200,z],ASPHALT,hidden,True)
contact=road.difference(lane.buffer(.002)).difference(walk)
aprons=unary_union([p.buffer(.25) for _,_,_,p in placed]).difference(road.buffer(-.02)).difference(walk)
planar_cells('SM_RoadClosure',contact,ROAD_Z)
planar_cells('SM_ParkingApron',aprons,ROAD_Z)
planar_cells('SM_RoadSupport',road.union(aprons),ROAD_Z,True)
M['rows']=[x for x in M['rows'] if '/Meshes/JunctionAsphalt.' not in x['mesh']]
report['road_closure_area_m2']=contact.area;report['parking_apron_area_m2']=aprons.area

# Roof islands provide exact closed building envelopes without cloning 200
# shared facade meshes or adding collision to unrelated asset users.
v,t=surfaces['RoofSurfaces'];edges=np.vstack([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]);graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(v),len(v)))
nc,labels=connected_components(graph,directed=False);islands=0
for k in range(nc):
    ti=t[labels[t[:,0]]==k]
    if not len(ti):continue
    used=np.unique(ti);mapping={int(old):new for new,old in enumerate(used)};top=v[used];tris=np.array([[mapping[int(a)] for a in x] for x in ti]);n=len(top)
    verts=np.vstack([top,np.column_stack([top[:,:2],np.full(n,GROUND)])]);faces=list(tris);faces.extend((tris[:,[2,1,0]]+n).tolist())
    count=collections.Counter(tuple(sorted((int(a),int(b)))) for face in tris for a,b in [(face[0],face[1]),(face[1],face[2]),(face[2],face[0])])
    for (a,b),times in count.items():
        if times==1:faces.extend([[a,b,b+n],[a,b+n,a+n]])
    origin=[float(top[:,0].mean()),float(top[:,1].mean()),GROUND]
    add_mesh(f'SM_BuildingEnvelope_{islands:02d}',verts,faces,origin);islands+=1
report['building_collision_envelopes']=islands

# Parked-car collision follows three convex body sections (static only).
car_meshes=sorted({row['mesh'] for row in vehicle_rows});collision_paths={}
for i,mesh in enumerate(car_meshes):
    vv=np.array(B[mesh]['vertices'])/100;axis=int(np.argmax(vv.max(0)[:2]-vv.min(0)[:2]));bounds=np.linspace(vv[:,axis].min(),vv[:,axis].max(),4);verts=[];faces=[]
    for j in range(3):
        points=vv[(vv[:,axis]>=bounds[j]-.08)&(vv[:,axis]<=bounds[j+1]+.08)]
        directions=np.array([d for d in itertools.product([-1,0,1],repeat=3) if any(d)],dtype=float);directions/=np.linalg.norm(directions,axis=1)[:,None]
        support=np.max(points@directions.T,axis=0)+.00001
        corners=HalfspaceIntersection(np.column_stack([directions,-support]),points.mean(0)).intersections
        hull=ConvexHull(corners);base=len(verts);verts.extend(corners);faces.extend((hull.simplices+base).tolist())
    name=f'SM_VehicleEnvelope_{i:02d}';meshpath=BASE+'/Collision/'+name
    jobs.append(dict(kind='create',asset=meshpath,vertices_cm=(np.array(verts)*100).tolist(),triangles=faces,collision=True,hidden=True,material=HIDDEN_MAT))
    trs=[copy.deepcopy(t) for row in vehicle_rows if row['mesh']==mesh for t in row['transforms']]
    new_rows.append(row_for(meshpath,HIDDEN_MAT,trs,collision_only=True));collision_paths[mesh]=meshpath
report['vehicle_collision_meshes']=collision_paths
# Legacy trees have no BodySetup shapes. Add trunk cylinders, avoiding canopy boxes.
verts=[];faces=[]
for z in [0,4]:
    verts.extend([[.30*math.cos(i*math.tau/12),.30*math.sin(i*math.tau/12),z] for i in range(12)])
for i in range(12):
    j=(i+1)%12;faces.extend([[i,j,j+12],[i,j+12,i+12]])
for i in range(1,11):faces.extend([[0,i+1,i],[12,12+i,12+i+1]])
name='SM_LegacyTreeTrunk';path=BASE+'/Collision/'+name
jobs.append(dict(kind='create',asset=path,vertices_cm=(np.array(verts)*100).tolist(),triangles=faces,collision=True,hidden=True,material=HIDDEN_MAT))
new_rows.append(row_for(path,HIDDEN_MAT,[x['t'] for x in legacy],collision_only=True))

M['rows']=[x for x in M['rows'] if x['transforms']]+new_rows
M['layout_repair_applied']='20261028-v1';M['counts']['instances']=sum(len(x['transforms']) for x in M['rows']);M['counts']['components']=len(M['rows'])
if (P/'Performance/published.json').exists():
    import runpy
    M,jobs=runpy.run_path(str(P/'Performance/manifest_policy.py'))['optimize'](M,jobs)
report['final_manifest_instances']=M['counts']['instances'];report['mesh_jobs']=len(jobs);report['legacy_trees_preserved']=len(legacy)
report['opposite_bank_modified']=False;report['apartment_keepout_overlap_m2']=road.intersection(keep).area+pads.intersection(keep).area
for name,g in [('road',road),('contact',contact),('aprons',aprons),('pads',pads),('parking_domain',parking_domain)]:
    (R/(name+'.wkb')).write_bytes(shapely.to_wkb(g))
(R/'repaired_manifest.json').write_text(json.dumps(M,separators=(',',':')),encoding='utf8')
(R/'legacy_layout.json').write_text(json.dumps(D,ensure_ascii=False,indent=2),encoding='utf8')
(R/'mesh_jobs.json').write_text(json.dumps(jobs,separators=(',',':')),encoding='utf8')
(R/'repair_plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda x:x.item()),encoding='utf8')
print('REPAIR_PLAN_READY',report['mesh_jobs'],report['final_manifest_instances'],flush=True)
