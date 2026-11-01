import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'FactoryIconSources.blend'))
o=bpy.data.objects['SM_ThunderGodHammer_head_mount_factory'];s=bpy.context.scene
print('SETTINGS',s.render.engine,s.view_settings.view_transform,s.view_settings.exposure,s.view_settings.gamma,[(v.name,str(v.material_override)) for v in s.view_layers])
print('POLY_MATS',sorted(set(f.material_index for f in o.data.polygons)),[(x.name,x.link,x.material.name) for x in o.material_slots])
for m in [slot.material for slot in o.material_slots]:
 print('MATERIAL',m.name,m.use_nodes)
 print('LINKS',[(l.from_node.type,l.from_socket.name,l.to_node.type,l.to_socket.name) for l in m.node_tree.links])
 print('IMAGES',[(n.image.name,n.image.size[:],n.image.filepath,n.image.has_data) for n in m.node_tree.nodes if n.type=='TEX_IMAGE'])
print('WORLD',[(n.type,n.name) for n in s.world.node_tree.nodes])
print('UVBOUNDS',[(u.name,min(x.uv.x for x in u.data),max(x.uv.x for x in u.data),min(x.uv.y for x in u.data),max(x.uv.y for x in u.data)) for u in o.data.uv_layers])
print('CAMERA',str(s.camera),s.camera.matrix_world[:],s.camera.data.ortho_scale)
print('RENDER',s.render.use_sequencer,s.sequence_editor,s.render.use_simplify,s.render.use_compositing)
print('SLOTS',[(x.name,x.link,x.material.name) for x in o.material_slots]);print('UV',[(u.name,u.active_render) for u in o.data.uv_layers])
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'GuanLeiRebuildV2/GuanLeiSeatV2_IconSource.blend'))
o=bpy.data.objects['SM_ThunderHammer_GuanLeiSeatV2'];s=bpy.context.scene
print('LEGENDARY',[(x.name,x.type,list(x.location),list(x.scale)) for x in s.objects])
print('BOUNDS',[[min(v.co[i] for v in o.data.vertices) for i in range(3)],[max(v.co[i] for v in o.data.vertices) for i in range(3)]],list(o.location),list(o.scale))
print('CAMERA2',str(s.camera),s.camera.matrix_world[:],s.camera.data.ortho_scale)
