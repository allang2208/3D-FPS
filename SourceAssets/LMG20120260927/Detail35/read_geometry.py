import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Body.fbx'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');root=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted();out=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 group={g.index:g.name for g in ob.vertex_groups}
 for i,mat in enumerate(ob.data.materials):
  if not any(k in mat.name for k in ['Hardware','Rail','Charging','Carry','Inside']):continue
  faces=[p for p in ob.data.polygons if p.material_index==i];ids=sorted({v for p in faces for v in p.vertices})
  if not ids:continue
  v=np.array([root@ob.matrix_world@ob.data.vertices[x].co for x in ids]);weights={}
  for vi in ids:
   for g in ob.data.vertices[vi].groups:weights[group[g.group]]=weights.get(group[g.group],0)+g.weight
  out.append({'material':mat.name,'faces':len(faces),'bounds':np.stack([v.min(0),v.max(0)]).tolist(),'weights':weights})
(O/'native_regions.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
