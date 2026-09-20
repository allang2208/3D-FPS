"""Reuse complete accepted left-arm chains, including twists and finger poses.
The M16 charging tail and every non-contact reload interval remain its own.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
I=json.loads((O/'authoring.json').read_text());M=json.loads((O/'models.json').read_text())
bpy.context.preferences.filepaths.save_version=0
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,w):
 p,q,s=a.decompose();p1,q1,s1=b.decompose();return Matrix.LocRotScale(p.lerp(p1,w),q.slerp(q1,w),s.lerp(s1,w))
def pose(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
# Cache the accepted complete drum actions before opening the target skeleton.
bpy.ops.wm.open_mainfile(filepath=I['donors']['drum']['source']);r=bpy.data.objects['SK_M4_Infima']
oldrest={b.name:b.matrix_local.copy() for b in r.data.bones}
drum={k:[pose(r,bpy.data.actions['A_M4_DrumContact_'+k],j*.5) for j in range(e*2+1)] for k,e in [('reload',126),('reload_empty',148)]}
bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene;scene.render.fps=60;r.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
left=[n for n in rest if n.endswith('_l')]
clips={'idle':180,'aim':2,'fire':46,'aim_fire':46,'equip':38,'reload':126,'reload_empty':162,'inspect':180,'SprintEnter':18,'SprintLoop':36,'SprintExit':18,'QuickCombat':54}
names={'equip':'equip_charge','SprintEnter':'sprint_enter','SprintLoop':'sprint_loop','SprintExit':'sprint_exit','QuickCombat':'quick_melee'}
cache={k:[pose(r,bpy.data.actions['M16_'+names.get(k,k)],j*.5) for j in range(e*2+1)] for k,e in clips.items()}
shift=Vector(json.loads((S/'M16Gameplay20260919/build.json').read_text())['magazine_contact_shift_m'])
for kind in ('reload','reload_empty'):
 end=clips[kind];poses=[]
 for j in range(end*2+1):
  f=j*.5;old=drum[kind][min(j,len(drum[kind])-1)]
  p={n:old[n]@oldrest[n].inverted()@rest[n] if n in old else None for n in rest}
  for n in rest:
   if p[n] is None:p[n]=p[parents[n]]@local[n]
  for n in left:p[n].translation+=p['WPN_root'].to_3x3()@shift
  # Preserve M16 mechanical pieces that do not exist in the M4 donor.
  if kind=='reload_empty' and f>=88:
   base=cache[kind][j];w=smooth(88,111,f)
   p={n:mix(p[n],base[n],w) for n in rest}
  poses.append(p)
 cache['drum_'+kind]=poses;clips['drum_'+kind]=end
report={'reference':'Accepted M4 VRE whole-arm grasp / M4_DrumContact; M16 right-hand charging handle tail 111..162','testing':'Not run','clips':{}}
def bake(family,kind,poses):
 end=clips[kind];a=bpy.data.actions.new('M16_'+family+'_'+kind);a.use_fake_user=True;r.animation_data.action=a
 # Create channels once, then bulk write dense, quaternion-continuous keys.
 for b in r.pose.bones:
  b.rotation_mode='QUATERNION'
  for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
 curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
 for n in rest:
  values=[];previous=None
  for p in poses:
   m=local[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,sc=m.decompose()
   if previous and q.dot(previous)<0:q.negate()
   previous=q.copy();values.append((loc,q,sc))
  for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(poses))
    c.keyframe_points.foreach_set('co',[x for j,row in enumerate(values) for x in (j*.5,row[field][axis])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 scene.frame_start=0;scene.frame_end=end;scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True);name='A_M16_'+family+'_'+kind;file=dest/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
 report['clips'][family+'/'+kind]={'family':family,'kind':kind,'name':name,'file':str(file),'duration':end/60,'source_action':a.name}
 (O/'animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('M16_ATTACHMENT_CLIP',family,kind,flush=True)
 return a
for kind in ('drum_reload','drum_reload_empty'):bake('base',kind,cache[kind])
for family in ('drum','vertical','canted','prism','angled'):
 donor=I['donors'][family];P={n:Matrix(m) for n,m in donor['pose'].items()}
 D=Matrix.Translation(shift) if family=='drum' else Matrix(M['grip_mount'])@Matrix(donor['mount']).inverted()
 held={n:D@P[n] for n in left if n in P}
 for kind,end in clips.items():
  if family=='drum' and kind in ('reload','reload_empty','drum_reload','drum_reload_empty'):continue
  poses=[]
  for j,base in enumerate(cache[kind]):
   f=j*.5;p={n:m.copy() for n,m in base.items()};w=1.
   if 'reload' in kind:
    start=88 if 'empty' in kind else 96;finish=111 if 'empty' in kind else 126
    w=1-smooth(0,10,f) if f<start else smooth(start,finish,f)
   elif kind.startswith('Sprint'):
    w=0. if kind=='SprintLoop' else 1-smooth(0,end*.45,f) if kind=='SprintEnter' else smooth(end*.55,end,f)
   elif kind in ('equip','inspect'):
    oldheld=cache['idle'][0]['WPN_root'].inverted()@cache['idle'][0]['hand_l']
    distance=(base['hand_l'].translation-(base['WPN_root']@oldheld).translation).length
    w=1-smooth(.025,.075,distance)
   if w>0:
    target={n:p['WPN_root']@h for n,h in held.items()}
    # Blend local complete chain, preserving donor lengths and twist rotations.
    # No isolated wrist move, no finger solving, no twist reset.
    for n in left:
     if n not in target:continue
     parent=parents[n];oldlocal=base[parent].inverted()@base[n]
     newlocal=(target[parent] if parent in target else base[parent]).inverted()@target[n]
     p[n]=p[parent]@mix(oldlocal,newlocal,w)
   poses.append(p)
  bake(family,kind,poses)
 pose(r,bpy.data.actions['M16_'+family+'_idle'],0)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/('M16_'+family+'_Animations_Editable.blend')))
print('M16_ATTACHMENT_ANIMATIONS_AUTHORED',len(report['clips']),flush=True)
