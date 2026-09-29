"""Reuse the imported bed geometry/material slots; author fitted convex collision and resting poses."""
import json
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Quaternion

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
SOURCE=PROJECT/'SourceAssets/HospitalBed20260929'
BED_SCALE=json.loads((ROOT.parent/'Config/room.json').read_text(encoding='utf-8'))['bed_scatter'].get('asset_scale',1.0)
OUT=ROOT/'Authored'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'Exports/SM_HospitalBed.fbx'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
all_points=[]
colliders=[]
mesh_name='SM_Ward_HospitalBed'

def hull(points):
    bm=bmesh.new()
    for p in set(tuple(v) for v in points):bm.verts.new(p)
    result=bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    unused=[e for e in result['geom_interior']+result['geom_unused'] if isinstance(e,bmesh.types.BMVert) and e.is_valid]
    if unused:bmesh.ops.delete(bm,geom=list(set(unused)),context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    mesh=bpy.data.meshes.new('Collision');bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(f'UCX_{mesh_name}_{len(colliders):02d}',mesh)
    bpy.context.scene.collection.objects.link(obj);colliders.append(obj)

for obj in objects:
    points=[tuple(obj.matrix_world@v.co) for v in obj.data.vertices]
    all_points.extend(points)
    # Weld only for identifying closed source parts; never modify the approved render mesh.
    keys=[tuple(round(v,5) for v in p) for p in points]
    graph={k:set() for k in keys}
    for edge in obj.data.edges:
        a,b=(keys[i] for i in edge.vertices);graph[a].add(b);graph[b].add(a)
    seen=set()
    for start in graph:
        if start in seen:continue
        stack=[start];seen.add(start);component=[]
        while stack:
            v=stack.pop();component.append(v)
            for n in graph[v]:
                if n not in seen:seen.add(n);stack.append(n)
        lo=[min(v[i] for v in component) for i in range(3)]
        hi=[max(v[i] for v in component) for i in range(3)]
        # The two U-shaped outer rails are concave. Their +X profile vertices
        # trace the tube centreline; build one fitted hull per segment, keeping
        # the large spaces between uprights empty for movement and hit traces.
        if hi[0]-lo[0]<.065 and hi[1]-lo[1]>.9 and hi[2]-lo[2]>.8:
            centers={v for v in component if abs(v[0]-hi[0])<.00002}
            segments={tuple(sorted((v,n))) for v in centers for n in graph[v] if n in centers}
            if len(segments)<3:raise RuntimeError('Cannot derive bed rail collision centreline')
            radius=(hi[0]-lo[0])/2
            x=(lo[0]+hi[0])/2
            for a,b in sorted(segments):
                a=Vector((x,a[1],a[2]));b=Vector((x,b[1],b[2]))
                direction=(b-a).normalized();side=Vector((1,0,0));other=direction.cross(side)
                shell=[p+radius*(math.cos(t*math.tau/8)*side+math.sin(t*math.tau/8)*other)
                       for p in (a,b) for t in range(8)]
                hull(shell+[a-direction*radius,b+direction*radius])
        else:
            hull(component)

bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.object.join()
bed=bpy.context.object;bed.name=mesh_name
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# Bake the requested size into the ward derivative and every fitted hull.
# Pose bounds below use the same scale; the approved imported source is untouched.
for obj in [bed]+colliders:
    for vertex in obj.data.vertices:vertex.co*=BED_SCALE
all_points=[tuple(v*BED_SCALE for v in p) for p in all_points]
for obj in colliders:obj.select_set(True)
bpy.context.view_layer.objects.active=bed
fbx=OUT/(mesh_name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)

# Unreal Rotator pitch/roll use negative right-handed Y/X rotations. Determine
# the inverted pitch from the actual head and foot rail support heights so an
# upside-down bed rests on both ends instead of hanging from its tall headboard.
physical_points=all_points+[tuple(v.co) for obj in colliders for v in obj.data.vertices]
ue_points=[Vector((100*p[0],-100*p[1],100*p[2])) for p in physical_points]
def rotation(pitch,roll):
    return Quaternion((0,1,0),math.radians(-pitch))@Quaternion((1,0,0),math.radians(-roll))
head=[p for p in ue_points if p.x<-85*BED_SCALE]
foot=[p for p in ue_points if p.x>85*BED_SCALE]
low,high=-30.,0.
for _ in range(40):
    pitch=(low+high)/2;q=rotation(pitch,180)
    difference=min((q@p).z for p in head)-min((q@p).z for p in foot)
    if difference>0:low=pitch
    else:high=pitch
inverted_pitch=(low+high)/2
poses=[]
for name,pitch,roll,weight in [('Upright',0,0,.55),('LeftSide',0,90,.15),('RightSide',0,-90,.15),('Inverted',inverted_pitch,180,.15)]:
    rotated=[rotation(pitch,roll)@p for p in ue_points]
    poses.append(dict(id=name,pitch=pitch,roll=roll,weight=weight,
                      min=[min(p[i] for p in rotated) for i in range(3)],max=[max(p[i] for p in rotated) for i in range(3)]))
manifest=dict(mesh=mesh_name,fbx=str(fbx),source_mesh='/Game/Props/HospitalBed20260929/SM_HospitalBed',
    source_license=str(SOURCE/'license.txt'),credit="Hospital Bed by loxfear, CC-BY-4.0",
    materials={'Frame':'/Game/Props/HospitalBed20260929/Materials/M_HospitalBed_Frame',
               'Linen':'/Game/Props/HospitalBed20260929/Materials/M_HospitalBed_Linen',
               'Pillow':'/Game/Props/HospitalBed20260929/Materials/M_HospitalBed_Pillow'},
    asset_scale=BED_SCALE,collision_hulls=len(colliders),poses=poses,rendered=False,gameplay_tested=False)
(ROOT/'bed-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WardHospitalBedCollision.blend'))
print('WARD_BED_AUTHORED',len(colliders),'convex hulls; inverted pitch',inverted_pitch,flush=True)
