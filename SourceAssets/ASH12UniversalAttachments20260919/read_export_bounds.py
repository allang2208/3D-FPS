"""Measure the nine exported FBX meshes as the authoritative repair bounds."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;models=json.loads((O/'models.json').read_text())
out={}
for key,part in models['parts'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=part['file'])
 pts=[ob.matrix_world@v.co for ob in bpy.context.scene.objects if ob.type=='MESH' for v in ob.data.vertices]
 # Blender FBX meter-space -> UE centimeters; Y is reflected on import.
 pts=[(v.x*100,-v.y*100,v.z*100) for v in pts]
 low=[min(v[i] for v in pts) for i in range(3)];high=[max(v[i] for v in pts) for i in range(3)]
 out[key]={'min':low,'max':high,'vertices':len(pts)}
(O/'export_bounds.json').write_text(json.dumps(out,indent=2))
print('ASH_EXPORT_BOUNDS '+json.dumps(out),flush=True)
