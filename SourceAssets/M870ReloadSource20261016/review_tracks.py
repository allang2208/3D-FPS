"""Requested source comparison: contacts, continuity, native lengths and scope."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ReloadSource_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;auth=json.loads((O/'authoring.json').read_text())
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False
def poses(name,count):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];out=[]
 for f in range(count):s.frame_set(f);out.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return out
R={}
for role,entry in auth['clips'].items():
 count=auth['recipe'][role]['frames'];old=poses(auth['recipe'][role]['input_action'],count);new=poses(entry['action'],count)
 protected=[n for n in rest if not under(n,'clavicle_r')]
 error=max(abs(a[n][i][j]-b[n][i][j]) for a,b in zip(old,new) for n in protected for i in range(4) for j in range(4))
 lengths=[];steps=[]
 for f,row in enumerate(new):
  if f>0:steps.append({'frame':f,'hand_step_mm':(row['hand_r'].translation-new[f-1]['hand_r'].translation).length*1000})
  if not 18<=f<360:continue
  for a,b in [('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]+[(n,parents[n]) for n in rest if under(n,'hand_r') and n!='hand_r']:
   lengths.append(abs((row[a].translation-row[b].translation).length-(rest[a].translation-rest[b].translation).length)*1000)
 endpoints=max(abs(old[f][n][i][j]-new[f][n][i][j]) for f in (0,count-1) for n in rest for i in range(4) for j in range(4))
 R[role]={'frames':count,'duration':entry['duration'],'protected_max_matrix_error':error,'endpoint_max_matrix_error':endpoints,'native_segment_length_error_max_mm':max(lengths),'largest_hand_steps':sorted(steps,key=lambda x:-x['hand_step_mm'])[:5],'boundaries':[row for row in steps if row['frame'] in (18,44,60,110,160,210,260,310,360,372)]}
(O/'source_review.json').write_text(json.dumps(R,indent=2));print(json.dumps(R),flush=True)
