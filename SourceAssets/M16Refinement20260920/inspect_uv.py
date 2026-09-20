import bpy,json
from pathlib import Path
O=Path(__file__).parent;out={}
for label,path in [('source',O.parent/'M16UniversalAttachments20260920/Sources/holographic.fbx'),('installed_source',O/'Meshes/SM_M16_holographic.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));o=next(o for o in bpy.context.scene.objects if o.type=='MESH');row={}
 for mi,mat in enumerate(o.data.materials):
  loops=[j for p in o.data.polygons if p.material_index==mi for j in p.loop_indices];row[mat.name]={}
  for uv in o.data.uv_layers:
   values=[uv.data[j].uv for j in loops];row[mat.name][uv.name]=[[min(v[i] for v in values),max(v[i] for v in values)] for i in range(2)] if values else []
 out[label]=row
(O/'uv_inspection.json').write_text(json.dumps(out,indent=2));print('UV_INSPECTED',flush=True)
