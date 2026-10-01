"""Reuse the finished pallet jack from the freight assembly without rebuilding it."""
import hashlib,json,re
from pathlib import Path
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
SOURCE=PROJECT/'SourceAssets/DungeonVentFreight20260922/Authored'
for folder in ('Authored','Receipts'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
original='SM_RS_FreightTransfer_Props'
name='SM_Freight_PalletJack'
with bpy.data.libraries.load(str(SOURCE/'Dungeon_VentFreight.blend'),link=False) as (src,dst):
    dst.objects=[original]
obj=dst.objects[0]
bpy.context.scene.collection.objects.link(obj)
# The original authored cart occupies x 1.00..1.78, y 10.72..12.39.
# Pallets end before y 10.5 and the rack is at x 16.75; remove those whole parts.
bm=bmesh.new();bm.from_mesh(obj.data)
remove=[v for v in bm.verts if not (.98<=v.co.x<=1.81 and 10.68<=v.co.y<=12.42 and -.01<=v.co.z<=1.42)]
bmesh.ops.delete(bm,geom=remove,context='VERTS')
bm.to_mesh(obj.data);bm.free();obj.data.update()
obj.name=name;obj.data.name=name;obj.location=(0,0,0)
origin=Vector((1.39,11.555,0))
for v in obj.data.vertices:v.co-=origin
# Retain the exact source UVs, vertex wear, normals, bevels and material surfaces.
used=sorted({face.material_index for face in obj.data.polygons})
materials=[obj.data.materials[i] for i in used]
indices=[used.index(face.material_index) for face in obj.data.polygons]
obj.data.materials.clear()
for mat in materials:obj.data.materials.append(mat)
for face,index in zip(obj.data.polygons,indices):face.material_index=index

# Simple authored collision follows each fork, rear pump block and handle.
# The gap between the forks remains empty instead of using one overall hull.
colliders=[]
def hull(center,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(center)-origin)
    c=bpy.context.object;c.name='UCX_'+name+'_'+str(len(colliders)).zfill(2)
    c.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    colliders.append(c)
for x in (1.10,1.68):hull((x,11.435,.105),(.20,1.44,.21))
hull((1.39,12.18,.31),(.79,.40,.62))
hull((1.39,12.325,.845),(.105,.145,.60))
hull((1.39,12.36,1.215),(.54,.072,.36))
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
for c in colliders:c.select_set(True);c.hide_render=True
bpy.context.view_layer.objects.active=obj
fbx=ROOT/'Authored'/(name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/PalletJack_Reused.blend'))
source_record=next(o for o in json.loads((SOURCE/'manifest.json').read_text('utf-8'))['objects'] if o['name']==original)
mapping={}
for mat in materials:
    key=re.sub(r'[._][0-9]{3}$','',mat.name)
    mapping[key]=source_record['materials'][key]
lo=[min(v.co[i] for v in obj.data.vertices) for i in range(3)]
hi=[max(v.co[i] for v in obj.data.vertices) for i in range(3)]
record=dict(name=name,fbx=str(fbx),asset='/Game/Dungeons/CargoWarehouse20261001/Reused/Meshes/'+name,
    materials=mapping,triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),
    bounds_m=dict(min=lo,max=hi),collision_hulls=len(colliders),nanite=True,
    source_blend=str(SOURCE/'Dungeon_VentFreight.blend'),source_object=original,
    source_sha256=hashlib.sha256((SOURCE/'Dungeon_VentFreight.blend').read_bytes()).hexdigest(),
    pivot_source_m=list(origin),tests_run=False,rendered=False)
(ROOT/'Authored/manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('PALLET_JACK_EXTRACTED',json.dumps(dict(triangles=record['triangles'],bounds=record['bounds_m'],materials=list(mapping))),flush=True)
