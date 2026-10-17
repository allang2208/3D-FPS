"""Requested right-hand diagnosis on current native skin and both source clips."""
import bpy,json,gzip,math,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;stage='before' if '--before' in sys.argv else 'after'
source=O.parent/'M870Super90Sprint20261016/M870_Super90Sprint_Editable.blend' if stage=='before' else O/'M870_ReloadWrist_Editable.blend'
authdir=O.parent/'M870ReloadContact20261016' if stage=='before' else O
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;auth=json.loads((authdir/'authoring.json').read_text())
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
rf=rest['hand_r'].translation-rest['lowerarm_r'].translation
def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False
def sample(name,count):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];out=[]
 for f in range(count):s.frame_set(f);out.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return out
report={}
for role,entry in auth['clips'].items():
 count=round(entry['duration']*60)+1;rows=sample(entry['action'],count)
 old=sample(auth['recipe'][role]['input_action'],count) if stage=='after' else rows
 protected=[n for n in rest if not under(n,'clavicle_r')]
 fixed=max(abs(a[n][i][j]-b[n][i][j]) for a,b in zip(rows,old) for n in protected for i in range(4) for j in range(4))
 def held(f):
  if f<18 or f>=360:return False
  index=0 if f<60 else min(6,1+(f-60)//50)
  return f<=44+index*50
 hand=max((a['hand_r'].translation-b['hand_r'].translation).length*1000 for f,(a,b) in enumerate(zip(rows,old)) if held(f))
 bends=[];translation=[];bone_lengths=[];steps=[];hand_steps=[]
 for f,row in enumerate(rows):
  if f<15 or f>360:continue
  hd=row['hand_r']@rest['hand_r'].inverted();fore=row['hand_r'].translation-row['lowerarm_r'].translation
  bends.append(math.degrees((hd.to_quaternion()@rf).angle(fore)))
  for n in rest:
   if under(n,'hand_r') and n!='hand_r':
    loc=row[parents[n]].inverted()@row[n];rl=rest[parents[n]].inverted()@rest[n]
    translation.append((loc.translation-rl.translation).length*1000)
  bone_lengths.extend([abs(fore.length-rf.length)*1000,abs((row['lowerarm_r'].translation-row['upperarm_r'].translation).length-(rest['lowerarm_r'].translation-rest['upperarm_r'].translation).length)*1000])
  if f>0:
   steps.append((row['lowerarm_r'].translation-rows[f-1]['lowerarm_r'].translation).length*1000)
   if f<360:hand_steps.append((row['hand_r'].translation-rows[f-1]['hand_r'].translation).length*1000)
 report[role]={'frames':count,'duration':entry['duration'],'preserved_max_matrix_error':fixed,'held_hand_position_error_mm':hand,
  'active_wrist_bend_max_degrees':max(bends),'active_digit_base_error_max_mm':max(translation),'active_bone_length_error_max_mm':max(bone_lengths),'elbow_frame_step_max_mm':max(steps),'loading_hand_frame_step_max_mm':max(hand_steps)}
(O/(stage+'_source_review.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if '--metrics-only' in sys.argv:raise SystemExit
for ob in list(s.objects):
 if ob.type in ('CAMERA','LIGHT') or (ob.type=='MESH' and ('V7' in ob.name or 'BareArm' in ob.name)):bpy.data.objects.remove(ob,do_unlink=True)
with gzip.open(O/'native_arms.json.gz','rt',encoding='utf-8') as f:d=json.load(f)
faces=[f for f in d['faces'] if any(sum(w for n,w in d['weights'][i].items() if n.endswith('_r'))>.5 for i in f)]
me=bpy.data.meshes.new('Current native right arm');me.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in d['vertices']],[],faces);me.update()
arm=bpy.data.objects.new('CurrentNativeRightArm',me);s.collection.objects.link(arm)
for p in me.polygons:p.use_smooth=True
for n in {n for w in d['weights'] for n in w}:arm.vertex_groups.new(name=n)
for i,w in enumerate(d['weights']):
 for n,v in w.items():arm.vertex_groups[n].add([i],v,'REPLACE')
arm.parent=r;arm.matrix_parent_inverse=Matrix.Identity(4);arm.matrix_basis=Matrix.Identity(4);arm.modifiers.new('Current native weights','ARMATURE').object=r
for ob in s.objects:
 if ob.type=='MESH':ob.hide_render=False;ob.color=(.65,.35,.20,1) if ob==arm else (.8,.025,.01,1) if ob.name=='M870_ReloadShell' else (.1,.12,.14,1)
cam=bpy.data.objects.new('DiagnosticCamera',bpy.data.cameras.new('DiagnosticCamera'));s.collection.objects.link(cam);s.camera=cam
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1000;s.render.resolution_y=760;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD'
if not s.world:s.world=bpy.data.worlds.new('DiagnosticWorld')
s.world.color=(.08,.08,.08);cam.data.type='ORTHO';cam.data.ortho_scale=.45
for role,f,side in [('reload_continuous',18,'side'),('reload_continuous',30,'side'),('reload_continuous',30,'palm'),('reload_continuous',44,'side'),('reload_continuous',54,'side'),('reload_full',390,'side')]:
 a=bpy.data.actions[auth['clips'][role]['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f)
 center=r.pose.bones['hand_r'].matrix.translation
 cam.location=center+Vector((-.28,.20,.27) if side=='side' else (.25,-.30,-.15));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(O/f'{stage}_{role}_{f}_{side}.png');bpy.ops.render.render(write_still=True)
# Author first-person framing from the retained M870 reference; this is not
# an interactive game capture. Include the exposed arm root in this view.
idle=json.loads((O.parent/'M870AKMArmSupport20261016/authoring.json').read_text())['clips']['idle']['action']
a=bpy.data.actions[idle];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
canon=r.data.bones['WPN_root'].matrix_local@r.pose.bones['WPN_root'].matrix.inverted()
transform=canon.inverted();cam.data.type='PERSP';cam.data.lens=25;cam.data.clip_start=.005
cam.location=transform@Vector((-.105,-.30,-.665));cam.rotation_euler=(transform.to_3x3()@Vector((0,1,0))).to_track_quat('-Z','Y').to_euler()
for f in (30,44,54):
 a=bpy.data.actions[auth['clips']['reload_continuous']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f)
 s.render.filepath=str(O/f'{stage}_first_person_{f}.png');bpy.ops.render.render(write_still=True)
print('M870_RELOAD_WRIST_SOURCE_REVIEW',stage,flush=True)
