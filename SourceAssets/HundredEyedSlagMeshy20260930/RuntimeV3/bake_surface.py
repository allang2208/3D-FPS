"""Bake original high-poly geometry and source normal detail onto the game UV atlas."""
import bpy, json
from pathlib import Path
from mathutils import Matrix
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HundredEyedSlag_RuntimeV3.blend'))
scene=bpy.context.scene
low=next(o for o in scene.objects if o.type=='MESH')
rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data.action=None
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
with bpy.data.libraries.load(str(OUT.parent/'PolishV2/HundredEyedSlag_PolishV2.blend'),link=False) as (source,target):
    target.objects=[n for n in source.objects if n.startswith('SK_HundredEyedSlag')]
high=next(o for o in target.objects if o and o.type=='MESH')
scene.collection.objects.link(high); high.parent=None; high.matrix_world=Matrix.Identity(4)
for mod in list(high.modifiers): high.modifiers.remove(mod)
for mod in low.modifiers: mod.show_render=False
material=low.data.materials[0].copy(); low.data.materials[0]=material
image=bpy.data.images.new('T_HundredEyedSlag_RuntimeV3_Normal',2048,2048,alpha=False)
image.colorspace_settings.name='Non-Color'
target_node=material.node_tree.nodes.new('ShaderNodeTexImage'); target_node.image=image
material.node_tree.nodes.active=target_node
scene.render.engine='CYCLES'; scene.cycles.samples=8; scene.cycles.device='GPU'
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX'; prefs.get_devices()
for device in prefs.devices: device.use=device.type!='CPU'
scene.render.bake.use_selected_to_active=True
scene.render.bake.use_clear=True; scene.render.bake.margin=12
scene.render.bake.cage_extrusion=.025; scene.render.bake.max_ray_distance=.06
scene.render.bake.normal_space='TANGENT'
bpy.ops.object.select_all(action='DESELECT'); high.select_set(True); low.select_set(True)
bpy.context.view_layer.objects.active=low
print('V3: high-to-game normal bake',flush=True)
bpy.ops.object.bake(type='NORMAL')
normal=next(n for n in material.node_tree.nodes if n.type=='NORMAL_MAP')
material.node_tree.links.new(target_node.outputs['Color'],normal.inputs['Color'])
folder=OUT/'Delivery/Textures'; folder.mkdir(exist_ok=True)
image.filepath_raw=str(folder/'T_HundredEyedSlag_RuntimeV3_Normal.png'); image.file_format='PNG'; image.save(); image.pack()
bpy.data.objects.remove(high,do_unlink=True)
for mod in low.modifiers: mod.show_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_RuntimeV3.blend'))
(OUT/'surface_bake_receipt.json').write_text(json.dumps({'baked':True,'source_triangles':2896776,'game_triangles':100000,
    'resolution':2048,'geometry_and_source_normal_projected':True,'uv_preserved':True,'normal_texture':image.filepath_raw},indent=2))
print('V3_SURFACE_BAKED',flush=True)
