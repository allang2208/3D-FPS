import bpy, json, sys
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191Hero20260913/QBZ191_Hero_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
def pose(name,f):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
p=pose('QBZ191_base_idle',0);W=p['WPN_root'];inv=W.inverted()
def bounds(pts):return {'min':[min(v[j] for v in pts) for j in range(3)],'max':[max(v[j] for v in pts) for j in range(3)]}
parts={};vertices={}
for ob in bpy.data.collections['QBZ_LOW'].objects:
 bone=ob.get('bone')
 if bone not in ['WPN_SOCKET_Magazine','WPN_ChargingHandle']:continue
 pts=[inv@p[bone]@r.data.bones[bone].matrix_local.inverted()@v.co for v in ob.data.vertices]
 vertices[bone]=[list(v) for v in pts]
 parts[bone]={'object':ob.name,**bounds(pts)}
 if 'Magazine' in bone:
  parts[bone]['sections']={str(z):bounds([v for v in pts if abs(v.z-z)<.008]) for z in [-.09,-.06,-.03,0]}
fit=json.loads((S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
G=Matrix(fit['grip_in_root']);H=Matrix(fit['hand_in_root'])
parts['donor_hand_in_grip']=[list(v) for v in G.inverted()@H]
parts['current']={}
for name,f in [('QBZ191_Seated_base_reload',95),('QBZ191_base_equip_charge',12)]:
 q=pose(name,f);I=q['WPN_root'].inverted()
 parts['current'][name]={n:[list(v) for v in I@q[n]] for n in ['hand_l','hand_r','WPN_SOCKET_Magazine','WPN_ChargingHandle']}
 if 'equip' in name:
  parts['charge_fingers']={n:list(I@q[n].translation) for n in q if n.startswith(('thumb','index','middle','ring','pinky')) and n.endswith('_r')}
pts=[Vector(v) for v in vertices['WPN_ChargingHandle'] if v[0]<-.029]
parts['handle_knob']=bounds(pts)
(O/'geometry.json').write_text(json.dumps({'parts':parts,'vertices':vertices},indent=2))
print(json.dumps(parts,indent=2),flush=True)
