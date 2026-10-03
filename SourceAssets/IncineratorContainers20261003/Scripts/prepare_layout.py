"""Author wall bays against real FBX surfaces, floor contacts and opening envelopes.

This is placement construction, not a game/physics test. No scene render or simulation.
Run in Blender background. The stored bays are mutually exclusive in space for every seed.
"""
import copy
import json
import math
import random
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
source=ROOT/'Config/placement-source.json'
if not source.exists():source=ROOT.parent/'DungeonIncineratorLine20261003/Config/source-modules.json'
modules={m['id']:m for m in read(source)['modules']}
assemblies=read(ROOT/'Config/assemblies.json')
files=(ROOT/'Config/geometry-files.txt').read_text('utf-8-sig').splitlines()
registry={Path(f).stem:PROJECT/f for f in files}
registry.update({o['name']:Path(o['fbx']) for o in read(ROOT/'Authored/manifest.json')['objects']})
cache={}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)


def mesh_data(name):
    if name in cache:return cache[name]
    path=registry[name]
    previous=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=False)
    objects=[o for o in bpy.data.objects if o not in previous]
    surfaces=[]
    for obj in objects:
        if obj.type!='MESH' or obj.name.startswith(('UCX_','UBX_','UCP_','USP_')):continue
        mesh=obj.data;mesh.calc_loop_triangles()
        vertices=np.zeros(len(mesh.vertices)*3,dtype=np.float64)
        mesh.vertices.foreach_get('co',vertices);vertices=vertices.reshape((-1,3))
        matrix=np.array(obj.matrix_world,dtype=np.float64)
        vertices=vertices@matrix[:3,:3].T+matrix[:3,3]
        # FBX -> Blender restores the original authoring axes. UE uses cm and mirrored Y.
        vertices*=np.array([100,-100,100])
        indices=np.array([list(t.vertices) for t in mesh.loop_triangles],dtype=np.int32)
        surfaces.append(vertices[indices])
    value=np.concatenate(surfaces)
    for obj in objects:
        mesh=obj.data if obj.type=='MESH' else None
        bpy.data.objects.remove(obj,do_unlink=True)
        if mesh and mesh.users==0:bpy.data.meshes.remove(mesh)
    cache[name]=value
    return value


def rotate(vertices,yaw):
    a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
    matrix=np.array([[c,-s,0],[s,c,0],[0,0,1]])
    return vertices@matrix.T


def bounds_for(family):
    assembly=assemblies['assemblies'][family];cloud=[]
    for part in assembly.get('static_parts',[]):
        cloud.append(mesh_data(part['mesh'].split('/')[-1]).reshape((-1,3))+part['position_cm'])
    for part in assembly['containers']:
        config=assemblies['prototypes'][part['prototype']];offset=np.array(part['position_cm'])
        cloud.append(mesh_data(config['body'].split('/')[-1]).reshape((-1,3))+offset)
        door=mesh_data(config['door'].split('/')[-1]).reshape((-1,3))
        hinge=np.array(config['hinge'])
        motion=config['opening_motion']
        # One-degree samples, expanded by 2 cm, enclose the full continuous motion.
        steps=math.ceil(abs(config.get('opened_roll',config.get('opened_yaw',0))))+1
        if motion=='Drawer':steps=2
        for fraction in np.linspace(0,1,steps):
            if motion=='Lid':
                a=-math.radians(config['opened_roll']*fraction);c,s=math.cos(a),math.sin(a)
                matrix=np.array([[1,0,0],[0,c,-s],[0,s,c]])
                vertices=door@matrix.T
            elif motion=='Swing':vertices=rotate(door,config['opened_yaw']*fraction)
            else:vertices=door+np.array(config['drawer_travel'])*fraction
            points=vertices+hinge+offset
            cloud.extend([points.min(axis=0)[None,:],points.max(axis=0)[None,:]])
    points=np.concatenate(cloud);lo=points.min(axis=0);hi=points.max(axis=0)
    closed_width,closed_depth,height=np.array(assembly['dimensions_m'])*100
    # Keep an interaction aisle beyond the closed front, as well as every moving part.
    lo[1]=min(lo[1],-closed_depth/2-90)
    lo[0]-=12;hi[0]+=12;lo[1]-=4;hi[1]+=4;hi[2]+=5
    lo[2]=1.0
    return lo,hi


envelopes={family:bounds_for(family) for family in assemblies['assemblies']}


