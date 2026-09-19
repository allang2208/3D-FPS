import bpy
import bmesh
import json
import math
from mathutils import Vector
from pathlib import Path

root = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root / 'handbrain_detailed_v02.glb'))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in meshes:
    bm=bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
    o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
points = [o.matrix_world @ Vector(corner) for o in meshes for corner in o.bound_box]
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
center = (low+high)/2
height = high.z-low.z
scale = 2.0/height
for o in meshes:
    o.location = (o.location - Vector((center.x, center.y, low.z))) * scale
    o.scale *= scale
    for p in o.data.polygons:
        p.use_smooth = True
report = {'vertices':sum(len(o.data.vertices) for o in meshes), 'polygons':sum(len(o.data.polygons) for o in meshes), 'triangles':sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons), 'mesh_objects':len(meshes), 'textures':[{'name':i.name,'size':list(i.size)} for i in bpy.data.images], 'uv_layers':[len(o.data.uv_layers) for o in meshes], 'finite_vertices':all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co), 'rigged':False, 'display_height_m':2.0}
(root/'model_report.json').write_text(json.dumps(report, indent=2))
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.export_scene.fbx(filepath=str(root/'handbrain_detailed_v02.fbx'), use_selection=True, path_mode='COPY', embed_textures=True, add_leaf_bones=False)
bpy.ops.export_scene.gltf(filepath=str(root/'handbrain_detailed_v02_clean.glb'), use_selection=True, export_format='GLB')
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=1000
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.18,0.18,0.18,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.5
for loc,power,size in [((3,-4,5),700,4),((-4,-1,3),450,3),((1,4,4),600,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object
    light.data.energy=power
    light.data.shape='DISK'
    light.data.size=size
    light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-0.01))
floor=bpy.context.object
mat=bpy.data.materials.new('Studio grey')
mat.diffuse_color=(0.16,0.16,0.16,1)
floor.data.materials.append(mat)
bpy.ops.object.camera_add()
camera=bpy.context.object
camera.data.type='ORTHO'
camera.data.ortho_scale=2.5
scene.camera=camera
scene.view_settings.view_transform='AgX'
for name,loc in [('front',(0,-6,1.15)),('right',(6,0,1.15)),('back',(0,6,1.15)),('left',(-6,0,1.15)),('hero',(4,-6,2.7))]:
    camera.location=loc
    camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(root/('render_'+name+'.png'))
    bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'handbrain_detailed_v02.blend'))
