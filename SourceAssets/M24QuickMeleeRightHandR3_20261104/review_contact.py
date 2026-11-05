"""Requested right-hand contact and twist review, on current native skin."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'skin and geometry','exec'))
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
before={family:entry(family,'quick_melee') for family in patch}
for family,clip in patch.items():
    D['profiles'][family]['clips']=[clip if c['base']==clip['base'] else c for c in D['profiles'][family]['clips']]
times=sorted(set([i/60 for i in range(55)]+[.08,.125,.25,.325,.55,.65]))
ids=np.r_[hand_ids[::3],arm_ids[::15]]
R={'complete':False,'scope':'Right hand and arm only, native skin with runtime-equivalent JC morphs. Count inside points when three-direction ray parity, ray-hit normal consensus and nearest triangle side agree. Keep ambiguous ray-only measurements separately (open grip cavities).','sample_times':times,'hand_vertex_stride':3,'arm_vertex_stride':15,'all_vertices':False,'continuous_time_proof':False,'runtime_tested':False,'profiles':{}}
for family in patch:
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default');bv=weapon_tree(kind,'mag10' if 'mag10' in family else 'mag5')
    rows=[]
    for t in times:
        row,_=compose(entry(family,'quick_melee'),t);_,sig=corrective_weights(row,[])
        X=skin_points(row,ids,True);inv=rest['WPN_root']@row['WPN_root'].inverted()
        X=(np.c_[X,np.ones(len(X))]@np.asarray(inv).T)[:,:3]
        ray_ds=signed_distance(bv,X,True);ds=ray_ds.copy()
        for index in np.flatnonzero(ds<0):
            vertex=Vector(X[index]);nearest,normal,_,_=bv.find_nearest(vertex)
            if (vertex-nearest).dot(normal)>0:ds[index]=abs(ds[index])
        k=int(np.argmin(ds));worst=ids[k]
        rows.append({'time':t,'max_penetration_mm':float(max(0.,-ds[k])),'ray_only_max_mm':float(max(0.,-min(ray_ds))),'vertices_deeper_than_1mm':int(np.sum(ds<-1.)),'worst_bone':RIGHT[int(W[worst].argmax())],'wrist_flex_dev_roll':sig['r'][1:4]})
    worst=max(rows,key=lambda v:v['max_penetration_mm'])
    R['profiles'][family]={'worst':worst,'samples':rows};print('RIGHT_CONTACT_REVIEW',family,worst,flush=True)
    (O/'right_contact_review.json').write_text(json.dumps(R,indent=2))
R['complete']=True;(O/'right_contact_review.json').write_text(json.dumps(R,indent=2));print('M24_RIGHT_CONTACT_REVIEW_COMPLETE',flush=True)
