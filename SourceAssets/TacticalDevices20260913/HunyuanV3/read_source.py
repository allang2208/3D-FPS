import bpy,json
from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets\TacticalDevices20260913\HunyuanV3')
bpy.ops.wm.open_mainfile(filepath=str(p/'Flashlight_Hunyuan_Editable.blend'))
for ob in bpy.data.objects:
 if ob.type=='MESH':
  print('SOURCE',ob.name,len(ob.data.vertices),list(ob.dimensions))
  for m in ob.data.materials:
   print('MATERIAL',m.name)
   for n in m.node_tree.nodes:
    if n.type=='TEX_IMAGE':print('IMAGE',n.image.name,list(n.image.size),[(l.to_node.type,l.to_socket.name) for l in n.outputs['Color'].links])
