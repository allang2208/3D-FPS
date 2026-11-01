from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
grip={n:Matrix(m) for n,m in json.loads((OUT/'grip_pose.json').read_text()).items()};idle=clips['idle'][0]
G=idle['WPN_root'];correction=G.inverted()@grip['hand_r']@idle['hand_r'].inverted()@G
local_delta={n:(idle[parents[n]].inverted()@idle[n]).to_quaternion().inverted()@(grip[parents[n]].inverted()@grip[n]).to_quaternion() for n in digits}
owned=[n for n in rest if under(n,'clavicle_r')];before={role:[clone(row) for row in rows] for role,rows in clips.items()}
diagnostic={'fixed_rifle_root_max_mm':0.,'fixed_left_arm_max_mm':0.,'right_clavicle_root_to_hold_max_mm':0.,'repaired_shoulder_track_max_delta_mm':0.,'max_reach_ratio':0.,'modified_roles':[]}
for role,rows in clips.items():
 shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}.get(role)
 for f,row in enumerate(rows):
  weight=1.
  if shift is not None:
   t=f-shift;weight=1-ease((t-7)/9)*(1-ease((t-41)/11))
  if weight<1e-7:continue
  prev=clone(row);held=row['WPN_root']@G.inverted()@grip['hand_r']
  row['hand_r']=row['hand_r'].lerp(held,weight)
  for n in digits:
   loc=prev[parents[n]].inverted()@prev[n]
   rot=loc.to_quaternion().slerp((grip[parents[n]].inverted()@grip[n]).to_quaternion(),weight)
   row[n]=row[parents[n]]@Matrix.LocRotScale(local_rest[n].translation,rot,Vector((1,1,1)))
  a=(rest['lowerarm_r'].translation-rest['upperarm_r'].translation).length;b=(rest['hand_r'].translation-rest['lowerarm_r'].translation).length
  ratio=(row['hand_r'].translation-row['upperarm_r'].translation).length/(a+b)
  if ratio>=.995:raise RuntimeError(f'{role}:{f} fixed-shoulder reach exceeds limit: {ratio}')
  diagnostic['max_reach_ratio']=max(diagnostic['max_reach_ratio'],ratio)
  fixed_arm(row,'r',0.)
  for n,m in prev.items():
   if n not in owned:row[n]=m
 diagnostic['modified_roles'].append(role)
 # Suppress independent per-frame fitting jumps in the last bolt revision.
 # Filter hand corrections in bolt space, so the mechanical travel itself is retained.
 if shift is not None:
  refs=[row['WPN_BoltHandle'].inverted()@row['hand_r'] for row in rows]
  elbow=[row['WPN_root'].inverted()@row['lowerarm_r'].translation for row in rows]
  finger_local=[{n:(row[parents[n]].inverted()@row[n]).to_quaternion() for n in digits} for row in rows]
  weights=(1.,4.,6.,4.,1.)
  def averaged(mats,f):
   p=Vector();v=Vector((0,0,0,0));q0=mats[f].to_quaternion()
   for off,w in zip(range(-2,3),weights):
    m=mats[max(0,min(len(mats)-1,f+off))];q=m.to_quaternion()
    if q.dot(q0)<0:q=-q
    p+=m.translation*(w/16);v+=Vector((q.w,q.x,q.y,q.z))*(w/16)
   return Matrix.LocRotScale(p,Quaternion(v).normalized(),Vector((1,1,1)))
  smooth=refs
  for repeat in range(2):smooth=[averaged(smooth,f) for f in range(len(rows))]
  held_local=G.inverted()@grip['hand_r']
  knob_vertices=[v.co for v in bpy.data.objects['M24_bolt'].data.vertices if v.co.x>.046]
  knob_center=sum(knob_vertices,Vector())/len(knob_vertices);core=[]
  for f,row in enumerate(rows):
   pivot=row['WPN_BoltHandle']@rest['WPN_BoltHandle'].inverted()@knob_center
   up=(row['WPN_root']@rest['WPN_root'].inverted()).to_3x3()@Vector((0,0,1))
   D=Matrix.Translation(pivot)@Quaternion(up,math.radians(-25)).to_matrix().to_4x4()@Matrix.Translation(-pivot)
   core.append(D@row['WPN_BoltHandle']@smooth[f])
  entry=rows[shift+16]['WPN_root'].inverted()@core[shift+16]
  exit_pose=rows[shift+41]['WPN_root'].inverted()@core[shift+41]
  open_pose={'hand_r':rest['hand_r'].copy()}
  for n in digits:
   m=open_pose[parents[n]]@local_rest[n]
   if 'metacarpal' not in n:
    finger,j,_=n.split('_');j=int(j)
    d=rest[f'{finger}_{j+1:02d}_r'].translation-rest[n].translation if j<3 else rest[n].to_3x3()@Vector((1,0,0))
    desired=(target_frame.col[0]*.35+target_frame.col[1]*.9).normalized() if finger=='thumb' else target_frame.col[0]
    current=m.to_quaternion()@rest[n].to_quaternion().inverted()@d
    m=Matrix.LocRotScale(m.translation,current.rotation_difference(desired)@m.to_quaternion(),Vector((1,1,1)))
   open_pose[n]=m
  open_local={n:(open_pose[parents[n]].inverted()@open_pose[n]).to_quaternion() for n in digits}
  grip_local={n:(grip[parents[n]].inverted()@grip[n]).to_quaternion() for n in digits}
  for n in digits:
   if n.startswith('index_'):open_local[n]=grip_local[n].copy()
  axis=(grip['hand_r'].translation-grip['upperarm_r'].translation).normalized();p=grip['lowerarm_r'].translation-grip['upperarm_r'].translation
  fixed_pole=G.to_quaternion().inverted()@(p-axis*p.dot(axis)).normalized()
  for f,row in enumerate(rows):
   t=f-shift;arc=0.
   if t<=7:h=row['WPN_root']@held_local
   elif t<16:
    w=ease((t-7)/9);h=row['WPN_root']@held_local.lerp(entry,w);arc=.030*math.sin(math.pi*w)
   elif t<=41:h=core[f]
   elif t<=43:h=row['WPN_root']@exit_pose
   elif t<52:
    w=ease((t-43)/9);h=row['WPN_root']@exit_pose.lerp(held_local,w);arc=.030*math.sin(math.pi*w)
   else:h=row['WPN_root']@held_local
   h.translation+=(row['WPN_root']@rest['WPN_root'].inverted()).to_3x3()@Vector((arc,0,0));row['hand_r']=h
   for n in digits:
    if t<=7:q=grip_local[n].slerp(open_local[n],ease((t-2)/5))
    elif t<16:q=open_local[n].slerp(finger_local[shift+16][n],ease((t-11)/5))
    elif t<=41:
     q0=finger_local[f][n];vec=Vector((0,0,0,0))
     for off,k in zip(range(-2,3),weights):
      qn=finger_local[max(0,min(len(rows)-1,f+off))][n]
      if qn.dot(q0)<0:qn=-qn
      vec+=Vector((qn.w,qn.x,qn.y,qn.z))*(k/16)
     q=Quaternion(vec).normalized()
    elif t<=43:q=finger_local[shift+41][n].slerp(open_local[n],ease((t-41)/2))
    elif t<52:q=open_local[n]
    else:q=open_local[n].slerp(grip_local[n],ease((t-52)/3))
    row[n]=row[parents[n]]@Matrix.LocRotScale(local_rest[n].translation,q,Vector((1,1,1)))
   # Protract by rotating the native clavicle about its held root. This replaces
   # the old per-frame shoulder translations while preserving native bone lengths.
   clav=row['WPN_root']@G.inverted()@grip['clavicle_r'];start=row['WPN_root']@G.inverted()@grip['upperarm_r'].translation
   cv=clav.translation;v0=start-cv;radius=v0.length;u=(h.translation-cv).normalized();distance=(h.translation-cv).length
   arm_length=(rest['lowerarm_r'].translation-rest['upperarm_r'].translation).length+(rest['hand_r'].translation-rest['lowerarm_r'].translation).length
   reach=.955*arm_length;cosine=(distance*distance+radius*radius-reach*reach)/(2*distance*radius)
   if cosine>1.0001:raise RuntimeError(f'{role}:{f} unreachable with native clavicle: {cosine}')
   if (h.translation-start).length>reach:
    co=max(-1,min(1,cosine));side=(v0-u*v0.dot(u)).normalized();v=u*(radius*co)+side*(radius*math.sqrt(max(0,1-co*co)))
    turn=v0.rotation_difference(v);clav=Matrix.LocRotScale(cv,turn@clav.to_quaternion(),Vector((1,1,1)));start=cv+v
   row['clavicle_r']=clav;row['upperarm_r'].translation=start
   # A perpendicular pole stays well-conditioned as the wrist crosses the bolt.
   pole=row['WPN_root'].to_quaternion()@fixed_pole
   row['lowerarm_r'].translation=row['upperarm_r'].translation+pole*.2
   fixed_arm(row,'r',0.)
   for n,m in before[role][f].items():
    if n not in owned:row[n]=m.copy()
 for old,row in zip(before[role],rows):
  for key,ns in [('fixed_rifle_root_max_mm',[n for n in rest if n.startswith('WPN_')]),('fixed_left_arm_max_mm',[n for n in rest if under(n,'clavicle_l')]),('repaired_shoulder_track_max_delta_mm',['upperarm_r','clavicle_r'])]:
   diagnostic[key]=max(diagnostic[key],max((old[n].translation-row[n].translation).length*1000 for n in ns))
  if shift is not None:
   expected=row['WPN_root']@G.inverted()@grip['clavicle_r'].translation
   diagnostic['right_clavicle_root_to_hold_max_mm']=max(diagnostic['right_clavicle_root_to_hold_max_mm'],(row['clavicle_r'].translation-expected).length*1000)
(OUT/'final_poses.json').write_text(json.dumps({role:serial(rows) for role,rows in clips.items()}))
(OUT/'anchor_record.json').write_text(json.dumps(diagnostic,indent=2));print('FIXED_ANCHORS',diagnostic,flush=True)
tree=ast.parse((OUT.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'bake','exec'));report={'clips':{},'fps':30,'runtime_tested':False};X=OUT/'Exports';X.mkdir(exist_ok=True)
for role,rows in clips.items():
 old=bpy.data.actions.get('A_M24_'+role);r.animation_data.action=None
 if old:bpy.data.actions.remove(old)
 bake(role,rows);bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 path=X/('A_M24_'+role+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 report['clips'][role].update(file=str(path),owned_bones=owned)
r.animation_data.action=bpy.data.actions['A_M24_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M24_GripFinish_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print('M24_GRIP_FINISH_EXPORTED',len(clips),flush=True)
