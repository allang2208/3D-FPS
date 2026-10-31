from pathlib import Path
import sys,json,collections,math,itertools
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'pythonlib'))
import numpy as np,shapely
from shapely.geometry import Polygon,MultiPoint,Point,LineString,box
from shapely.ops import unary_union
from shapely.affinity import affine_transform
from scipy.spatial.transform import Rotation
S=json.loads((R/'saved_scene.json').read_text());M=json.loads((R.parent/'publish_manifest.json').read_text());CFG=json.loads((R.parent/'native_inputs.json').read_text())
def matrix(t):return Rotation.from_quat(t['q']).as_matrix()*np.asarray(t['s'])[None,:]
def pts(v,t):return (np.asarray(v)@matrix(t).T+np.asarray(t['p']))/100
def key(mesh,t):
    q=np.array(t['q']);q=q if q[3]>=0 else -q
    return (mesh,*np.round(t['p'],1),*np.round(q,3),*np.round(t['s'],3))
def polygons(g):return list(g.geoms) if hasattr(g,'geoms') else [g]
def sample_geo(g):return dict(area=round(g.area,3),bounds=list(g.bounds),centroid=list(g.centroid.coords)[0])
native=[r for r in S['rows'] if r['native']]
expected=collections.Counter(key(r['mesh'],t) for r in M['rows'] for t in r['transforms']);actual=collections.Counter(key(r['mesh'],t) for r in native for t in r['transforms'])
report=dict(scope='saved apartment near-bank district',actual_native_instances=sum(actual.values()),expected_instances=sum(expected.values()),snapshot_missing=sum((expected-actual).values()),snapshot_extra=sum((actual-expected).values()),geometry_export_errors=S['geometry_errors'])
report['component_issues']=[dict(actor=r['actor'],component=r['component'],mesh=r['mesh'],mobility=r['mobility'],visible=r['visible'],hidden=r['hidden_in_game'],custom_stride=r['custom_stride'],custom_count=r['custom_count'],count=len(r['transforms'])) for r in native if (r['custom_stride']*len(r['transforms'])!=r['custom_count'] or r['visible'] is False or r['hidden_in_game'] is True or 'MOVABLE' in r['mobility'])]
report['null_materials']=[dict(actor=r['actor'],component=r['component'],mesh=r['mesh']) for r in native if any(m is None for m in r['materials'])]
report['duplicate_native_transforms']=[dict(mesh=k[0],p=list(k[1:4]),copies=n) for k,n in actual.items() if n>1]
local_cache={}
def footprint(mesh,t):
    b=S['meshes'][mesh];corners=list(itertools.product(*zip(b['min'],b['max'])))
    w=pts(corners,t)
    return MultiPoint(w[:,:2]).convex_hull,float(w[:,2].min()),float(w[:,2].max())
def exact_surface(mesh,t):
    b=S['meshes'][mesh]
    if 'vertices' not in b:return None
    mat=matrix(t)
    if abs(mat[0,2])+abs(mat[1,2])<1e-5:
        if mesh not in local_cache:
            vs=np.asarray(b['vertices'])/100;arr=vs[np.array(b['triangles'],dtype=int)]
            area=np.abs((arr[:,1,0]-arr[:,0,0])*(arr[:,2,1]-arr[:,0,1])-(arr[:,1,1]-arr[:,0,1])*(arr[:,2,0]-arr[:,0,0]))/2
            local_cache[mesh]=unary_union(shapely.polygons(arr[area>1e-7,:,:2]))
        return affine_transform(local_cache[mesh],[mat[0,0],mat[0,1],mat[1,0],mat[1,1],t['p'][0]/100,t['p'][1]/100])
    vs=pts(b['vertices'],t);tri=np.array(b['triangles'],dtype=int);arr=vs[tri]
    a=arr[:,1,:2]-arr[:,0,:2];b2=arr[:,2,:2]-arr[:,0,:2]
    areas=np.abs(a[:,0]*b2[:,1]-a[:,1]*b2[:,0])/2
    arr=arr[areas>1e-7]
    return unary_union(shapely.polygons(arr[:,:,:2]))
def road_kind(p):
    if 'JunctionAsphalt' in p:return 'junction'
    if 'SM_Lane_Car_' in p or 'SM_Lane_Divider_' in p:return 'lane'
    if 'SM_Sidewalk_' in p:return 'sidewalk'
    if 'Modular_Curb_' in p:return 'curb'
    if '/Meshes/BuildingPads' in p:return 'building_pad'
    if '/Meshes/ParkGround' in p:return 'park'
    return None
