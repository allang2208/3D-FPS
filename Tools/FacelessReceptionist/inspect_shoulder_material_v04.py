import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V04.blend'))
for name in ['Receptionist_ShoulderYoke','Receptionist_Blazer_Continuous']:
 o=bpy.data.objects[name]
 print(name,'slots',[(s.link,s.material.name if s.material else None) for s in o.material_slots],'mesh_mats',[m.name for m in o.data.materials], 'indices',list(set(p.material_index for p in o.data.polygons)))
 print('UV',[(u.name,u.active_render) for u in o.data.uv_layers])
 for mat in o.data.materials:
  print('MAT',mat.name)
  for node in mat.node_tree.nodes:
   if node.type=='TEX_IMAGE':print('IMAGE',node.image.name,node.image.filepath,tuple(node.image.pixels[:3]))
   if node.type=='NORMAL_MAP':print('NORMAL',node.inputs['Strength'].default_value,node.uv_map)
  print('LINKS',[(l.from_node.type,l.from_socket.name,l.to_node.type,l.to_socket.name) for l in mat.node_tree.links])
