import bpy,math,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;out={}
for clip,end in [('reload',126),('reload_empty',162)]:
 a=bpy.data.actions['A_M4_DrumThrow_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];prev={};steps=[]
 for k in range(end*2+1):
  s.frame_set(k//2,subframe=(k%2)/2);bpy.context.view_layer.update()
  for b in r.pose.bones:
   if 'arm' in b.name:
    q=b.matrix_basis.to_quaternion()
    if b.name in prev:
     x=math.degrees(prev[b.name].rotation_difference(q).angle);steps.append((min(x,360-x),k/2,b.name))
    prev[b.name]=q
 out[clip]=sorted(steps,reverse=True)[:15]
 assert out[clip][0][0]<45,(clip,out[clip][0])
(O/'twist_steps.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
