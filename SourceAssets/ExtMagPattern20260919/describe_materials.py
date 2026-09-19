import bpy,json
from pathlib import Path
O=Path(__file__).parent;r={}
for g in ['M4','AKM','QBZ']:
 bpy.ops.wm.open_mainfile(filepath=str(O/(g+'_ExtMag_Editable.blend')))
 m=bpy.data.objects['SM_ExtMag_'+g+'40'].data.materials[0]
 r[g]={'material':m.name,'images':[(n.image.name,n.image.filepath,bool(n.image.packed_file)) for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []}
(O/'material_sources.json').write_text(json.dumps(r,indent=2))
