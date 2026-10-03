"""Replace only the SVD empty-reload right-arm charge interval with an AKM hook."""
import bpy,json,math,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)
previous=json.loads((S/'SVDThumbUp20260923/authoring.json').read_text())
live=json.loads((O/'runtime_inputs.json').read_text())['clips']
fit=json.loads((O/'contact_fit.json').read_text());hook=Matrix(fit['contact_hand_root'])
inputs=json.loads((O/'pose_inputs.json').read_text());donor={n:Matrix(m) for n,m in inputs['AKM']['poses'][330].items()}
donor_elbow=(donor['WPN_root'].inverted()@donor['lowerarm_r']).translation+Vector(fit['handle_translation'])
groups={label:{n:Quaternion(q) for n,q in fit[label].items()} for label in ['finger_basis','approach_basis','release_basis']}
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select']],type_ignores=[]),'<source helpers>','exec'))
bpy.context.preferences.filepaths.save_version=0;report={}
def ease(x):
 x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def mix(a,b,w):
 p,q,s=a.decompose();p2,q2,s2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),s.lerp(s2,w))
def shifted(m,v):
 m=m.copy();m.translation+=Vector(v);return m
def frame(axis,normal):
 axis=axis.normalized();normal=normal-axis*normal.dot(axis)
 if normal.length<1e-6:normal=axis.orthogonal()
 normal.normalize();return Matrix((axis,normal.cross(axis).normalized(),normal)).transposed().to_quaternion()
def solve_elbow(A,E0,T,a,b):
 direction=T-A;distance=direction.length;axis=direction.normalized()
 if distance>a+b-.001:A+=axis*(distance-a-b+.001);distance=(T-A).length
 along=(a*a-b*b+distance*distance)/(2*max(distance,1e-7));pole=E0-A;pole-=axis*pole.dot(axis)
 if pole.length<1e-7:pole=axis.orthogonal()
 return A,A+axis*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