layers=collections.defaultdict(list);items=[];missing_geometry=[];meshcounts=collections.Counter()
for r in native:
    p=r['mesh'];meshcounts[p]+=len(r['transforms']);kind=road_kind(p)
    for i,t in enumerate(r['transforms']):
        if kind:
            # Rough sculpted curbs are contextual bounds only. Driving surfaces,
            # junctions and sidewalk corners retain actual triangle footprints.
            g=footprint(p,t)[0] if kind=='curb' else exact_surface(p,t)
            if g is None:missing_geometry.append(p);continue
            layers[kind].append(g)
        if any(w in p for w in ['/Vehicle/','StreetLamp','Road_Sign','Parking_Meter','Hydrant','Mail','BlackAlder']):
            g,z0,z1=footprint(p,t)
            cat='tree' if 'BlackAlder' in p else 'car' if '/Vehicle/' in p else 'lamp' if 'StreetLamp' in p else 'sign' if 'Road_Sign' in p else 'meter' if 'Parking_Meter' in p else 'hydrant' if 'Hydrant' in p else 'mail'
            items.append(dict(actor=r['actor'],component=r['component'],index=i,mesh=p,t=t,kind=cat,poly=g,z0=z0,z1=z1))
print('Footprints assembled', {k:len(v) for k,v in layers.items()},flush=True)
U={k:unary_union(v) for k,v in layers.items()};road=unary_union([U.get('lane',Polygon()),U.get('junction',Polygon())]);walk=U.get('sidewalk',Polygon());pad=U.get('building_pad',Polygon())
for k,g in dict(U,road=road).items():(R/(k+'.wkb')).write_bytes(shapely.to_wkb(g))
report['missing_surface_geometry']=sorted(set(missing_geometry))
report['surface_checks_complete']=not missing_geometry
report['surface_summary']={k:dict(area_m2=round(v.area,2),pieces=len(polygons(v))) for k,v in U.items()}
connected=road.buffer(.025).buffer(-.025)
parts=sorted(polygons(connected),key=lambda x:x.area,reverse=True)
report['road_connected_components_5cm_tolerance']=[sample_geo(g) for g in parts if g.area>.1]
roadlines=[];gaps=[]
for x in CFG['inputs']:
    tag=x['tag']
    if tag not in ['NBPCG_Local','NBPCG_Collector','NBPCG_Artery']:continue
    coords=np.array(x['points'])[:,:2]/100
    if x['closed']:coords=np.vstack([coords,coords[0]])
    line=LineString(coords);roadlines.append(line)
    missing=line.difference(road.buffer(.05))
    gaps.append(dict(name=x['name'],length_m=line.length,uncovered_m=missing.length,segments=[dict(length=s.length,bounds=list(s.bounds)) for s in polygons(missing) if s.length>.1]))
report['road_centerline_coverage']=gaps
report['road_building_pad_intersection_m2']=road.intersection(pad).area
height_ranges={}
for label in ['SM_Lane_Car_','SM_Lane_Divider_','JunctionAsphalt','SM_Sidewalk_']:
    low=[];high=[]
    for r in native:
        if label not in r['mesh']:continue
        b=S['meshes'][r['mesh']]
        for t in r['transforms']:
            w=pts(list(itertools.product(*zip(b['min'],b['max']))),t)
            low.append(float(w[:,2].min()));high.append(float(w[:,2].max()))
    if low:height_ranges[label]=dict(bottom_min_m=min(low),bottom_max_m=max(low),top_min_m=min(high),top_max_m=max(high))
report['surface_height_ranges']=height_ranges
keep=next(x for x in CFG['inputs'] if x['tag']=='NBPCG_Exclusion');keep=Polygon(np.array(keep['points'])[:,:2]/100)
report['apartment_keepout_road_intersection_m2']=road.intersection(keep).area
report['apartment_keepout_building_intersection_m2']=pad.intersection(keep).area
solids=[]
for x in items:
    g=x['poly']
    if x['kind'] in ('lamp','sign','tree'):g=Point(np.array(x['t']['p'])[:2]/100).buffer(.20 if x['kind']=='lamp' else .13 if x['kind']=='sign' else .28)
    solids.append(g)
tree=shapely.STRtree(solids);overlaps=[];roadprops=[]
for i,x in enumerate(items):
    if x['kind']!='car':
        intr=solids[i].intersection(road)
        if intr.area>.03:roadprops.append(dict(kind=x['kind'],mesh=x['mesh'],p=x['t']['p'],area_m2=intr.area,actor=x['actor'],component=x['component'],index=x['index']))
    for j in tree.query(solids[i],predicate='intersects'):
        if j<=i:continue
        y=items[j]
        if x['kind']!='car' and y['kind']!='car':continue
        if min(x['z1'],y['z1'])-max(x['z0'],y['z0'])<.03:continue
        g=solids[i].intersection(solids[j])
        if g.area>.015:overlaps.append(dict(a={k:x[k] for k in ['actor','component','index','kind','mesh']},b={k:y[k] for k in ['actor','component','index','kind','mesh']},p=np.array(x['t']['p']).tolist(),area_m2=g.area))
