from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'solver','exec'))
from collections import Counter
patch=json.loads((O/'profile_patch.json').read_text())
skin.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in skin.data.loop_triangles]);R=np.array([v.co[:] for v in skin.data.vertices])
_,weld=np.unique(np.round(R,6),axis=0,return_inverse=True);tw=weld[tri];nv=int(weld.max())+1
left=np.array([sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name.endswith('_l'))>.5 for v in skin.data.vertices])
root_region=left&(np.linalg.norm(R-np.array(rest['upperarm_l'].translation),axis=1)<.17)
upper_region=left&(np.linalg.norm(R-np.array(rest['lowerarm_l'].translation),axis=1)<.10)
edge=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in skin.data.polygons for i in range(len(p.vertices)))
boundary=np.array(sorted({i for e,count in edge.items() if count==1 for i in e if root_region[i]}))
def surface(row):
    set_pose(row);r.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update();obj=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh();X=np.array([v.co[:] for v in mesh.vertices]);obj.to_mesh_clear()
    cross=np.cross(X[tri[:,1]]-X[tri[:,0]],X[tri[:,2]]-X[tri[:,0]]);vn=np.zeros((nv,3))
    for k in range(3):np.add.at(vn,tw[:,k],cross)
    vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1.e-12);fold=np.einsum('ij,ij->i',cross,vn[tw].mean(axis=1))<0
    camera=np.c_[X,np.ones(len(X))]@np.array(C).T;x,y,z=camera[:,:3].T
    visible=(x>1)&(abs(y)<x*math.tan(math.radians(37.5))*16/9)&(abs(z)<x*math.tan(math.radians(37.5)))
    return {'root_fold_triangles':int((fold&root_region[tri].all(axis=1)).sum()),'elbow_fold_triangles':int((fold&upper_region[tri].all(axis=1)).sum()),'root_opening_vertices_visible':int(visible[boundary].sum()),'visible_arm_nearest_cm':float(np.linalg.norm(camera[visible&left,:3],axis=1).min()) if (visible&left).any() else None}
report=[]
for p in (0,.1,.2,.3,.4,.5,.65,.8,1):
    for phase in (0,.25,.5,.75) if p>=.65 else (0,):
        report.append({'progress':p,'phase':phase,'before':surface(runtime(p,phase)),'after':surface(runtime(p,phase,profiles=patch['profiles']))})
(O/'surface_review.json').write_text(json.dumps(report,indent=2));summary={label:{key:max(v[label][key] for v in report) for key in ('root_fold_triangles','elbow_fold_triangles','root_opening_vertices_visible')} for label in ('before','after')}
print('SHOULDER_SURFACE',json.dumps(summary),flush=True)
