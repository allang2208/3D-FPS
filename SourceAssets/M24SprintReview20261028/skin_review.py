from pathlib import Path
code=(Path(__file__).parent/'review.py').read_text()
exec(compile(code.split('setup_render();s.render.resolution_x=960')[0],'runtime_review','exec'))
setup_render();r.matrix_world=Matrix.Identity(4)
indices={n:i for i,n in enumerate(names)};weights=np.zeros((len(skin.data.vertices),len(names)))
for v in skin.data.vertices:
 for g in v.groups:
  n=skin.vertex_groups[g.group].name
  if n in indices:weights[v.index,indices[n]]=g.weight
hands={side:np.where(weights[:,[indices[n] for n in names if under(n,'hand_'+side)]].sum(1)>.95)[0] for side in ('l','r')}
def vertices(row):
 set_pose(row);morphs();r.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
 mesh=skin.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
 vs=np.array([list(v.co)+[1] for v in mesh.vertices]);skin.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
 return vs
idle=component(local_pose('idle',0));base=vertices(idle)@np.array(idle['WPN_root'].inverted()).T
report={'origin':ue.get('snapshot_origin'),'hand_surface_drift_from_idle_mm':{'l':0.,'r':0.},'closest_visible_arm_cm':1.e9,'samples':[],'uses_joint_corrective_shapes':True}
for p,ph in [(x,y) for x in (0,.15,.3,.5,.65,.8,1) for y in (0,.25,.5,.75)]:
 row=runtime(p,ph);vs=vertices(row);local=vs@np.array(row['WPN_root'].inverted()).T
 for side,ix in hands.items():report['hand_surface_drift_from_idle_mm'][side]=max(report['hand_surface_drift_from_idle_mm'][side],float(np.linalg.norm(local[ix,:3]-base[ix,:3],axis=1).max()*1000))
 cam_points=vs@np.array(C).T;x=cam_points[:,0];y=cam_points[:,1];z=cam_points[:,2]
 visible=(x>1)&(abs(y)<x*math.tan(math.radians(37.5))*16/9)&(abs(z)<x*math.tan(math.radians(37.5)))
 nearest=float(np.linalg.norm(cam_points[visible,:3],axis=1).min()) if visible.any() else None
 if nearest is not None:report['closest_visible_arm_cm']=min(report['closest_visible_arm_cm'],nearest)
 report['samples'].append({'progress':p,'phase':ph,'nearest_visible_arm_cm':nearest})
(O/'skin_review.json').write_text(json.dumps(report,indent=2));print('M24_SKIN_REVIEW',json.dumps({k:v for k,v in report.items() if k!='samples'}),flush=True)
