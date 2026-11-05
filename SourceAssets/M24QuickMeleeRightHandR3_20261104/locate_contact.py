from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'surface','exec'))
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
for family,clip in patch.items():D['profiles'][family]['clips']=[clip if c['base']==clip['base'] else c for c in D['profiles'][family]['clips']]
for family,t in [('skeleton_base',.13333333333333333),('skeleton_base',.25),('skeleton_base',.16666666666666666),('skeleton_mag10_balanced',.85)]:
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default');magazine='mag10' if 'mag10' in family else 'mag5';bv=weapon_tree(kind,magazine)
    row,_=compose(entry(family,'quick_melee'),t);ids=hand_ids[::3]
    X=skin_points(row,ids,True);inv=rest['WPN_root']@row['WPN_root'].inverted();X=(np.c_[X,np.ones(len(X))]@np.asarray(inv).T)[:,:3]
    ds=signed_distance(bv,X,True);k=int(np.argmin(ds));p=Vector(X[k]);print('SAMPLE',family,t,RIGHT[int(W[ids[k]].argmax())],list(p),ds[k],flush=True)
    for name in ('stock','front','grip_'+kind,'native_body',magazine):
        vs,fs=geometry[name];tree=BVHTree.FromPolygons(vs,fs,all_triangles=True)
        point,normal,face,dist=tree.find_nearest(p)
        print('PART',name,'distance',dist*1000,'normal_side',(p-point).dot(normal)*1000,'parity',signed_distance(tree,[p],True).tolist(),'normal_vote',signed_distance(tree,[p],False).tolist(),flush=True)