def bvh(triangles):
    points=triangles.reshape((-1,3))
    return BVHTree.FromPolygons(points.tolist(),np.arange(len(points)).reshape((-1,3)).tolist(),all_triangles=True)


def intersects(triangles,lo,hi):
    # Separating axes of an AABB and triangle. This preserves real gaps in merged meshes.
    mask=np.all(triangles.max(axis=1)>=lo,axis=1)&np.all(triangles.min(axis=1)<=hi,axis=1)
    t=triangles[mask]
    if not len(t):return False
    t=t-(lo+hi)/2;half=(hi-lo)/2
    edges=np.roll(t,-1,axis=1)-t
    axes=[np.cross(edges[:,0],edges[:,1])]
    for axis in np.eye(3):
        for edge in range(3):axes.append(np.cross(edges[:,edge],axis))
    remain=np.ones(len(t),dtype=bool)
    for axis in axes:
        projections=np.sum(t*axis[:,None,:],axis=2);radius=np.abs(axis)@half
        remain&=(projections.min(axis=1)<=radius+1e-5)&(projections.max(axis=1)>=-radius-1e-5)
    return bool(remain.any())


def overlaps(a,b):return bool(np.all(a[1]>b[0]) and np.all(b[1]>a[0]))


def box_at(family,p,yaw):
    lo,hi=envelopes[family]
    corners=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
    world=rotate(corners,yaw)+p
    return world.min(axis=0),world.max(axis=0)


def room_surfaces(module):
    all_tri=[];floors=[];walls=[]
    for part in module['parts']:
        name=part['mesh'].split('/')[-1]
        if name.startswith('SM_Treatment_'):continue
        if name not in registry:
            # The ceiling luminaires are above every cabinet/opening volume.
            if name.startswith('SM_CeilingLamp_'):continue
            raise RuntimeError('Authoring FBX unavailable '+name)
        tri=rotate(mesh_data(name)*part.get('scale',[1,1,1]),part['yaw'])+part['position']
        all_tri.append(tri)
        if any(word in name.lower() for word in ('floor','paving','platformdeck','bridgedeck','observationdeck')):floors.append(tri)
        if any(word in name.lower() for word in ('shell','walls')):walls.append(tri)
    return np.concatenate(all_tri),bvh(np.concatenate(floors)),bvh(np.concatenate(walls))


def support(floor,x,y,z):
    location,normal,_,_=floor.ray_cast(Vector((x,y,z+25)),Vector((0,0,-1)),50)
    if location is None or abs(normal.z)<.985 or abs(location.z-z)>18:return None
    return location.z


def candidates(module,family,geometry,layers):
    triangles,floor,wall=geometry;lo,hi=envelopes[family]
    width,depth,_=np.array(assemblies['assemblies'][family]['dimensions_m'])*100
    ports=module['ports'];seen=set();out=[]
    xmin=min(c['min'][0] for c in module['cells']);xmax=max(c['max'][0] for c in module['cells'])
    ymin=min(c['min'][1] for c in module['cells']);ymax=max(c['max'][1] for c in module['cells'])
    for layer in layers:
        for x in np.arange(xmin+45,xmax,85):
            for y in np.arange(ymin+45,ymax,85):
                if support(floor,x,y,layer) is None:continue
                for direction,yaw in (((1,0,0),-90),((-1,0,0),90),((0,1,0),0),((0,-1,0),180)):
                    hit,normal,_,distance=wall.ray_cast(Vector((x,y,layer+90)),Vector(direction),170)
                    if hit is None or abs(normal.z)>.15:continue
                    p=np.array([hit.x,hit.y,layer])-np.array(direction)*(hi[1]+7)
                    key=(round(p[0]/40),round(p[1]/40),layer,yaw)
                    if key in seen:continue
                    seen.add(key)
                    z=support(floor,p[0],p[1],layer)
                    if z is None:continue
                    # All four support corners lie on the same real horizontal floor.
                    feet=rotate(np.array([[dx,dy,0] for dx in (-width*.40,width*.40)
                        for dy in (-depth*.32,depth*.32)]),yaw)+p
                    heights=[support(floor,q[0],q[1],layer) for q in feet]
                    if any(h is None or abs(h-z)>.65 for h in heights):continue
                    p[2]=z+.3;box=box_at(family,p,yaw)
                    if any(abs(p[2]-port['position'][2])<190 and
                        np.linalg.norm(p[:2]-port['position'][:2])<210 for port in ports):continue
                    if any(overlaps(box,(np.array(b['min']),np.array(b['max']))) for b in module.get('walk_mask',[])):continue
                    if intersects(triangles,*box):continue
                    out.append(dict(position=[round(v,3) for v in p],yaw=yaw,box=[box[0].tolist(),box[1].tolist()],floor_z=z))
    return out


