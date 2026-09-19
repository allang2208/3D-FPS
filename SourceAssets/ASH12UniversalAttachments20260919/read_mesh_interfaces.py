import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;data=json.loads((O/'sources.json').read_text());I=json.loads((O/'authoring_inputs.json').read_text());result={}
for key,entry in data.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=entry['fbx'])
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];points=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 if key=='angled':points=[Matrix(I['donors']['angled']['mount']).inverted()@v for v in points]
 def bounds(pp):return [[min(v[i] for v in pp),max(v[i] for v in pp)] for i in range(3)] if pp else None
 result[key]={'bounds':bounds(points),'at_mount':bounds([p for p in points if abs(p.z)<.006]),'slots':[[m.name for m in o.data.materials] for o in obs],'uvs':[[l.name for l in o.data.uv_layers] for o in obs]}
(O/'interfaces.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
