import bpy,json
from pathlib import Path
p=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend')
r={}
for o in bpy.data.objects:
 if o.type=='MESH':
  r[o.name]=[m.name for m in o.data.materials if m]
mats={m.name:[{'image':n.image.filepath,'node':n.name} for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] for m in bpy.data.materials if m.use_nodes}
(p/'source_materials.json').write_text(json.dumps({'objects':r,'materials':mats},indent=2))
print('SOURCE_INSPECTED')
