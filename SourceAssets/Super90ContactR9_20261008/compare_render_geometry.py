from pathlib import Path
O=Path(__file__).parent;src=O/'render_saved.py';ns={'__file__':str(src)}
exec(compile(src.read_text().split('items=[]')[0],str(src),'exec'),ns)
bpy=ns['bpy'];s=ns['s'];Matrix=ns['Matrix'];json=ns['json'];np=__import__('numpy')
p=s['pose'](0,7,False,'vertical')[0];fit=json.loads((O/'grip_hand_canonical.json').read_text())['vertical'];s['arm'](p,s['copy'](p),Matrix(fit['hand']),'l')
for n in s['finger_names']['l']:p[n]=p[s['parents'][n]]@Matrix(fit['local'][n])
ns['apply'](p);out=[]
for ob in ns['groups']['weapon']:
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 selected=set()
 for poly in mesh.polygons:
  if 'Bare' in ob.data.materials[poly.material_index].name:selected.update(poly.vertices)
 out.extend([list(ob.matrix_world@mesh.vertices[i].co) for i in selected]);ev.to_mesh_clear()
D=np.load(O/'fit_inputs.npz');names=D['names'].tolist();vs=D['vertices'];ws=D['weights'];result=np.zeros((len(vs),3))
for j,n in enumerate(names):result+=(vs@np.linalg.inv(D['rest'][j]).T@np.asarray(p[n]).T)[:,:3]*ws[:,j,None]
np.savez_compressed(O/'compare_render_geometry.npz',render=out,calculated=result,weights=ws,names=names)
print('GEOMETRY_EXPORTED',len(out),flush=True)
