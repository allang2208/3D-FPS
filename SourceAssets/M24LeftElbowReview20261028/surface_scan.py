from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('setup_render();s.render.resolution_x=960')[0],'runtime','exec'))
setup_render()
# Match every corrective family and the threshold in FPSArmJointCorrectiveComponent.
def morphs_full():
 row={b.name:b.matrix for b in r.pose.bones};keys=skin.data.shape_keys.key_blocks
 for k in keys:k.value=0
 for side in ('l','r'):
  u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')];tw='lowerarm_twist_01_'+side
  elbow=angle(row[l].translation-row[u].translation,row[h].translation-row[l].translation)
  re=angle(rest[l].translation-rest[u].translation,rest[h].translation-rest[l].translation)
  f0=(rest['middle_01_'+side].translation-rest[h].translation).normalized()
  r0=rest['index_metacarpal_'+side].translation-rest['pinky_metacarpal_'+side].translation;r0=(r0-f0*r0.dot(f0)).normalized();z0=f0.cross(r0)
  q=rest[tw].to_quaternion().inverted();f0=q@f0;r0=q@r0;z0=q@z0
  direction=row[tw].to_quaternion().inverted()@(row['middle_01_'+side].translation-row[h].translation).normalized()
  flex=math.degrees(math.atan2(-direction.dot(z0),direction.dot(f0)));dev=math.degrees(math.atan2(direction.dot(r0),direction.dot(f0)))
  sane=1-smooth(95,135,max(abs(flex),abs(dev)))
  values={'JC_ElbowFlex75':tent(elbow,re,75,110),'JC_ElbowFlex110':tent(elbow,75,110,135),'JC_ElbowFlex135':clamp((elbow-110)/25),'JC_ElbowFlex20':clamp((re-elbow)/(re-20)) if re>21 else 0,
   'JC_WristFlexA':clamp(flex/40)*sane,'JC_WristFlexB':clamp(-flex/40)*sane,'JC_WristRadial':clamp(dev/20)*sane,'JC_WristUlnar':clamp(-dev/35)*sane}
  for k,v in values.items():
   n=k+'_'+side.upper()
   if n in keys:keys[n].value=v
  extra=[]
  for finger in ('index','middle','ring','pinky'):
   a,b,c=[finger+x+'_'+side for x in ('_metacarpal','_01','_02')]
   extra.append(max(0,angle(row[b].translation-row[a].translation,row[c].translation-row[b].translation)-angle(rest[b].translation-rest[a].translation,rest[c].translation-rest[b].translation)))
  axis=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
  rel=row[l].to_quaternion().inverted()@row[h].to_quaternion()@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
  if rel.w<0:rel=-rel
  roll=math.degrees(2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(axis),rel.w))
  sig=np.array([elbow,flex,dev,roll,*extra])
  for k in keys:
   if k.name.startswith('JC_Grip_'+side.upper()+'_'):
    delta=(np.array(extra)-np.array([float(x) for x in k.name.split('_')[3:]]))/12
   elif k.name.startswith('JC_Pose_'+side.upper()+'_'):
    delta=sig-np.array([-float(x[1:]) if x.startswith('m') else float(x) for x in k.name.split('_')[3:]])
    delta[3]=(delta[3]+180)%360-180;delta/=np.array([12,12,10,20,15,15,15,15])
   else:continue
   weight=math.exp(-.5*float(delta@delta));k.value=weight if weight>=.001 else 0
 bpy.context.view_layer.update()
morphs=morphs_full
rest_v=np.array([v.co[:] for v in skin.data.vertices]);skin.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in skin.data.loop_triangles])
_,weld=np.unique(np.round(rest_v,6),axis=0,return_inverse=True);tw=weld[tri];nv=int(weld.max())+1
center=np.array(rest['lowerarm_l'].translation);elbow_v=np.linalg.norm(rest_v-center,axis=1)<.065;elbow_t=elbow_v[tri].all(axis=1)
left_v=np.array([sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name.endswith('_l'))>.5 for v in skin.data.vertices]);left_t=left_v[tri].all(axis=1)
def evaluate(row):
 set_pose(row);morphs_full();r.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
 obj=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh();X=np.array([v.co[:] for v in mesh.vertices]);obj.to_mesh_clear()
 f=np.cross(X[tri[:,1]]-X[tri[:,0]],X[tri[:,2]]-X[tri[:,0]])
 vn=np.zeros((nv,3))
 for k in range(3):np.add.at(vn,tw[:,k],f)
 vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1.e-12)
 inverted=np.einsum('ij,ij->i',f,vn[tw].mean(axis=1))<0
 result={'elbow_fold_triangles':int((inverted&elbow_t).sum()),'left_arm_fold_triangles':int((inverted&left_t).sum()),'elbow_fold_area_mm2':float(np.linalg.norm(f[inverted&elbow_t],axis=1).sum()/2*1e6)}
 camera=np.c_[X,np.ones(len(X))]@np.array(C).T;x,y,z=camera[:,:3].T
 visible=(x>0)&(abs(y)<x*math.tan(math.radians(37.5))*16/9)&(abs(z)<x*math.tan(math.radians(37.5)))&left_v
 result['nearest_visible_left_arm_cm']=float(np.linalg.norm(camera[visible,:3],axis=1).min()) if visible.any() else None
 return result
samples=[]
for i in range(121):
 p=i/120
 for phase in (0,.25,.5,.75):samples.append({'progress':p,'phase':phase,**evaluate(runtime(p,phase))})
for i in range(121):
 ph=i/120;samples.append({'progress':1,'phase':ph,**evaluate(runtime(1,ph))})
actions=[]
for role,data in ue['clips'].items():
 family='mag10' if role.endswith('_mag10') else 'base'
 for i in range(data['keys']):actions.append({'role':role,'time':i/data['fps'],**evaluate(component(local_pose(role,i/data['fps'],family)))})
report={'source':ue.get('snapshot_origin'),'morph_driver':'Full C++-equivalent elbow/wrist/grip/pose families, threshold .001','samples':samples,'elbow_triangles':int(elbow_t.sum()),'max_elbow_fold_triangles':max(v['elbow_fold_triangles'] for v in samples),'max_left_fold_triangles':max(v['left_arm_fold_triangles'] for v in samples),'all_actions_samples':actions,'all_actions_max_elbow_fold_triangles':max(v['elbow_fold_triangles'] for v in actions),'runtime_game_tested':False}
(O/'surface_scan.json').write_text(json.dumps(report,indent=2));print('ELBOW_SURFACE_SCAN',json.dumps({k:v for k,v in report.items() if k not in ('samples','all_actions_samples')}),flush=True)
folder=O/'ElbowViews';folder.mkdir(exist_ok=True);s.render.resolution_x=800;s.render.resolution_y=600
for label,p,ph in [('idle',0,0),('raise',.15,0),('middle',.4,.4),('carry',1,.25)]:
 row=runtime(p,ph);set_pose(row);morphs_full();r.matrix_world=Matrix.Identity(4)
 target=row['lowerarm_l'].translation
 for side,off in [('outer',(-.28,-.15,.15)),('inner',(.22,.13,-.08))]:
  cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.30
  s.render.filepath=str(folder/(label+'_'+side+'.png'));bpy.ops.render.render(write_still=True)
 render(row,folder/(label+'_game.png'))
