"""Focused full-skin readback check of both saved bipod clip branches."""
from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
P=np.array([v.co[:] for v in skin.data.vertices]);skin.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in skin.data.loop_triangles])
_,weld=np.unique(np.round(P,6),axis=0,return_inverse=True);tw=weld[tri];nv=int(weld.max())+1
elbow=np.linalg.norm(P-np.array(rest['lowerarm_l'].translation),axis=1)<.065;mask=elbow[tri].all(axis=1)
result={}
for family in ('base','mag10'):
    samples=[]
    for i in range(49):
        t=i/100;set_pose(sample_pose(t,family),t,family=family);ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();X=np.array([v.co[:] for v in me.vertices]);ob.to_mesh_clear()
        face=np.cross(X[tri[:,1]]-X[tri[:,0]],X[tri[:,2]]-X[tri[:,0]]);normals=np.zeros((nv,3))
        for j in range(3):np.add.at(normals,tw[:,j],face)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-12)
        folds=np.einsum('ij,ij->i',face,normals[tw].mean(axis=1))<0
        samples.append({'t':t,'elbow_fold_triangles':int((folds&mask).sum())})
    result[family]={'max_elbow_folds':max(x['elbow_fold_triangles'] for x in samples),'samples':samples}
(O/'Review/saved_surface_check.json').write_text(json.dumps(result,indent=2))
print('SAVED_SURFACE',json.dumps({k:v['max_elbow_folds'] for k,v in result.items()}),flush=True)
