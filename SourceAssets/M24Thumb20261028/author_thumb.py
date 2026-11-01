"""Correct signed native distal axes without changing any wrist/arm/gun tracks."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
OWNED=[f'{d}_03_r' for d in ('thumb','index','middle','ring','pinky')]
SHIFTS={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}
original={role:[{n:m.copy() for n,m in row.items()} for row in clips[role]] for role in SHIFTS}

def localq(row,n):return (row[parents[n]].inverted()@row[n]).to_quaternion()

def correct_axis(row,n):
 # Skin and all child offsets extend along -X, including the thumb. Keep
 # native roll and align that signed axis to the intended donor direction.
 base=row[parents[n]]@local_rest[n]
 intended=row[n].to_quaternion()@Vector((1,0,0))
 actual_axis=base.to_quaternion()@Vector((-1,0,0))
 world=actual_axis.rotation_difference(intended)@base.to_quaternion()
 return row[parents[n]].to_quaternion().inverted()@world

for role,shift in SHIFTS.items():
 rows=clips[role];src=original[role]
 opened={n:(localq(src[shift+7],n) if n.startswith('index_') else correct_axis(src[shift+7],n)) for n in OWNED}
 opened['thumb_03_r']=local_rest['thumb_03_r'].to_quaternion()@Quaternion((0,0,1),math.radians(-5))
 held={n:localq(src[0],n) for n in OWNED}
 core=[{n:correct_axis(row,n) for n in OWNED} for row in src]
 for f,qs in enumerate(core):
  # Native thumb IP flexes about local Z. Do not reproduce the donor's
  # lateral IP bend, and keep the little fingertip outside the bolt knob.
  t=f-shift;keys=[(16,0),(20,10),(25,14),(30,10),(35,14),(41,3)]
  j=max(0,min(len(keys)-2,bisect.bisect_right([k[0] for k in keys],t)-1))
  a,b=keys[j],keys[j+1];w=ease((t-a[0])/(b[0]-a[0]));deg=a[1]+(b[1]-a[1])*w
  qs['thumb_03_r']=local_rest['thumb_03_r'].to_quaternion()@Quaternion((0,0,1),math.radians(deg))
  qs['pinky_03_r']=local_rest['pinky_03_r'].to_quaternion()
  ring_keys=[(16,5),(20,5),(23,-10),(25,-10),(28,10),(32,10),(36,5),(41,0)]
  j=max(0,min(len(ring_keys)-2,bisect.bisect_right([k[0] for k in ring_keys],t)-1))
  a,b=ring_keys[j],ring_keys[j+1];w=ease((t-a[0])/(b[0]-a[0]));deg=a[1]+(b[1]-a[1])*w
  qs['ring_03_r']=local_rest['ring_03_r'].to_quaternion()@Quaternion((0,0,1),math.radians(deg))
 for f,row in enumerate(rows):
  t=f-shift
  for n in OWNED:
   if t<=2 or t>=55:continue
   if t<7:q=held[n].slerp(opened[n],ease((t-2)/5))
   elif t<=11:q=opened[n]
   elif t<16:q=opened[n].slerp(core[shift+16][n],ease((t-11)/5))
   elif t<=41:q=core[f][n]
   elif t<43:q=core[shift+41][n].slerp(opened[n],ease((t-41)/2))
   elif t<=52:q=opened[n]
   else:q=opened[n].slerp(localq(src[min(len(src)-1,shift+55)],n),ease((t-52)/3))
   loc=src[f][parents[n]].inverted()@src[f][n]
   row[n]=row[parents[n]]@Matrix.LocRotScale(loc.translation,q,loc.to_scale())

(OUT/'final_poses.json').write_text(json.dumps({role:serial(clips[role]) for role in SHIFTS}))
diagnostic={'scope':'five right distal rotations; native signed axis correction','roles':{},'runtime_tested':False}
for role,shift in SHIFTS.items():
 max_unowned=0.;max_offset=0.;max_thumb_angle=0.;max_frame_rotation=0.
 for f,(row,old) in enumerate(zip(clips[role],original[role])):
  max_unowned=max(max_unowned,max(max(abs(row[n][i][j]-old[n][i][j]) for i in range(4) for j in range(4)) for n in row if n not in OWNED))
  for n in OWNED:
   loc=row[parents[n]].inverted()@row[n];orig=old[parents[n]].inverted()@old[n]
   max_offset=max(max_offset,(loc.translation-orig.translation).length*1000)
   if n.startswith('thumb_'):
    q=local_rest[n].to_quaternion().inverted()@loc.to_quaternion();max_thumb_angle=max(max_thumb_angle,math.degrees(min(q.angle,2*math.pi-q.angle)))
   if f:
    q=localq(clips[role][f-1],n).rotation_difference(localq(row,n));max_frame_rotation=max(max_frame_rotation,math.degrees(min(q.angle,2*math.pi-q.angle)))
 diagnostic['roles'][role]={'unowned_matrix_delta':max_unowned,'local_translation_delta_mm':max_offset,'max_thumb_last_joint_swing_deg':max_thumb_angle,'max_distal_frame_rotation_deg':max_frame_rotation}
(OUT/'authoring_checks.json').write_text(json.dumps(diagnostic,indent=2))
tree=ast.parse((OUT.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'bake','exec'));report={'clips':{},'fps':30,'runtime_tested':False,'owned_bones':OWNED}
for role in SHIFTS:
 old=bpy.data.actions.get('A_M24_'+role);r.animation_data.action=None
 if old:bpy.data.actions.remove(old)
 bake(role,clips[role])
r.animation_data.action=bpy.data.actions['A_M24_fire'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(20)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M24_Thumb_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))

# The native grip profiles store local delta rotations. Calculate them from
# the exact UE raw base samples, avoiding a second FBX retarget/compression.
patch={}
for role in SHIFTS:
 data=ue['clips'][role];replacements=[]
 for n in OWNED:
  times=[];values=[];previous=None;idx=names.index(n)
  for f,row in enumerate(clips[role]):
   raw=data['poses'][str(f)][idx];baseq=unpack(raw)[1]
   desired=K@(row[parents[n]].inverted()@row[n])@K
   dq=desired.to_quaternion()@baseq.inverted();dq.normalize()
   if previous is not None and dq.dot(previous)<0:dq.negate()
   times.append(f/data['fps']);values.extend([dq.x,dq.y,dq.z,dq.w]);previous=dq.copy()
  replacements.append({'bone':n,'times':times,'quaternions':values})
 patch[role]={'base':data['path'],'rotations':replacements}
(OUT/'rotation_patch.json').write_text(json.dumps(patch))
print('M24_DISTAL_ROTATIONS_AUTHORED',json.dumps(diagnostic),flush=True)
