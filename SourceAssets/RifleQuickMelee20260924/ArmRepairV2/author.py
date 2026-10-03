"""Keep the accepted weapon tracks; repair full arm skin deformation and SVD grip."""
import bpy,json,math,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;P=O.parent;S=P.parent;D=O/'Animations';D.mkdir(exist_ok=True)
sources=json.loads((P/'sources.json').read_text());clips=json.loads((P/'authoring.json').read_text());grip=json.loads((O/'rear_grip.json').read_text())
records={};bpy.context.preferences.filepaths.save_version=0
def ease(x):
 x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def mix(a,b,w):
 p,q,s=a.decompose();p2,q2,s2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),s.lerp(s2,w))
def frame(axis,normal):
 axis=axis.normalized();normal-=axis*normal.dot(axis)
 if normal.length<1e-6:normal=axis.orthogonal()
 normal.normalize();return Matrix((axis,normal.cross(axis).normalized(),normal)).transposed().to_quaternion()
def solve_elbow(A,E0,T,a,b):
 direction=T-A;distance=direction.length;axis=direction.normalized()
 if distance>a+b-.0005:A+=axis*(distance-a-b+.0005);distance=(T-A).length
 along=(a*a-b*b+distance*distance)/(2*max(distance,1e-7));pole=E0-A;pole-=axis*pole.dot(axis)
 if pole.length<1e-7:pole=axis.orthogonal()
 return A,A+axis*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
# Reuse only the established FBX bone bake, not its old arm solver.
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['select','bake']],type_ignores=[]),'<bone bake>','exec'))
for key,info in clips.items():
 weapon,family=key.split('/');data=sources[key]
 bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False);r=bpy.data.objects[data['rig']];scene=bpy.context.scene
 src=bpy.data.actions[info['action']];r.animation_data.action=src;r.animation_data.action_slot=src.slots[0];r.data.pose_position='POSE'
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 lr={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
 idle={n:Matrix(m) for n,m in data['idle'].items()};poses=[]
 hands={s:{'hand_'+s}|{b.name for b in r.data.bones['hand_'+s].children_recursive} for s in 'rl'}
 for f in range(217):
  scene.frame_set(f);bpy.context.view_layer.update();old={b.name:b.matrix.copy() for b in r.pose.bones};p={n:m.copy() for n,m in old.items()}
  t=f/240.;weight=ease(t/.055)*(1-ease((t-.74)/.16))
  for side in 'rl':
   cn,un,fn,hn=[x+'_'+side for x in ['clavicle','upperarm','lowerarm','hand']]
   H=old[hn].copy();A=old[un].translation.copy();E=old[fn].translation.copy()
   if weapon=='SVD' and side=='r':
    H=mix(H,old['WPN_root']@Matrix(grip['hand_in_root']),weight)
    delta=H@old[hn].inverted()
    for n in hands[side]:p[n]=delta@old[n]
    # Cache complete local poses before rebuilding the finger parents.
    for n in rest:
     if n not in grip['finger_basis']:continue
     before=old[parents[n]].inverted()@old[n];target=lr[n]@Quaternion(grip['finger_basis'][n]).to_matrix().to_4x4()
     p[n]=p[parents[n]]@mix(before,target,weight)
    a=(idle[fn].translation-idle[un].translation).length;b=(idle[hn].translation-idle[fn].translation).length
    A,E=solve_elbow(A,E,H.translation,a,b)
   T=H.translation;ua=(E-A).normalized();fa=(T-E).normalized()
   ru=(rest[fn].translation-rest[un].translation).normalized();rf=(rest[hn].translation-rest[fn].translation).normalized()
   # Palm width defines axial roll. Project it onto the forearm plane so
   # wrist flexion never becomes a second forearm twist.
   width=rest['index_metacarpal_'+side].translation-rest['pinky_metacarpal_'+side].translation
   hand_deform=H.to_quaternion()@rest[hn].to_quaternion().inverted()
   fd=frame(fa,hand_deform@width)@frame(rf,width.copy()).inverted()
   fq=fd@rest[fn].to_quaternion()
   # Carry that same anatomical width through the elbow into the upper arm.
   uq=(frame(ua,fd@width)@frame(ru,width.copy()).inverted())@rest[un].to_quaternion()
   # At entry/exit use the transported current idle's main-bone rotation,
   # never the rejected clip's independently twisted helper rotations.
   for main,origin,q,oldaxis,newaxis in [(un,A,uq,idle[fn].translation-idle[un].translation,E-A),(fn,E,fq,idle[hn].translation-idle[fn].translation,T-E)]:
    baseline=oldaxis.normalized().rotation_difference(newaxis.normalized())@idle[main].to_quaternion()
    rotation=baseline.slerp(q,weight);p[main]=Matrix.LocRotScale(origin,rotation,idle[main].to_scale())
    for suffix in ['01','02']:
     name=main[:-2]+'_twist_'+suffix+'_'+side
     if name not in rest:continue
     baseline_local=idle[main].inverted()@idle[name]
     rigid_local=rest[main].inverted()@rest[name]
     p[name]=p[main]@mix(baseline_local,rigid_local,weight)
   p[cn]=old[cn].copy();p[cn].translation+=A-old[un].translation
   p[hn]=H
   if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()
  if f in [0,216]:p={n:m.copy() for n,m in idle.items()}
  poses.append(p)
 # The baking helper prefixes A_SVD_; export into task-local names, then use
 # each weapon's unchanged destination name from its current runtime clip.
 temp_key=weapon+'_'+family+'_QuickMeleeSkinV2'
 action=bake(r,poses,temp_key,240);temp=D/('A_SVD_'+temp_key+'.fbx');fbx=D/(info['name']+'.fbx');temp.replace(fbx)
 action.name=weapon+'_'+family+'_QuickMeleeSkinV2'
 # Save at the contact frame so the editable source opens on the repaired area.
 scene.frame_set(40);bpy.context.view_layer.update()
 blend=O/f'{weapon}_{family}_QuickMeleeSkinV2.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
 records[key]={**info,'source':str(fbx),'blend':str(blend),'action':action.name,'previous_source':info['source'],
  'changed':'complete segment-local helper transforms and palm-defined roll; SVD rear grip recalibrated; accepted weapon tracks retained','game_tested':False}
 (O/'authoring.json').write_text(json.dumps(records,indent=2));print('ARM_SKIN_AUTHORED',key,flush=True)
