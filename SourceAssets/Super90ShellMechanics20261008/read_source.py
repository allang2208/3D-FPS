import bpy,json,math
from pathlib import Path
from collections import Counter
from mathutils import Vector
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_Super90'];out={'meshes':[],'clips':{}}
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 weights=Counter();mats=Counter()
 for v in ob.data.vertices:
  for g in v.groups:
   if g.weight>.5:weights[ob.vertex_groups[g.group].name]+=1
 for p in ob.data.polygons:mats[ob.data.materials[p.material_index].name]+=1
 out['meshes'].append({'name':ob.name,'verts':len(ob.data.vertices),'materials':dict(mats),'weights':dict(weights)})
for name in ('A_Super90_idle','A_Super90_inspect','A_Super90_reload_one','A_Super90_reload_full','A_Super90_fire'):
 a=bpy.data.actions.get(name)
 if not a:continue
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
  bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
  m=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['WPN_bolt'].matrix
  rows.append({'frame':f,'pos':list(m.translation),'rotation':list(m.to_quaternion())})
 first=Vector(rows[0]['pos']);travel=max((Vector(x['pos'])-first).length*100 for x in rows)
 out['clips'][name]={'count':len(rows),'travel_cm':travel,'samples':rows[::max(1,len(rows)//8)]}
(O/'source_parts.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out),flush=True)
