"""Three-joint thumb opposition with one-axis MCP/IP flexion."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
OWNED=thumb_names
SHIFTS={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}
original={role:[{n:m.copy() for n,m in row.items()} for row in clips[role]] for role in SHIFTS}
def localq(row,n):return (row[parents[n]].inverted()@row[n]).to_quaternion()
def pose_params(t):
 # Close the thumb with the actual stroke. The large legacy MCP lateral
 # swing is moved to the basal joint instead of twisting the phalanges.
 closed=ease((t-29)/4)*(1-ease((t-37)/4))
 return (-8.,-4.-26*closed,18.*closed,8.,8.)
opened=[Q(x=-6,y=4,z=-8),Q(z=0),Q(z=2)]
for role,shift in SHIFTS.items():
 rows=clips[role];src=original[role]
 for f,row in enumerate(rows):
  t=f-shift
  if t<=2 or t>=55:continue
  x,y,z,mcp,ip=pose_params(t);grasp=[Q(x,y,z),Q(z=mcp),Q(z=ip)]
  initial=[local_rest[n].to_quaternion().inverted()@localq(src[0],n) for n in OWNED]
  final=[local_rest[n].to_quaternion().inverted()@localq(src[min(shift+55,len(src)-1)],n) for n in OWNED]
  if t<7:qs=[a.slerp(b,ease((t-2)/5)) for a,b in zip(initial,opened)]
  elif t<=11:qs=opened
  elif t<19:qs=[a.slerp(b,ease((t-11)/8)) for a,b in zip(opened,grasp)]
  elif t<=41:qs=grasp
  elif t<47:qs=[a.slerp(b,ease((t-41)/6)) for a,b in zip(grasp,opened)]
  elif t<=50:qs=opened
  else:qs=[a.slerp(b,ease((t-50)/5)) for a,b in zip(opened,final)]
  rows[f]=thumb(row,qs)
(OUT/'final_poses.json').write_text(json.dumps({role:serial(clips[role]) for role in SHIFTS}))
report={'clips':{},'fps':30,'owned_bones':OWNED,'runtime_tested':False}
tree=ast.parse((OUT.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'bake','exec'))
for role in SHIFTS:
 old=bpy.data.actions.get('A_M24_'+role);r.animation_data.action=None
 if old:bpy.data.actions.remove(old)
 bake(role,clips[role])
r.animation_data.action=bpy.data.actions['A_M24_fire'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(20)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M24_ThumbAnatomy_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
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
(OUT/'rotation_patch.json').write_text(json.dumps(patch));print('M24_THUMB_ANATOMY_AUTHORED',flush=True)
