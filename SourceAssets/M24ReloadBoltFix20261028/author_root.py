"""Camera clearance on the M24 support chain; no weapon, contact or right-hand edits."""
from pathlib import Path
exec(compile((Path(__file__).parent/'fit_root.py').read_text().split("folder=O/'candidates'")[0],'fit','exec'))
owned=[n for n in names if under(n,'clavicle_l') and (not under(n,'hand_l') or n=='hand_l')]
def corrected(role,t,family='base'):
 row=component(local_pose(role,t,family));shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}[role]
 f=t*30-shift;w=ease((f-2)/14)*(1-ease((f-42)/13))
 return adjust(row,30*w,(4*w,0,-10*w)) if w>1e-8 else row
if (O/'elbow_correctives.npz').exists():
 extra=np.load(O/'elbow_correctives.npz');basis=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data])
 for name in extra.files:
  if name in skin.data.shape_keys.key_blocks:raise RuntimeError('Corrective name already exists '+name)
  key=skin.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(basis+extra[name]/100).ravel());key.value=0
 skin.data.update()
patch={};report={'owned':owned,'max_preserved_component_delta':0.,'max_length_error_mm':0.,'samples':0,'worst_root_before':1.,'worst_root_after':1.,'peak_proximal_before':0,'peak_proximal_after':0}
folder=O/'after';folder.mkdir(exist_ok=True);s.render.resolution_x=960;s.render.resolution_y=540
for family,role in [('base','fire'),('mag10','fire'),('base','cycle'),('mag10','cycle'),('base','reload_empty'),('mag10','reload_empty_mag10')]:
 data=ue['clips'][role];duration=(data['keys']-1)/data['fps'];times=[i/120 for i in range(round(duration*120)+1)]
 tracks={n:{'bone':n,'times':times,'values':[]} for n in owned};last={};action=bpy.data.actions.new('M24_RootClearance_'+family+'_'+role)
 r.animation_data_create();r.animation_data.action=action
 for i,t in enumerate(times):
  original=component(local_pose(role,t,family));row=corrected(role,t,family)
  for n in names:
   if n in owned and n!='hand_l':continue
   report['max_preserved_component_delta']=max(report['max_preserved_component_delta'],max(abs(row[n][a][b]-original[n][a][b]) for a in range(4) for b in range(4)))
  for child,parent in [('lowerarm_l','upperarm_l'),('hand_l','lowerarm_l')]:
   report['max_length_error_mm']=max(report['max_length_error_mm'],abs((row[child].translation-row[parent].translation).length-(rest[child].translation-rest[parent].translation).length)*1000)
  f=t*data['fps'];lo=min(int(f),data['keys']-2);blend=f-lo
  for n in owned:
   j=names.index(n);p,q,sc=unpack(data['poses'][str(lo)][j]);pp,qq,ss=unpack(data['poses'][str(lo+1)][j]);p=p.lerp(pp,blend);q=q.slerp(qq,blend);sc=sc.lerp(ss,blend)
   local=K@(row[parents[n]].inverted()@row[n])@K;dp,dq,ds=local.decompose();dp-=p;dq=dq@q.inverted();ds-=sc;dq.normalize()
   if n in last and last[n].dot(dq)<0:dq=-dq
   last[n]=dq.copy();tracks[n]['values'].extend([*dp,dq.x,dq.y,dq.z,dq.w,*ds])
  # Keep a complete editable action with the current V9 mesh and correctives.
  r.animation_data.action=action
  for n in names:
   local=row[parents[n]].inverted()@row[n] if parents[n] else row[n];b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.matrix_basis=local_rest[n].inverted()@local
   for path in ('location','rotation_quaternion','scale'):b.keyframe_insert(data_path=path,frame=i,group=n)
  report['samples']+=1
 patch[family+'/'+role]={'family':family,'base':data['path'],'duration':duration,'tracks':list(tracks.values())}
 if family=='base' and role in ('fire','cycle'):
  for i in range(data['keys']):
   a=stats(component(local_pose(role,i/30,family)));b=stats(corrected(role,i/30,family))
   report['worst_root_before']=min(report['worst_root_before'],a['root_top'] or 1);report['worst_root_after']=min(report['worst_root_after'],b['root_top'] or 1)
   report['peak_proximal_before']=max(report['peak_proximal_before'],a['proximal_root_visible_vertices']);report['peak_proximal_after']=max(report['peak_proximal_after'],b['proximal_root_visible_vertices'])
  for i in (0,8,16,23,30,36,42,50,55):render(corrected(role,i/30,family),folder/f'{role}_{i:02}.png')
for role in ('reload_empty','reload_empty_mag10'):
 family='mag10' if role.endswith('mag10') else 'base'
 render(corrected(role,75/30,family),folder/f'{role}_75.png',extended=family=='mag10')
(O/'root_patch.json').write_text(json.dumps(patch));(O/'root_authoring.json').write_text(json.dumps(report,indent=2))
s.render.fps=120;s.frame_start=0;s.frame_end=220;r.matrix_world=Matrix.Identity(4)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_BoltRoot_Editable.blend'))
print('M24_ROOT_AUTHORED',json.dumps(report),flush=True)