def curves(action):
 return {(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}

for family in ['base','vertical','canted','prism','angled']:
 key=family+'/reload_empty';info=previous[key]
 if Path(info['source']).resolve()!=Path(live[key]['source']).resolve():raise RuntimeError('Source revision changed '+key)
 bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
 source=bpy.data.actions[info['name']];poses=[sample(r,source,f) for f in range(516)]
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 lr={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
 fingers=list(groups['finger_basis']);un,fn,hn,cn='upperarm_r','lowerarm_r','hand_r','clavicle_r'
 modified=[cn,un,fn,hn,'upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_twist_01_r','lowerarm_twist_02_r']+fingers
 if 'ik_hand_r' in rest:modified.append('ik_hand_r')
 entry=poses[268]['WPN_root'].inverted()@poses[268][hn];finish=poses[432]['WPN_root'].inverted()@poses[432][hn]
 closed=poses[0]['WPN_root'].inverted()@poses[0]['WPN_bolt']
 backtravel=(poses[344]['WPN_root'].inverted()@poses[344]['WPN_bolt']).translation-closed.translation
 pre=shifted(hook,(-.035,.028,.012));back=shifted(hook,backtravel);away=shifted(back,(-.04,.018,.012))
 ru=(rest[fn].translation-rest[un].translation).normalized();rf=(rest[hn].translation-rest[fn].translation).normalized()
 width=rest['index_metacarpal_r'].translation-rest['pinky_metacarpal_r'].translation
 bounds={f:{n:(lr[n].inverted()@poses[f][parents[n]].inverted()@poses[f][n]).to_quaternion() for n in fingers} for f in [268,432]}
 action=source.copy();source.name='REFERENCE_BEFORE_CHARGE_GRIP_'+source.name;action.name=info['name'];action.use_fake_user=True
 original=curves(source);tracks=curves(action);rows={n:[] for n in modified}
 for f in range(269,432):
  old=poses[f];p={n:m.copy() for n,m in old.items()};W=old['WPN_root']
  if f<294:local=mix(entry,pre,ease((f-268)/26))
  elif f<310:local=mix(pre,hook,ease((f-294)/16))
  elif f<=344:
   travel=(W.inverted()@old['WPN_bolt']).translation-closed.translation;local=shifted(hook,travel)
  elif f<364:local=mix(back,away,ease((f-344)/20))
  else:local=mix(away,finish,ease((f-364)/68))
  H=W@local
  # Preserve the entire finger group and all rest-local positions/scales.
  p[hn]=H
  for n in fingers:
   if f<294:q=bounds[268][n].slerp(groups['approach_basis'][n],ease((f-268)/26))
   elif f<310:q=groups['approach_basis'][n].slerp(groups['finger_basis'][n],ease((f-294)/16))
   elif f<=344:q=groups['finger_basis'][n].copy()
   elif f<358:q=groups['finger_basis'][n].slerp(groups['release_basis'][n],ease((f-344)/14))
   else:q=groups['release_basis'][n].slerp(bounds[432][n],ease((f-358)/74))
   basis=lr[n].inverted()@old[parents[n]].inverted()@old[n];loc,unused,scale=basis.decompose()
   p[n]=p[parents[n]]@lr[n]@Matrix.LocRotScale(loc,q,scale)
  support=ease((f-268)/28)*(1-ease((f-364)/68))
  A=old[un].translation.copy();E=old[fn].translation.lerp(W@donor_elbow,support)
  a=(old[fn].translation-old[un].translation).length;b=(old[hn].translation-old[fn].translation).length
  A,E=solve_elbow(A,E,H.translation,a,b);T=H.translation
  fd=frame(T-E,(H.to_quaternion()@rest[hn].to_quaternion().inverted())@width)@frame(rf,width).inverted()
  fq=fd@rest[fn].to_quaternion();uq=(frame(E-A,fd@width)@frame(ru,width).inverted())@rest[un].to_quaternion()
  for main,origin,q,oldaxis,newaxis in [(un,A,uq,old[fn].translation-old[un].translation,E-A),(fn,E,fq,old[hn].translation-old[fn].translation,T-E)]:
   transported=oldaxis.normalized().rotation_difference(newaxis.normalized())@old[main].to_quaternion()
   p[main]=Matrix.LocRotScale(origin,transported.slerp(q,support),old[main].to_scale())
   for suffix in ['01','02']:
    n=main[:-2]+'_twist_'+suffix+'_r';oldlocal=old[main].inverted()@old[n];rigid=rest[main].inverted()@rest[n]
    p[n]=p[main]@mix(oldlocal,rigid,support)
  p[cn].translation+=A-old[un].translation
  if 'ik_hand_r' in rest:p['ik_hand_r']=H.copy()
  for n in modified:
   basis=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);rows[n].append((f,basis.decompose()))
 # Copy the original action and replace only the authorised right-arm channels
 # in frames 269..431. All weapon, magazine and left-hand curves stay verbatim.
 for n in modified:
  for prop,index,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   path=f'pose.bones["{n}"].{prop}'
   values=[];last=None
   for f in range(516):
    if 269<=f<432:v=rows[n][f-269][1][index].copy()
    elif prop=='rotation_quaternion':v=Quaternion([original[(path,j)].evaluate(f) for j in range(4)])
    else:v=Vector([original[(path,j)].evaluate(f) for j in range(3)])
    if prop=='rotation_quaternion':
     if last is not None and last.dot(v)<0:v.negate()
     last=v.copy()
    values.append(v)
   for j in range(count):
    c=tracks[(path,j)];c.keyframe_points.clear();c.keyframe_points.add(516)
    c.keyframe_points.foreach_set('co',[v for f,row in enumerate(values) for v in (f,row[j])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
 scene.render.fps=120;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=515;scene.frame_set(330);bpy.context.view_layer.update()
 blend=O/f'SVD_{family}_ChargeGrip.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
 select([r]);fbx=D/(info['name']+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[key]={'path':info['path'],'name':info['name'],'blend':str(blend),'action':action.name,'source':str(fbx),'previous_source':live[key]['source'],'previous_blend':info['blend'],
  'fps':120,'frames':515,'duration':515/120,'modified_bones':modified,'modified_frames':[269,431],'donor':fit['donor'],
  'charge_phases':{'leave_grip':268,'approach':294,'contact':310,'rear_stop_and_release':344,'bolt_closed':350,'withdraw':364,'return':432},'game_tested':False}
 (O/'authoring.json').write_text(json.dumps(report,indent=2));print('SVD_CHARGE_AUTHORED',key,flush=True)
print('SVD_CHARGE_AUTHORING_COMPLETE',len(report),flush=True)
