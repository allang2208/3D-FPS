"""Bake the fitted rigid weapon/palm group and full arm chains; animations only."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'M4QuickMeleeRefine20260919K'))
from arm_support import axial_angle
sources=json.loads((O/'sources.json').read_text());motion=json.loads((O/'motion.json').read_text())
records=json.loads((O/'authoring.json').read_text()) if (O/'authoring.json').exists() else {}
bpy.context.preferences.filepaths.save_version=0
def frame(axis,normal):
 axis=axis.normalized();normal=normal-axis*normal.dot(axis);normal.normalize()
 return Matrix((axis,normal.cross(axis).normalized(),normal)).transposed().to_quaternion()
for key,d in sources.items():
 if '--' in sys.argv and sys.argv[sys.argv.index('--')+1:] and key not in sys.argv[sys.argv.index('--')+1:]:continue
 weapon,family=key.split('/')
 bpy.ops.wm.open_mainfile(filepath=d['source'],use_scripts=False);r=bpy.data.objects[d['rig']];scene=bpy.context.scene
 idle={n:Matrix(m) for n,m in d['idle'].items()};rest={n:Matrix(m) for n,m in d['rest'].items()};parents=d['parents']
 lr={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
 W0=idle['WPN_root'];rigid={'WPN_root'}|{b.name for b in r.data.bones['WPN_root'].children_recursive}|{n for n in rest if n.startswith(('WPN_','PKM_','New_PKM_'))}
 handbones={s:{'hand_'+s}|{b.name for b in r.data.bones['hand_'+s].children_recursive} for s in 'rl'}
 poses=[];previous={s:0. for s in 'rl'}
 for i,row in enumerate(motion[key]):
  W=Matrix(row['root']);delta=W@W0.inverted();p={n:m.copy() for n,m in idle.items()};weight=row['support_weight']
  for n in rigid:p[n]=delta@idle[n]
  for side in 'rl':
   cn,un,fn,hn=[n+'_'+side for n in ['clavicle','upperarm','lowerarm','hand']]
   sh0,el0,wr0=[idle[n].translation for n in [un,fn,hn]];H=delta@idle[hn]
   sh=Vector(row['arms'][side]['shoulder']);el=Vector(row['arms'][side]['elbow']);wr=H.translation
   U,L=el0-sh0,wr0-el0;u,f=(el-sh).normalized(),(wr-el).normalized();normal=u.cross(f).normalized()
   uq=frame(u,normal)@frame(U,U.cross(L)).inverted()@idle[un].to_quaternion()
   fq=frame(f,normal)@frame(L,U.cross(L)).inverted()@idle[fn].to_quaternion()
   handrot=H.to_quaternion()@rest[hn].to_quaternion().inverted()
   desired=handrot@(rest[hn].translation-rest[fn].translation).normalized()
   natural_fq=(desired.rotation_difference(f)@handrot)@rest[fn].to_quaternion()
   roll=axial_angle(natural_fq@fq.inverted(),f,previous[side]);previous[side]=roll
   p[cn]=idle[cn].copy();p[cn].translation+=sh-sh0
   for main,origin,q,axis,residual in [(un,sh,uq,u,0.),(fn,el,fq,f,roll)]:
    p[main]=Matrix.LocRotScale(origin,q,idle[main].to_scale())
    transport=q@idle[main].to_quaternion().inverted();neutral=q@rest[main].to_quaternion().inverted()
    for suffix in ['01','02']:
     name=main[:-2]+'_twist_'+suffix+'_'+side
     if name not in rest:continue
     oldpos=origin+transport@(idle[name].translation-idle[main].translation);oldrot=transport@idle[name].to_quaternion()
     twist=Quaternion(axis,residual*d['stations'][name])
     newpos=origin+twist@neutral@(rest[name].translation-rest[main].translation)
     newrot=twist@neutral@rest[name].to_quaternion()
     p[name]=Matrix.LocRotScale(oldpos.lerp(newpos,weight),oldrot.slerp(newrot,weight),idle[name].to_scale())
   for n in handbones[side]:p[n]=delta@idle[n]
   if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()
  if i in [0,len(motion[key])-1]:p={n:m.copy() for n,m in idle.items()}
  poses.append(p)
 a=bpy.data.actions.new(f'{weapon}_{family}_QuickMelee20260924');a.use_fake_user=True;r.animation_data.action=a
 for b in r.pose.bones:
  b.rotation_mode='QUATERNION'
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
 curves={(c.data_path,c.array_index):c for layer in a.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
 for n in rest:
  values=[];prev=None
  for p in poses:
   loc,q,scale=(lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])).decompose()
   if prev is not None and prev.dot(q)<0:q.negate()
   prev=q.copy();values.append((loc,q,scale))
  for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(values))
    c.keyframe_points.foreach_set('co',[v for i,row in enumerate(values) for v in (i,row[field][axis])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];r.data.pose_position='POSE'
 scene.render.fps=240;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=216;scene.frame_set(0)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 name='A_'+weapon+'_'+('' if family=='base' else family+'_')+'quick_melee';dest=O/'Animations'/weapon;dest.mkdir(parents=True,exist_ok=True);fbx=dest/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 blend=O/f'{weapon}_{family}_QuickMelee.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
 runtime=json.loads((O/'runtime_before.json').read_text())['clips'][key+'/quick_melee']['asset'].split('.')[0]
 records[key]={'name':name,'source':str(fbx),'blend':str(blend),'action':a.name,'fps':240,'duration':.9,'contact':1/6,'path':runtime,'game_tested':False}
 (O/'authoring.json').write_text(json.dumps(records,indent=2));print('MELEE_AUTHORED',key,flush=True)
