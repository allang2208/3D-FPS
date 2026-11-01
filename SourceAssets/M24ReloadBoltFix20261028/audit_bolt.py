from pathlib import Path
import ast
exec(compile((Path(__file__).parent/'review.py').read_text().split('setup_render();s.render.resolution_x=960')[0],'review','exec'))
setup_render()
tree=ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full')),'morphs','exec'))
morphs=morphs_full
root_v=np.array([sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name in ('clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l'))>.5 for v in skin.data.vertices])
shoulder_axis=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).normalized()
proximal_v=root_v & np.array([(v.co-rest['upperarm_l'].translation).dot(shoulder_axis)<.15 for v in skin.data.vertices])
def stats(row):
 set_pose(row);morphs();r.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
 ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();X=np.array([v.co[:] for v in mesh.vertices]);ob.to_mesh_clear()
 Y=(np.c_[X,np.ones(len(X))]@np.array(C).T)[:,:3];x,y,z=Y.T
 u=.5+y/(2*np.maximum(x,.01)*math.tan(math.radians(37.5))*16/9);v=.5-z/(2*np.maximum(x,.01)*math.tan(math.radians(37.5)))
 vis=(x>1)&(u>0)&(u<1)&(v>0)&(v<1)&root_v
 return {'root_visible_vertices':int(vis.sum()),'proximal_root_visible_vertices':int((vis&proximal_v).sum()),'root_nearest_cm':float(np.linalg.norm(Y[vis],axis=1).min()) if vis.any() else None,'root_top':float(v[vis].min()) if vis.any() else None,'bones':{n:list(C@row[n].translation) for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l')}}
out=[];folder=O/'before';folder.mkdir(exist_ok=True)
for role in ('fire','cycle'):
 data=ue['clips'][role]
 for i in range(data['keys']):out.append({'role':role,'frame':i,**stats(component(local_pose(role,i/data['fps'])))})
 for f in (0,8,16,24,30,36,42,50):
  render(component(local_pose(role,f/30)),folder/f'{role}_{f:02}.png')
(O/'bolt_before.json').write_text(json.dumps(out,indent=2))
print('BOLT_ROOT_AUDIT',json.dumps(sorted(out,key=lambda x:x['root_top'] or 1)[:3]),flush=True)
