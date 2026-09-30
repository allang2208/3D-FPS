import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_SurfaceReform42.blend'),use_scripts=False)
names=json.loads((O/'model.json').read_text())['parts']
data={o.name:[m.name if m else None for m in o.data.materials] for o in bpy.data.objects if o.type=='MESH' and (o.name in names or o.name.endswith('_S42') or any(m and m.name=='M_LMG201_F37_Interior' for m in o.data.materials))}
(O/'source_materials.json').write_text(json.dumps(data,indent=2));print(json.dumps(data),flush=True)
