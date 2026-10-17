import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M870UrbanAnimations20261015/M870_Urban_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
def row(name,f):
 r.animation_data.action=bpy.data.actions[name];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(f)
 return {b.name:b.matrix.copy() for b in r.pose.bones}
i=row('A_M870_idle',0);G=r.data.bones['WPN_root'].matrix_local@i['WPN_root'].inverted()
for role,f in [('A_M870_idle',0),('A_M870_reload_full.001',212),('A_M870_inspect.001',75)]:
 p=row(role,f)
 print(role,'gun_delta_degrees',[round(math.degrees(a),1) for a in (G@p['WPN_root']@i['WPN_root'].inverted()@G.inverted()).to_euler()])
 for n in ['upperarm_l','lowerarm_l','hand_l','WPN_bolt']:
  print(n,[round(v,4) for v in (G@p[n]).translation])
 print('hand relative change',[round(math.degrees(a),1) for a in ((p['WPN_root'].inverted()@p['hand_l'])@(i['WPN_root'].inverted()@i['hand_l']).inverted()).to_euler()])
