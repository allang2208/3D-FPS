import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
names=['hand_l','hand_r','index_03_r','middle_03_r','WPN_SOCKET_Magazine','WPN_ChargingHandle','WPN_BoltCatch','WPN_bolt']
print('GUN_BONES',[b.name for b in r.pose.bones if b.name.startswith('WPN')]);print('MESHES',[o.name for o in r.children if o.type=='MESH'])
report={}
for clip,end in [('reload',126),('reload_empty',162),('equip_charge',38)]:
 a=bpy.data.actions['M4_MAT_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[];prev=None;peaks={};localpeaks={}
 for k in range(end*4+1):
  f=k/4;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();inv=r.pose.bones['WPN_root'].matrix.inverted();p={n:inv@r.pose.bones[n].matrix for n in names if n in r.pose.bones};local={b.name:b.matrix_basis.to_quaternion() for b in r.pose.bones if b.name.endswith(('_l','_r'))}
  if prev:
   for n,m in p.items():
    speed=(m.translation-prev[n].translation).length*240;angle=math.degrees(m.to_quaternion().rotation_difference(prev[n].to_quaternion()).angle)*240
    if speed>peaks.get(n,{}).get('speed_m_s',0):peaks[n]={'frame':f,'speed_m_s':speed,'angular_deg_s':angle}
   for n,q in local.items():
    angle=math.degrees(q.rotation_difference(prevlocal[n]).angle)*240
    if angle>localpeaks.get(n,{}).get('angular_deg_s',0):localpeaks[n]={'frame':f,'angular_deg_s':angle}
  rows.append({'frame':f,'bones':{n:{'position':list(m.translation),'rotation':list(m.to_quaternion())} for n,m in p.items()}});prev=p;prevlocal=local
 report[clip]={'frames':rows,'peak_weapon_relative_speed':peaks,'peak_local_angular_speed':localpeaks}
(O/'motion_after.json').write_text(json.dumps(report,indent=2));print('MOTION_AUDIT_DONE')
for o in r.children:
 if o.type=='MESH' and 'Arms' not in o.name:
  print('GROUPS',o.name,{g.name:sum(1 for v in o.data.vertices if any(w.group==g.index and w.weight>.1 for w in v.groups)) for g in o.vertex_groups if 'bolt' in g.name.lower() or 'Charging' in g.name})
