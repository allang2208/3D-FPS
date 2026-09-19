"""Keep a distinct cleaned derivative of the actual 5080 mesh."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
p=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(p/'foregrip_raw.glb'))
obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in obs:o.select_set(True)
bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=bpy.context.object
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
orig=len(o.data.polygons)
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
# AI mesh contains singular junctions that block edge-collapse decimation.
# A fine voxel pass consolidates this topology before the low-poly reduction.
o.data.remesh_voxel_size=.003
bpy.ops.object.voxel_remesh()
if len(o.data.polygons)>16000:
 mod=o.modifiers.new('Preserve silhouette reduction','DECIMATE');mod.ratio=16000/len(o.data.polygons);bpy.ops.object.modifier_apply(modifier=mod.name)
mod=o.modifiers.new('Restrained surface smoothing','SMOOTH');mod.factor=.15;mod.iterations=2
with bpy.data.libraries.load(str(p/'AngledForegrip_M4_Editable.blend'),link=False) as (a,b):b.materials=['Body.001']
m=bpy.data.materials.get('Body.001');o.data.materials.clear();o.data.materials.append(m)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
for uv in o.data.uv_layers.active.data:uv.uv=(.53+uv.uv.x*.12,.79+uv.uv.y*.05)
for f in o.data.polygons:f.use_smooth=True
o.name='FG_5080_Cleaned_M4Material'
bpy.ops.wm.save_as_mainfile(filepath=str(p/'Foregrip_5080_Cleaned.blend'))
bpy.ops.export_scene.gltf(filepath=str(p/'Foregrip_5080_Cleaned.glb'),use_selection=True,export_apply=True)
(p/'generated_cleanup.json').write_text(json.dumps({'raw_faces':orig,'cleaned_faces':len(o.data.polygons),'material':m.name,'separate_from_authored_candidate':True},indent=2))
