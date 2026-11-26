"""Check saved native collision hulls against all roads and seven door approaches."""
import json,re
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import MultiPoint,LineString
from wall_support_geometry import ROOT,rotate_vertices
from layout_geometry import house_paths
source=ROOT/'SourceAssets/TemperateHillsVillage';out=source/'WallReview20261114'
snapshot=json.loads((out/'current-scene.json').read_text(encoding='utf-8'))
plan=json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit=json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
paths=[(r['name'],LineString(np.array(r['points'])*100),r['width']*50) for r in plan['roads']]
paths += [('door_'+str(i+1),LineString(np.array(p)*100),width*50) for i,(p,width) in enumerate(house_paths(plan,kit))]
expected=[i for w in plan['yard_walls'] for i in w['native_instances']]
vectors=re.compile(r'\(X=([-+\deE.]+),Y=([-+\deE.]+),Z=([-+\deE.]+)\)')
records=[];maximum_pose_error=0.;mesh_hulls={}
for number,e in enumerate(expected):
    matches=[a for a in snapshot['instances'] if a['mesh']==e['mesh'] and np.linalg.norm(np.array(a['pos'])-e['pos'])<.05
        and np.linalg.norm(np.array(a['scale'])-e['scale'])<.001]
    assert len(matches)==1
    actual=matches[0]
    maximum_pose_error=max(maximum_pose_error,float(np.linalg.norm(np.array(actual['pos'])-e['pos'])))
    assert actual['collision_profile']=='BlockAll' and 'QUERY_AND_PHYSICS' in actual['collision_enabled']
    shape=snapshot['meshes'][actual['mesh']]
    if actual['mesh'] not in mesh_hulls:
        hulls=[]
        for text in shape['convex']:
            assert 'Translation=(X=0.000000,Y=0.000000,Z=0.000000)' in text
            assert 'Scale3D=(X=1.000000,Y=1.000000,Z=1.000000)' in text
            assert 'Rotation=(X=0.000000,Y=0.000000,Z=0.000000,W=1.000000)' in text
            v=np.array([list(map(float,m)) for m in vectors.findall(text.split(',IndexData=')[0])])
            hulls.append((v,ConvexHull(v).simplices))
        mesh_hulls[actual['mesh']]=hulls
    points=[]
    for v,f in mesh_hulls[actual['mesh']]:
        q=rotate_vertices(v*np.array(actual['scale']),actual['rot'])+np.array(actual['pos'])
        if (q[:,2]>0).any():points.extend(q[q[:,2]>0])
        t=q[f]
        for a,b in ((0,1),(1,2),(2,0)):
            va,vb=t[:,a],t[:,b];valid=(va[:,2]*vb[:,2]<0)
            a,b=va[valid],vb[valid]
            if len(a):points.extend(a+(b-a)*(-a[:,2]/(b[:,2]-a[:,2]))[:,None])
    assert len(points)>2
    hull=MultiPoint(np.array(points)[:,:2]).convex_hull
    clearance,route=min((hull.distance(line)-half,name) for name,line,half in paths)
    bounds=hull.bounds
    pad_clearance=min(bounds[0]+4600,4600-bounds[2],bounds[1]+3200,3200-bounds[3])
    records.append(dict(index=number,hulls=len(shape['convex']),route=route,edge_clearance_cm=round(clearance,2),
        pad_edge_clearance_cm=round(pad_clearance,2)))
report=dict(saved_boundaries=len(records),saved_house_masonry=len(snapshot['instances'])-len(records),
    maximum_position_difference_cm=maximum_pose_error,collision_profiles='BlockAll / QueryAndPhysics',
    roads_checked=len(plan['roads']),door_approaches_checked=len(plan['houses']),
    route_intrusions=[r for r in records if r['edge_clearance_cm']<0],
    minimum_collision_route_clearance_cm=min(r['edge_clearance_cm'] for r in records),
    minimum_collision_pad_edge_clearance_cm=min(r['pad_edge_clearance_cm'] for r in records),
    method='Saved native convex collision vertices, clipped at village ground Z=0; planar corridor clearance, not a player movement playtest',rows=records)
(out/'collision-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
