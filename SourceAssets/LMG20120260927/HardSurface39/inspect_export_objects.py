import bpy,json
from pathlib import Path
O=Path(__file__).parent
out={}
for name in ['After_BipodBase','Before_BipodLegA','Before_BipodLegB','Current_FrontSight']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/(name+'.fbx')),use_anim=False)
 out[name]=[]
 for ob in bpy.data.objects:
  if ob.type!='MESH':continue
  xyz=[ob.matrix_world@v.co for v in ob.data.vertices]
  out[name].append({'name':ob.name,'vertices':len(xyz),'bounds':[[min(v[i] for v in xyz) for i in range(3)],[max(v[i] for v in xyz) for i in range(3)]]})
(O/'export_objects.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
