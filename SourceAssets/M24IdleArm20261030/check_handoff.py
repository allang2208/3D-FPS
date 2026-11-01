from pathlib import Path
exec(compile((Path(__file__).parent/'author_profiles.py').read_text().split('report={};previews={};modified={}')[0],'setup','exec'))
patch=json.loads((O/'profile_patch.json').read_text())['profiles'];P=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data]);cor=np.load(O.parent/'M24BipodHands20261030/elbow_correctives.npz');curves=json.loads((O.parent/'M24BipodHands20261030/elbow_curves.json').read_text())
for n in cor.files:
    key=skin.shape_key_add(name=n,from_mix=False);key.data.foreach_set('co',(P+cor[n]/100).ravel());key.value=0
skin.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in skin.data.loop_triangles]);_,weld=np.unique(np.round(P,6),axis=0,return_inverse=True);tw=weld[tri];nv=int(weld.max())+1
elbow=np.linalg.norm(P-np.array(rest[l].translation),axis=1)<.065;mask=elbow[tri].all(axis=1);output={}
for family in ('base','mag10'):
    entry=next(c for c in patch[family] if 'Bipod_' in c['base']);clip=roles[entry['base']];results=[];max_step=0.;last=None
    for i in range(49):
        t=i/100;row,_=local_pose(clip,entry,t);set_pose(row)
        for n,c in curves.items():skin.data.shape_keys.key_blocks[n].value=float(np.interp(t,c['times'],c['values']))
        bpy.context.view_layer.update();ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();X=np.array([v.co[:] for v in me.vertices]);ob.to_mesh_clear();face=np.cross(X[tri[:,1]]-X[tri[:,0]],X[tri[:,2]]-X[tri[:,0]]);normals=np.zeros((nv,3))
        for j in range(3):np.add.at(normals,tw[:,j],face)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-12);folds=np.einsum('ij,ij->i',face,normals[tw].mean(axis=1))<0
        results.append({'time':t,'elbow_folds':int((folds&mask).sum())})
        if last is not None:max_step=max(max_step,(row[h].translation-last).length*100)
        last=row[h].translation.copy()
    output[family]={'samples':results,'max_elbow_folds':max(x['elbow_folds'] for x in results),'max_wrist_step_cm_per_10ms':max_step}
(O/'handoff.json').write_text(json.dumps(output,indent=2));print('IDLE_HANDOFF',json.dumps({f:{k:v for k,v in entry.items() if k!='samples'} for f,entry in output.items()}),flush=True)
