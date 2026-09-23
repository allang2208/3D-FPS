"""SVD contact families: accepted grouped fingers, complete arm, original mechanics."""
import bpy,ast,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)
src=json.loads((O/'sources.json').read_text());geo=json.loads((O/'authoring.json').read_text());G=Matrix(geo['grip_transform'])
ns=globals();tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select','bake','solve_arm','smooth','mix']],type_ignores=[]),'SVD_original_author_functions','exec'),ns)
sys.path.insert(0,str(S/'SVDCompletion20260923'))
from tactical_actions import sprint_generator
bpy.context.preferences.filepaths.save_version=0
donors={}
for family in ['vertical','canted','prism','angled']:
 path=Path(src['animations'][family+'/idle']['source'][0]).with_suffix('.blend')
 bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
 inv=r.pose.bones['WPN_root'].matrix.inverted()
 donors[family]={'source':str(path),'hand':G@inv@r.pose.bones['hand_l'].matrix,'fingers':{b.name:r.pose.bones['hand_l'].matrix.inverted()@b.matrix for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))}}
report={}
for family,donor in donors.items():
 bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_Modular_Editable.blend'));r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');scene=bpy.context.scene
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 names=[b.name for b in r.data.bones if b.name.endswith('_l') and b.name.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
 idle=sample(r,bpy.data.actions['A_SVD_idle'],0);idlehand=idle['WPN_root'].inverted()@idle['hand_l']
 def contact(row,weight):
  goal={n:m.copy() for n,m in row.items()};H=row['WPN_root']@donor['hand'];solve_arm(goal,H,'l')
  for n,m in donor['fingers'].items():goal[n]=H@m
  # Distribute the target hand's forearm twist along the original auxiliary chain.
  lf=goal['lowerarm_l'];df=lf.to_3x3()@rest['lowerarm_l'].to_3x3().inverted();dh=H.to_3x3()@rest['hand_l'].to_3x3().inverted()
  q=(dh@df.inverted()).to_quaternion();axis=(H.translation-lf.translation).normalized();v=Vector((q.x,q.y,q.z));v=axis*v.dot(axis);twist=Quaternion((q.w,v.x,v.y,v.z));twist.normalize()
  if twist.w<0:twist.negate()
  for suffix,fraction in [('02',.40),('01',.82)]:
   n='lowerarm_twist_'+suffix+'_l';m=lf@rest['lowerarm_l'].inverted()@rest[n];p=m.translation.copy();m=Quaternion().slerp(twist,fraction).to_matrix().to_4x4()@m;m.translation=p;goal[n]=m
  result={n:m.copy() for n,m in row.items()}
  for n in names:
   pn=parent[n];a=row[pn].inverted()@row[n];b=goal[pn].inverted()@goal[n]
   result[n]=result[pn]@mix(a,b,weight)
  return result
 gripidle=contact(idle,1)
 for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','inspect','quick_melee']:
  original=bpy.data.actions['A_SVD_'+clip];count=round(src['svd_clips'][clip]['seconds']*120);poses=[]
  for frame in range(count+1):
   row=sample(r,original,frame);weight=1.
   if clip.startswith('reload'):weight=1-smooth(frame/24)+smooth((frame-272)/30)
   elif clip=='inspect':
    local=row['WPN_root'].inverted()@row['hand_l'];delta=(local.translation-idlehand.translation).length
    weight=1-smooth((delta-.012)/.045)
   poses.append(contact(row,weight))
  bake(r,poses,family+'_'+clip,120)
  report[family+'/'+clip]={'name':'A_SVD_'+family+'_'+clip,'fps':120,'frames':count,'seconds':count/120,'donor':donor['source'],'mechanics':'original SVD gun/right-arm/magazine/bolt tracks retained'}
  print('SVD_ATTACH_ANIMATION',family,clip,flush=True)
 make_sprint,settings=sprint_generator(r,gripidle)
 for clip,count in [('sprint_enter',48),('sprint_loop',120),('sprint_exit',48)]:
  poses=[]
  for f in range(count+1):
   fraction=f/count;progress=1 if clip=='sprint_loop' else 1-fraction if clip=='sprint_exit' else fraction
   poses.append(make_sprint(progress,2*math.pi*fraction if clip=='sprint_loop' else None))
  bake(r,poses,family+'_'+clip,120)
  report[family+'/'+clip]={'name':'A_SVD_'+family+'_'+clip,'fps':120,'frames':count,'seconds':count/120,'donor':donor['source'],'method':'SVD tactical release/regrip generated from family contact idle'}
  print('SVD_ATTACH_ANIMATION',family,clip,flush=True)
 sample(r,bpy.data.actions['A_SVD_'+family+'_idle'],0);scene.frame_start=0;scene.frame_end=120
 bpy.ops.wm.save_as_mainfile(filepath=str(O/('SVD_'+family+'_Editable.blend')))
 (O/'animations.json').write_text(json.dumps(report,indent=2))
print('SVD_ATTACH_ANIMATIONS_COMPLETE',len(report),flush=True)
