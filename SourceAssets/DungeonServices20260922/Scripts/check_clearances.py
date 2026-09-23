"""Geometric inspection explicitly requested by the user; no gameplay tests."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
def load_mesh(entry,scene):
    verts=[Vector(v) for v in entry['v']];faces=entry['f']
    lo=[min(v[i] for v in verts) for i in range(3)];hi=[max(v[i] for v in verts) for i in range(3)]
    actual=next(a for a in scene['actors'] if a['label']==entry['actor'])['components'][0]
    err=max(abs(a-b) for a,b in zip(lo+hi,actual['local_min']+actual['local_max']))
    if err>.02:raise RuntimeError('Source coordinate mismatch '+entry['actor']+' '+str((lo,hi,err)))
    return dict(v=verts,f=faces,tree=BVHTree.FromPolygons(verts,faces,epsilon=0),bounds=(lo,hi),error_cm=err)
def boxes(mesh):
    # Welding normals-split export vertices recovers each closed support cuboid.
    parent={}
    def find(k):
        parent.setdefault(k,k)
        if parent[k]!=k:parent[k]=find(parent[k])
        return parent[k]
    keys=[tuple(round(a,3) for a in v) for v in mesh['v']]
    for face in mesh['f']:
        root=find(keys[face[0]])
        for idx in face[1:]:parent[find(keys[idx])]=root
    groups={}
    for k in keys:groups.setdefault(find(k),[]).append(k)
    return [([min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]) for vs in groups.values()]
def inside_box(v,b,margin=.02):return all(b[0][i]+margin<v[i]<b[1][i]-margin for i in range(3))
def triangles_penetrating_boxes(mesh,solids):
    # SAT catches long triangles crossing a pier even when every vertex lies
    # outside it. Shrink solids 0.2 mm to exclude intentional flush anchor faces.
    all_tri=np.array([[mesh['v'][i] for i in face] for face in mesh['f']])
    lo=all_tri.min(axis=1);hi=all_tri.max(axis=1);count=0
    for bounds in solids:
        low=np.array(bounds[0])+.02;high=np.array(bounds[1])-.02
        candidates=all_tri[np.all((hi>low)&(lo<high),axis=1)]
        center=(low+high)/2;half=(high-low)/2
        for tri in candidates-center:
            edges=[tri[1]-tri[0],tri[2]-tri[1],tri[0]-tri[2]]
            axes=[np.cross(edges[0],edges[1])]+[np.cross(e,a) for e in edges for a in np.eye(3)]
            hit=True
            for axis in axes:
                if np.dot(axis,axis)<1e-15:continue
                projection=tri@axis;radius=np.abs(axis)@half
                if projection.min()>radius or projection.max()<-radius:hit=False;break
            count+=int(hit)
    return count
def inside_closed(v,m):
    direction=Vector((1,.177,.233)).normalized();origin=Vector(v);hits=0
    for i in range(128):
        hit=m['tree'].ray_cast(origin,direction,10000)
        if hit[0] is None:break
        hits+=1;origin=hit[0]+direction*.002
    return hits%2==1
report=dict(scope='Requested ceiling/light and structural-service interference only',gameplay_tests=False,stages={})
for suffix,scene_name in [('', 'scene-before.json'),('_after','scene-after.json')]:
    scene=json.loads((ROOT/'Sources'/scene_name).read_text())
    entries=json.loads((ROOT/'Sources'/('geometry-source-lod0'+suffix+'.json')).read_text())
    meshes={e['actor']:load_mesh(e,scene) for e in entries}
    supports=boxes(meshes['DGN_AV2_ConcreteSupports'])
    roofs={k:v for k,v in meshes.items() if k.endswith('_Ceiling') or any(n in k for n in ('VaultBacking','VaultStones','ModernCeiling'))}
    fixtures={k:v for k,v in meshes.items() if 'Fixtures' in k}
    result=dict(support_solids=len(supports),service_penetrating_triangles={},fixture_roof_penetrations={},lights=[],
                max_export_bound_error_cm=max(m['error_cm'] for m in meshes.values()))
    for key in ('DGN_AV2_ServicePipes','DGN_AV2_CableTrays'):
        result['service_penetrating_triangles'][key]=triangles_penetrating_boxes(meshes[key],supports)
    # All current fixtures, including obsolete-light replacements, against actual roofs.
    for key,m in fixtures.items():
        failures=[]
        for roof,r in roofs.items():
            count=sum(inside_closed(v,r) for v in m['v'] if inside_box(v,r['bounds']))
            if count:failures.append(dict(roof=roof,inside_vertices=count))
        result['fixture_roof_penetrations'][key]=failures
    for light in scene['lights']:
        if not light['properties']['visible'] or light['properties']['intensity']<=0:continue
        pos=Vector(light['location']);p=light['properties'];samples=[pos]
        if light['class_name']=='RectLightComponent':
            # Both installed area sources point vertically down, length along X.
            samples += [pos+Vector((dx*p['source_width']/2,dy*p['source_height']/2,0)) for dx in (-1,1) for dy in (-1,1)]
        else:
            radius=p.get('source_radius') or 0;half=(p.get('source_length') or 0)/2
            samples += [pos+Vector((dx*(half+radius),dy*radius,dz*radius)) for dx,dy,dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
        blocked=[name for name,r in roofs.items() if any(inside_box(v,r['bounds']) and inside_closed(v,r) for v in samples)]
        upward=[(name,r['tree'].ray_cast(pos,Vector((0,0,1)),3000)) for name,r in roofs.items()]
        gaps=[(name,hit[3]) for name,hit in upward if hit[0] is not None]
        result['lights'].append(dict(actor=light['actor'],source_intersects_roof=blocked,
            nearest_roof_above_cm=min((g for _,g in gaps),default=None)))
    report['stages']['after' if suffix else 'before']=result
    print('CLEARANCE_STAGE',suffix or 'before',json.dumps(result),flush=True)
(ROOT/'Receipts/clearance-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
