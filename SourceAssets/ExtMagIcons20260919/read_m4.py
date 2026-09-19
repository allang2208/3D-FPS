import bpy,json
p='D:/FPS3D/FPSGAME/SourceAssets/ExtMagIcons20260919/Icons/ue_m4a1_magazine_ext_mag.blend'
bpy.ops.wm.open_mainfile(filepath=p)
o=next(x for x in bpy.context.scene.objects if x.type=='MESH')
print('UVS',[(u.name,u.active_render) for u in o.data.uv_layers])
for m in o.data.materials:
 print('MAT',m.name)
 for n in m.node_tree.nodes:
  print(n.type, n.name, n.image.filepath if n.type=='TEX_IMAGE' and n.image else '')
  if n.type=='BSDF_PRINCIPLED':print([(s.name,str(s.default_value)) for s in n.inputs if s.name in ['Metallic','Roughness','Base Color']])
 for l in m.node_tree.links:print('LINK',l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name)
