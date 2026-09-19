"""ASH support-hand families. Preserve every firing-hand and mechanical track."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'VREGripExtensions20260912/ReferenceWorkflow'))
from front_pose import solve_arm
I=json.loads((O/'authoring_inputs.json').read_text());M=json.loads((O/'models.json').read_text())
bpy.context.preferences.filepaths.save_version=0
SOURCE=S/'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend'
def mix(a,b,t):
 p,q,s=a.decompose();p1,q1,s1=b.decompose();return Matrix.LocRotScale(p.lerp(p1,t),q.slerp(q1,t),s.lerp(s1,t))
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*t*(t*(t*6-15)+10)
report={'sources':{'base':str(SOURCE)},'clips':{},'reference':'VREGripExtensions20260912/Delivery/Runtime_Grips.png','sample_rate':120}
for family in ('vertical','canted','prism','angled'):
 bpy.ops.wm.open_mainfile(filepath=str(SOURCE));r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene;scene.render.fps=60
 r.data.pose_position='POSE'
 for file,names in [
  (S/'ASH12TacticalSprint20260919/ASH12_TacticalSprint_Editable.blend',['ASH12_TacticalSprint_'+k for k in ('Enter','Loop','Exit')]),
  (S/'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',['ASH12_QuickCombat_N_Base'])]:
  with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.actions=names
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
 fingers=list(I['donors'][family]['fingers']);names=['clavicle_l','upperarm_l','lowerarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','ik_hand_l']+fingers
 names=[n for n in names if n in rest]
 donor={n:Matrix(v) for n,v in I['donors'][family]['fingers'].items()}
 held=Matrix(M['parts'][family]['mount_in_root'])@Matrix(M['parts'][family]['hand_in_mount'])
 def pose(action,f):
  r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
  return {b.name:b.matrix.copy() for b in r.pose.bones}
 idle=pose(bpy.data.actions['ASH12_idle'],0);oldheld=idle['WPN_root'].inverted()@idle['hand_l']
 clips=[('idle','ASH12_idle',180),('aim','ASH12_aim',2),('fire','ASH12_fire',46),('aim_fire','ASH12_aim_fire',46),('equip','ASH12_equip_charge',38),('reload','ASH12_Reference_reload',144),('reload_empty','ASH12_EmptyReload_RightEdgeReachPullReturn',198),('SprintEnter','ASH12_TacticalSprint_Enter',18),('SprintLoop','ASH12_TacticalSprint_Loop',36),('SprintExit','ASH12_TacticalSprint_Exit',18),('QuickCombat','ASH12_QuickCombat_N_Base',54)]
 for kind,source_name,end in clips:
  source=bpy.data.actions[source_name];samples=[];previous={}
  for j in range(end*2+1):
   f=j*.5;p=pose(source,f);baseline={n:local[n].inverted()@(p[parents[n]].inverted()@p[n]) for n in names}
   w=1.
   if kind.startswith('Sprint'):
    progress=1 if kind=='SprintLoop' else f/end if kind=='SprintEnter' else 1-f/end
    w=1-smooth(0,.45,progress)
   elif kind=='equip':
    distance=(p['hand_l'].translation-(p['WPN_root']@oldheld).translation).length
    w=1-smooth(.025,.075,distance)
   if w>0:
    old=p['WPN_root']@oldheld;new=p['WPN_root']@held
    target=new@old.inverted()@p['hand_l'];H=mix(p['hand_l'],target,w)
    solve_arm(p,rest,H,p['WPN_root']@Matrix(M['parts'][family]['mount_in_root']),w)
    if 'ik_hand_l' in p:p['ik_hand_l']=H.copy()
    for n in fingers:p[n]=p[parents[n]]@local[n]@mix(baseline[n],donor[n],w)
   row={}
   for n in names:
    m=local[n].inverted()@(p[parents[n]].inverted()@p[n]);loc,q,sc=m.decompose()
    if n in previous and q.dot(previous[n])<0:q.negate()
    previous[n]=q.copy();row[n]=(loc,q,sc)
   samples.append(row)
  a=source.copy();a.name='ASH12_'+family+'_'+kind;a.use_fake_user=True;r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
  for n in names:
   for prop in ('location','rotation_quaternion','scale'):
    if (f'pose.bones["{n}"].{prop}',0) not in curves:r.pose.bones[n].keyframe_insert(prop,frame=0)
  curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
  for n in names:
   for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(count):
     c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(samples))
     c.keyframe_points.foreach_set('co',[v for j,row in enumerate(samples) for v in (j*.5,row[n][field][axis])])
     for k in c.keyframe_points:k.interpolation='LINEAR'
     c.update()
  scene.frame_start=0;scene.frame_end=end;scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True);name='A_ASH12_'+family+'_'+kind;file=dest/(name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
  report['clips'][family+'/'+kind]={'family':family,'kind':kind,'name':name,'source_action':source_name,'file':str(file),'duration':end/60,'action':a.name}
  (O/'animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('ASH_GRIP_CLIP_AUTHORED',family,kind,flush=True)
 # Include the actual fitted grip in the editable scene, rigidly following root.
 before=set(scene.objects);bpy.ops.import_scene.fbx(filepath=M['parts'][family]['file'])
 ob=next(x for x in scene.objects if x not in before and x.type=='MESH');ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 ob.data.transform(rest['WPN_root']@Matrix(M['parts'][family]['mount_in_root']));ob.vertex_groups.new(name='WPN_root').add(list(range(len(ob.data.vertices))),1.,'REPLACE');mod=ob.modifiers.new('ASH rigid attachment','ARMATURE');mod.object=r
 pose(bpy.data.actions['ASH12_'+family+'_idle'],0);scene.frame_end=180
 bpy.ops.wm.save_as_mainfile(filepath=str(O/('ASH12_'+family+'_Grips_Editable.blend')))
print('ASH_GRIP_FAMILIES_AUTHORED',flush=True)