report['ground_prop_overlaps']=overlaps;report['nonvehicle_obstacles_on_carriageway']=roadprops
report['parking_far_from_roads']=[dict(actor=x['actor'],component=x['component'],index=x['index'],mesh=x['mesh'],p=x['t']['p'],distance_to_carriageway_m=x['poly'].distance(road)) for x in items if x['kind']=='car' and not road.is_empty and x['poly'].distance(road)>8]
legacy_conflicts=[]
if not road.is_empty:
    for r in S['rows']:
        if not r['actor'].startswith('NB28_Cell'):continue
        p=r['mesh'];is_tree=any(w in p for w in ['Tree','Aspen'])
        for i,t in enumerate(r['transforms']):
            footprint_g,z0,z1=footprint(p,t)
            if z1<-108.36:continue
            g=Point(np.array(t['p'])[:2]/100).buffer(.25) if is_tree else footprint_g
            road_area=g.intersection(road).area;building_area=g.intersection(pad).area
            if road_area>.03 or building_area>.03:
                legacy_conflicts.append(dict(actor=r['actor'],component=r['component'],index=i,mesh=p,p=t['p'],tree=is_tree,road_overlap_m2=road_area,building_overlap_m2=building_area))
report['retained_furnishing_conflicts']=legacy_conflicts
report['collision_disabled_by_mesh']={p:n for p,n in meshcounts.items() if any(w in p for w in ['BlackAlder','/Vehicle/','/Kit_Sidewalk']) and any(r['mesh']==p and 'NO_COLLISION' in r['collision'] for r in native)}
report['blocking_meshes_without_simple_collision']=[dict(mesh=p,instances=meshcounts[p],trace=b['collision_trace']) for p,b in S['meshes'].items() if p in meshcounts and b['simple_collision_count']==0 and 'COMPLEX_AS_SIMPLE' not in str(b['collision_trace']) and any(r['mesh']==p and 'NO_COLLISION' not in r['collision'] for r in native)]
report['native_trees']=len([x for x in items if x['kind']=='tree'])
report['nearbank_legacy_actors']=[a for a in S['actors'] if a['label'].startswith('NB28_')]
report['remaining_retired_actors']=[a['label'] for a in S['actors'] if a['label'] in CFG['retire_legacy_labels']]
if not report['surface_checks_complete']:
    for k in ['surface_summary','road_connected_components_5cm_tolerance','road_centerline_coverage','road_building_pad_intersection_m2','apartment_keepout_road_intersection_m2','apartment_keepout_building_intersection_m2','nonvehicle_obstacles_on_carriageway','parking_far_from_roads','retained_furnishing_conflicts']:
        report[k]=None
(R/'findings.json').write_text(json.dumps(report,indent=2),encoding='utf8')
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
fig,ax=plt.subplots(figsize=(16,12));ax.set_facecolor('#edf0e8')
for kind,color in [('lane','#87929a'),('junction','#606d78'),('sidewalk','#d4c2a0'),('curb','#9a9a92'),('building_pad','#4d6582'),('park','#a0c082')]:
    for poly in polygons(U.get(kind,Polygon())):
        if poly.is_empty or poly.geom_type!='Polygon':continue
        ax.add_patch(Patch(np.asarray(poly.exterior.coords),facecolor=color,edgecolor='none',label=kind))
for x in items:
    c={'tree':'#306039','lamp':'#dd8b11','car':'#657a90','sign':'#a05371','meter':'#6b5160','hydrant':'#d22','mail':'#874'}[x['kind']]
    ax.scatter(x['t']['p'][0]/100,x['t']['p'][1]/100,s=8 if x['kind']=='tree' else 2,c=c)
ax.add_patch(Patch(np.asarray(keep.exterior.coords),fill=False,edgecolor='#e15759',lw=2))
ax.set_aspect('equal');ax.set_xlim(-535,535);ax.set_ylim(-555,110);ax.set_title('Saved apartment near-bank geometry - road / sidewalk / building footprints');ax.set_xlabel('World X (m)');ax.set_ylabel('World Y (m)');ax.grid(alpha=.15)
fig.tight_layout();fig.savefig(R/'district_geometry.png',dpi=160);plt.close(fig)
print(json.dumps({k:report[k] for k in ['actual_native_instances','snapshot_missing','snapshot_extra','road_building_pad_intersection_m2','apartment_keepout_road_intersection_m2','native_trees']}),flush=True)
print('road pieces',len(report['road_connected_components_5cm_tolerance'] or []),'prop overlaps',len(overlaps),'roadprops',len(roadprops),'collision holes',len(report['blocking_meshes_without_simple_collision']),flush=True)
