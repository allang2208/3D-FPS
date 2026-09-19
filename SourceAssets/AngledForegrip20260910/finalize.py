import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
p=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(p/'AngledForegrip_M4_Editable.blend'))
s=bpy.context.scene
if (p/'foregrip_raw.glb').exists():
 col=bpy.data.collections.get('5080_RAW_REFERENCE')
 if not col:col=bpy.data.collections.new('5080_RAW_REFERENCE');s.collection.children.link(col)
 if not len(col.objects):
  bpy.ops.import_scene.gltf(filepath=str(p/'foregrip_raw.glb'))
  for obj in list(bpy.context.selected_objects):
   for c in list(obj.users_collection):c.objects.unlink(obj)
   col.objects.link(obj)
 col.hide_viewport=True;col.hide_render=True
used=[]
for m in [bpy.data.materials.get('Body.001'),bpy.data.materials.get('Grip Default.001')]:
 for node in m.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image:
   f=Path(bpy.path.abspath(node.image.filepath));assert f.exists(),f
   used.append({'material':m.name,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'colorspace':node.image.colorspace_settings.name})
   node.image.pack()
(p/'material_provenance.json').write_text(json.dumps(used,indent=2))
s.camera.location=(2.1,-4,1.65);s.camera.data.ortho_scale=2.85
s.camera.rotation_euler=(Vector((0,0,-.025))-s.camera.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.select_all(action='DESELECT')
for o in s.objects:
 if o.name.startswith('FG_'):o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['FG_Frame_M4Body']
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':
  area.spaces.active.region_3d.view_perspective='CAMERA'
  area.spaces.active.shading.type='MATERIAL'
  area.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=str(p/'AngledForegrip_M4_Editable.blend'))
print('PACKED_SOURCE_OK',len(used))
