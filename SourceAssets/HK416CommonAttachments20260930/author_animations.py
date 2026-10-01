"""HK416 grip families with independent drum contact and bolt-release timing."""
import bpy,json,math,argparse,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
parser=argparse.ArgumentParser();scope=parser.add_mutually_exclusive_group();scope.add_argument('--only-drum-empty',action='store_true');scope.add_argument('--only-standard-empty',action='store_true');scope.add_argument('--only-inspect',action='store_true');parser.add_argument('--output-directory',type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
only_kind='drum_reload_empty' if args.only_drum_empty else 'reload_empty' if args.only_standard_empty else None
OUT=args.output_directory or O;OUT.mkdir(parents=True,exist_ok=True)
def author_inspection():
 sys.path.insert(0,str(S/'HK416Inspect20261001'))
 from author_inspect import author
 return author(OUT)
if args.only_inspect:
 authored=author_inspection();print('HK416_INSPECT_EXPORT_COMPLETE',len(authored['clips']),flush=True);sys.exit(0)
sys.path.insert(0,str(O))
from drum_empty_contact import align_release_hand
I=json.loads((S/'M16UniversalAttachments20260920/authoring.json').read_text());M=json.loads((O/'models.json').read_text())
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
with bpy.data.libraries.load(str(S/'M4SlapImpact20260910/M4_Hand_MAT_Editable.blend'),link=False) as (src,dst):dst.actions=['M4_MAT_reload_empty']
slap=[pose(r,dst.actions[0],j*.5) for j in range(325)]
bpy.ops.wm.open_mainfile(filepath=str(S/'HK416Reworked20260930/HK416_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene;scene.render.fps=60;r.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
left=[n for n in rest if n.endswith('_l')]
clips={'idle':180,'aim':2,'fire':46,'aim_fire':46,'equip':38,'reload':126,'reload_empty':162,'SprintEnter':18,'SprintLoop':36,'SprintExit':18,'QuickCombat':108}
names={'equip':'equip_charge','SprintEnter':'sprint_enter','SprintLoop':'sprint_loop','SprintExit':'sprint_exit','QuickCombat':'quick_melee'}
cache={k:[pose(r,bpy.data.actions['HK416_base_'+names.get(k,k)],j*.5) for j in range(e*2+1)] for k,e in clips.items()}
for j,p in enumerate(cache['reload_empty']):align_release_hand(p,j*.5,slap[j],parents,release_frame=130.)
shift=Vector((0,0,0))
for kind in ('reload','reload_empty'):
 end=148 if kind=='reload_empty' else clips[kind];poses=[]
 for j in range(end*2+1):
  f=j*.5;old=drum[kind][min(j,len(drum[kind])-1)]
  p={n:old[n]@oldrest[n].inverted()@rest[n] if n in old else None for n in rest}
  for n in rest:
   if p[n] is None:p[n]=p[parents[n]]@local[n]
  for n in left:p[n].translation+=p['WPN_root'].to_3x3()@shift
  # The drum donor already strikes at 116 and then closes its bolt.
  # Mixing the standard-magazine tail here delays that strike to 130;
  # it also replaces the drum's 148-frame recovery with a 162-frame tail.
  if kind=='reload_empty':align_release_hand(p,f,slap[j+28],parents)
  poses.append(p)
 cache['drum_'+kind]=poses;clips['drum_'+kind]=end
report={'reference':'HK416 native contact / complete M4SlapImpact left arm; standard and extended strike 130 end 162, drum strike 116 end 148','testing':'Runtime not run','clips':{}}
def bake(family,kind,poses):
 end=clips[kind];action_name='HK416_'+family+'_'+names.get(kind,kind)
 if action_name in bpy.data.actions:bpy.data.actions[action_name].name='REFERENCE_'+action_name
 a=bpy.data.actions.new(action_name);a.use_fake_user=True;r.animation_data.action=a
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
 dest=OUT/'Animations'/family;dest.mkdir(parents=True,exist_ok=True);name='A_HK416_'+family+'_'+names.get(kind,kind);file=dest/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
 report['clips'][family+'/'+kind]={'family':family,'kind':kind,'name':name,'file':str(file),'duration':end/60,'source_action':a.name}
 (OUT/'animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('HK416_ATTACHMENT_CLIP',family,kind,flush=True)
 return a
for kind in ('reload_empty','drum_reload','drum_reload_empty'):
 if not only_kind or kind==only_kind:bake('base',kind,cache[kind])
for family in ('drum','vertical','canted','prism','angled'):
 if only_kind and family=='drum':continue
 donor=I['donors'][family];P={n:Matrix(m) for n,m in donor['pose'].items()}
 D=Matrix.Translation(shift) if family=='drum' else Matrix(M['grip_mount'])@Matrix(donor['mount']).inverted()
 held={n:D@P[n] for n in left if n in P}
 for kind,end in clips.items():
  if only_kind and kind!=only_kind:continue
  if family=='vertical' and not kind.startswith('drum_') and kind!='reload_empty':continue
  if family=='drum' and kind in ('reload','reload_empty','drum_reload','drum_reload_empty'):continue
  poses=[]
  for j,base in enumerate(cache[kind]):
   f=j*.5;p={n:m.copy() for n,m in base.items()};w=1.
   if 'reload' in kind:
    start=128 if kind=='drum_reload_empty' else 142 if kind=='reload_empty' else 96
    finish=148 if kind=='drum_reload_empty' else 162 if kind=='reload_empty' else 126
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
 if not only_kind:
  pose(r,bpy.data.actions['HK416_'+('base' if family=='vertical' else family)+'_idle'],0)
  bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('HK416_'+family+'_Animations_Editable.blend')))
if only_kind:
 pose(r,bpy.data.actions['HK416_base_'+only_kind],116 if args.only_drum_empty else 130)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('HK416_DrumEmpty_Editable.blend' if args.only_drum_empty else 'HK416_StandardEmpty_Editable.blend')))
if not only_kind:
 inspection=author_inspection();report['clips'].update(inspection['clips']);report['inspect_reference']=inspection['reference']
 (OUT/'animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HK416_ATTACHMENT_ANIMATIONS_AUTHORED',len(report['clips']),flush=True)
