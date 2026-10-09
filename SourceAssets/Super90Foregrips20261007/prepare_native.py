"""Capture the editable rig's bind bases and fore-end attachment surfaces."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_Super90_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
data={'rest':{b.name:list(map(list,b.matrix_local)) for b in r.data.bones},'idle':{b.name:list(map(list,b.matrix)) for b in r.pose.bones},'rig_world':list(map(list,r.matrix_world))}
ob=bpy.data.objects['Super90_body'];rows=json.loads((O.parent/'Super90Optics20261007/body_regions.json').read_text());region=next(row for row in rows if row['id']==0)
vertices=[ob.data.vertices[i].co for i in region['vertices']]
data['foreend_sections']={str(y):[[min(v[k] for v in sorted(vertices,key=lambda v:abs(v.y-y))[:24]),max(v[k] for v in sorted(vertices,key=lambda v:abs(v.y-y))[:24])] for k in range(3)] for y in (.075,.10,.125,.15,.175,.20,.225)}
(O/'binding.json').write_text(json.dumps(data,indent=2))
print('SUPER90_FOREEND_BINDING',json.dumps({'hand':list(r.pose.bones['hand_l'].matrix.translation),'gun':list(r.pose.bones['WPN_root'].matrix.translation),'foreend_sections':data['foreend_sections']}),flush=True)