def variant(family,slot_id,p,yaw):
    assembly=assemblies['assemblies'][family];specs=[]
    for i,item in enumerate(assembly['containers']):
        spec=copy.deepcopy(assemblies['prototypes'][item['prototype']]);spec.pop('dimensions_m',None)
        offset=rotate(np.array([item['position_cm']]),yaw)[0]
        spec.update(position=(np.array(p)+offset).tolist(),yaw=yaw,
                    container_id=slot_id+'.'+str(i),caption=item.get('caption',spec['caption']))
        specs.append(spec)
    return dict(id=family,containers=specs)


# Totals are search entrances: 4-5 / 10-11 / 8-9, 22-25 across the three rooms.
# Main hall also includes its B1 records alcove. Static carcass and 3 drawers share a fixed bay.
plans={
    'ShoredBreach':[('ToolBox',6,[3,4],[0]),('PPELocker',3,[1,1],[0])],
    'AbandonedIncineratorHall':[
        ('RecordsCabinet',1,[1,1],[-356]),('PPELocker',3,[2,2],[0,-356,240]),
        ('HeatCabinet',3,[2,2],[0,-356]),('ToolBox',4,[1,2],[0,-356,240])],
    'AbandonedFlueGasStation':[
        ('PPELocker',2,[1,1],[0]),('HeatCabinet',2,[1,1],[0]),
        ('FilterCase',6,[3,4],[0,240]),('ToolBox',3,[2,2],[0,240])]
}
layout=dict(revision='treatment_wall_bays_v1_20261003',preview_seed=20261003,
    outline=assemblies['outline'],groups={},fixed_parts={},count_ranges={},physical_count_ranges={},
    authoring_policy='actual FBX triangle clearance; full opening envelope and 90cm front access; floor support and port/walk masks',
    tests_run=False,game_run=False,rewards_deferred=True)
for identity,plan in plans.items():
    print('TREATMENT_BAYS_AUTHORING '+identity,flush=True)
    module=modules[identity];geometry=room_surfaces(module);reserved=[];groups=[];fixed=[];ranges=[0,0];physical=[0,0]
    rng=random.Random(20261003+len(groups)+list(plans).index(identity))
    for family,desired,picks,layers in plan:
        pool=candidates(module,family,geometry,layers);rng.shuffle(pool)
        if family=='RecordsCabinet':pool.sort(key=lambda p:np.linalg.norm(np.array(p['position'][:2])-[-1000,-160]))
        # Spread alternatives along room walls, including ground and upper/B1 levels.
        slots=[]
        for candidate in pool:
            box=(np.array(candidate['box'][0]),np.array(candidate['box'][1]))
            if any(overlaps(box,other) for other in reserved):continue
            sid='Treatment.'+identity+'.'+family+'.'+str(len(slots)+1)
            slots.append(dict(id=sid,variants=[variant(family,sid,candidate['position'],candidate['yaw'])],
                clearance_cm=dict(min=box[0].tolist(),max=box[1].tolist()),floor_z=candidate['floor_z']))
            reserved.append(box)
            if family=='RecordsCabinet':
                for part in assemblies['assemblies'][family]['static_parts']:
                    fixed.append(dict(mesh=part['mesh'],position=candidate['position'],yaw=candidate['yaw'],
                        scale=[1,1,1],collision=True,materials=[],fluid=False,treatment_container_fixed=True))
            if len(slots)==desired:break
        if len(slots)<picks[1]:
            raise RuntimeError('Insufficient clear wall bays '+identity+'/'+family+': '+str(len(slots)))
        groups.append(dict(id='Treatment.'+identity+'.'+family,pick_count=picks,slots=slots))
        entries=len(assemblies['assemblies'][family]['containers'])
        ranges=[ranges[i]+picks[i]*entries for i in range(2)];physical=[physical[i]+picks[i] for i in range(2)]
        print('TREATMENT_BAYS '+family+' '+str(len(slots))+' pick='+str(picks),flush=True)
    layout['groups'][identity]=groups;layout['fixed_parts'][identity]=fixed
    layout['count_ranges'][identity]=ranges;layout['physical_count_ranges'][identity]=physical
(ROOT/'Config/layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')
print('TREATMENT_LAYOUT_AUTHORED '+str(layout['count_ranges']),flush=True)
