"""Requested M870 reload diagnosis: compare the two corrected source clips."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ReloadContact_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
auth=json.loads((O/'authoring.json').read_text());grasp=Matrix(auth['grasp'])
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False
preserved=[n for n in parents if not under(n,'clavicle_r')]
def poses(name,count):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 rows=[]
 for f in range(count):
  s.frame_set(f);rows.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return rows
result={}
for role,entry in auth['clips'].items():
 count=auth['recipe'][role]['frames'];old=poses(auth['recipe'][role]['input_action'],count);new=poses(entry['action'],count)
 preserved_error=max(abs(old[f][n][i][j]-new[f][n][i][j]) for f in range(count) for n in preserved for i in range(4) for j in range(4))
 drift=angle=0.;held=0
 for f,row in enumerate(new):
  if f<18 or f>=360:continue
  idx=0 if f<60 else min(6,1+(f-60)//50)
  if f>44+idx*50:continue
  rel=row['WPN_Shell'].inverted()@row['hand_r'];held+=1
  drift=max(drift,(rel.translation-grasp.translation).length)
  angle=max(angle,math.degrees(rel.to_quaternion().rotation_difference(grasp.to_quaternion()).angle))
 result[role]={'frames':count,'duration':entry['duration'],'preserved_bones_max_matrix_error':preserved_error,
  'held_frames':held,'hand_to_cartridge_max_translation_error_mm':drift*1000,'hand_to_cartridge_max_rotation_error_deg':angle}
report={'scope':'Source clip matrices only: left chain/weapon/prop retained, all seven held intervals per reload. No game, networking or audio run.',
 'clips':result,'source_check_passed':all(v['preserved_bones_max_matrix_error']<.0001 and v['hand_to_cartridge_max_translation_error_mm']<.01 and v['hand_to_cartridge_max_rotation_error_deg']<.1 for v in result.values())}
(O/'source_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
