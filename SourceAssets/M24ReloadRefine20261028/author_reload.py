"""Native left finger curves, with a firm hold through the seating contact."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'reload_library','exec'))
grasp={n:Matrix(m) for n,m in json.loads((O/'grasp_pose.json').read_text()).items()}
digits=[f'{finger}_{j:02d}_l' for finger in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
closed={n:(grasp[parents[n]].inverted()@grasp[n]).to_quaternion() for n in digits}
def Q(x=0,y=0,z=0):return Quaternion((0,0,1),math.radians(z))@Quaternion((0,1,0),math.radians(y))@Quaternion((1,0,0),math.radians(x))
relaxed={}
for n in digits:
 finger,j,_=n.split('_');j=int(j)
 basis=(Q(-12,8,6) if j==1 else Q(z=6 if j==2 else 4)) if finger=='thumb' else Q(z={1:12,2:18,3:10}[j])
 relaxed[n]=local_rest[n].to_quaternion()@basis
patch={};final={};report={'fps':30,'window_source_frames':[4,54],'roles':{},'preserved':'gun, magazine, wrists, shoulders, elbows, all right-hand channels, bone offsets and scales','source_review_only':True}
for role in ('reload','reload_empty','reload_mag10','reload_empty_mag10'):
 rows=clips[role];data=ue['clips'][role];out=[];tracks={n:[] for n in digits}
 for f,original in enumerate(rows):
  row=clone(original)
  if 4<f<54:
   for n in digits:
    finger=n.split('_')[0];local=original[parents[n]].inverted()@original[n]
    begin=(rows[4][parents[n]].inverted()@rows[4][n]).to_quaternion()
    end=(rows[54][parents[n]].inverted()@rows[54][n]).to_quaternion()
    close_start={'index':12,'middle':12.5,'ring':13,'pinky':13.5,'thumb':13}[finger]
    close_end={'index':19,'middle':19.5,'ring':20,'pinky':20.5,'thumb':20}[finger]
    release_start={'index':40,'middle':40.3,'ring':40.6,'pinky':40.9,'thumb':40.4}[finger]
    if f<=12:q=begin.slerp(relaxed[n],ease((f-4)/8))
    elif f<close_end:q=relaxed[n].slerp(closed[n],ease((f-close_start)/(close_end-close_start)))
    elif f<=release_start:q=closed[n]
    elif f<46:q=closed[n].slerp(relaxed[n],ease((f-release_start)/(46-release_start)))
    else:q=relaxed[n].slerp(end,ease((f-46)/8))
    row[n]=row[parents[n]]@Matrix.LocRotScale(local.translation,q,local.to_scale())
  out.append(row)
  for n in digits:
   local=K@(row[parents[n]].inverted()@row[n])@K
   raw=unpack(data['poses'][str(f)][names.index(n)])[1]
   dq=local.to_quaternion()@raw.inverted()
   if tracks[n] and sum(a*b for a,b in zip(tracks[n][-1],[dq.x,dq.y,dq.z,dq.w]))<0:dq=-dq
   tracks[n].append([dq.x,dq.y,dq.z,dq.w])
 patch[role]={'base':data['path'],'window':[4/30,54/30], 'rotations':[{'bone':n,'times':[f/30 for f in range(len(rows))],'quaternions':[x for q in tracks[n] for x in q]} for n in digits]}
 final[role]=out;report['roles'][role]={'frames':len(rows),'grasp_complete':20.5/30,'release_starts_after_seat':40/30,'return_complete':54/30}
(O/'rotation_patch.json').write_text(json.dumps(patch))
(O/'final_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in final.items()}))
tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'reload_bake','exec'))
report['clips']={}
for role,rows in final.items():
 r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
 if old:bpy.data.actions.remove(old)
 bake(role,rows)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ReloadRefine_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
setup_render();folder=O/'After';folder.mkdir(exist_ok=True)
for role in ('reload','reload_mag10'):
 for f in (12,16,21,24,35,38,40,43,46,50):
  show(final[role][f],folder/f'{role}_{f:03d}.png','right',role.endswith('mag10'))
print('M24_RELOAD_FINGER_CURVES_AUTHORED',flush=True)
