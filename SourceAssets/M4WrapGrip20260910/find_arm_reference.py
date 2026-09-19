import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene

def sample(name,f):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
p=sample('M4_MAT_reload_empty',80);target=p['hand_l'];print('CURRENT',{n:list(p[n].translation) for n in ['hand_l','lowerarm_l','upperarm_l','clavicle_l']},flush=True);rows=[]
for act,end in [('M4_idle',0),('M4_reload',188),('M4_equip',62)]:
 for f in range(0,end+1,2):
  q=sample(act,f);delta=target@q['hand_l'].inverted();elbow=(delta@q['lowerarm_l']).translation;shoulder=(delta@q['upperarm_l']).translation
  score=max(0,elbow.x-(target.translation.x-.12))*10+max(0,elbow.z-(target.translation.z-.12))*10+max(0,shoulder.x+.25)*5+max(0,shoulder.z+.20)*5+(elbow-Vector((-.25,-.08,-.25))).length
  rows.append(dict(source=act,frame=f,score=score,elbow=list(elbow),shoulder=list(shoulder)))
rows.sort(key=lambda r:r['score']);print(rows[:12]);(O/'arm_reference_candidates.json').write_text(json.dumps(rows,indent=2))
