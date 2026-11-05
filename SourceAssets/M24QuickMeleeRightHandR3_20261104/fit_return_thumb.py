"""Fit one smooth thumb-opening gesture per grip for the return from stock."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'assembled geometry','exec'))
script=(O/'release_arc.py').read_text();owned=['clavicle_r',*RIGHT,'ik_hand_r']
exec(script[script.index('def release_offset'):script.index('for family,clip in source.items()')]);thumb_offsets={};stable_palm=Vector()
clips=json.load(gzip.open(O/'contact_fit_patch.json.gz','rt'))
thumb_names=[f'thumb_{i:02d}_r' for i in (1,2,3)]
thumb_mask=W[:,[ri[n] for n in thumb_names]].sum(1)
ids=hand_ids[thumb_mask[hand_ids]>.08];ids=ids[::2]
times=[i/120 for i in range(75,85)]

def signed_depths(tree,points):
    depths=[]
    for point in points:
        v=Vector(point);p,n,_,d=tree.find_nearest(v)
        if (v-p).dot(n)>=0 or d>.025:continue
        if signed_distance(tree,[v],True)[0]<0:depths.append(d*1000)
    return depths

def clouds(kind):
    records=[]
    for family in (('skeleton_base','skeleton_mag10') if kind=='Default' else ('skeleton_base_stable','skeleton_mag10_stable')):
        for t in times:
            row,_=compose(clips[family],t);gun=row['WPN_root']@rest['WPN_root'].inverted()
            row=move_hand(row,gun.to_3x3()@release_offset(t,kind));open_fingers(row,t,kind)
            inv=gun.inverted();root=(inv@row['thumb_01_r']).translation;tip=(inv@row['thumb_03_r']).translation;axis=tip-root
            X=(np.c_[skin_points(row,ids,True),np.ones(len(ids))]@np.asarray(inv).T)[:,:3]
            records.append((X,np.asarray(root),axis,smooth((t-.626)/.018)*(1-smooth((t-.668)/.016))))
    return records

result={}
for kind in ('Default','stable'):
    tree=weapon_tree(kind,'mag5')
    if kind=='stable':
        # Route the open hand around the back of this grip. The stock sits just
        # above it, so both surfaces must participate in the choice of path.
        from itertools import product
        palm_ids=np.unique(np.r_[hand_ids[::4],hand_ids[::3],arm_ids[::15]])
        samples=[]
        for family in ('skeleton_base_stable','skeleton_mag10_stable'):
            for t in times:
                row,_=compose(clips[family],t);gun=row['WPN_root']@rest['WPN_root'].inverted()
                row=move_hand(row,gun.to_3x3()@release_offset(t,kind));open_fingers(row,t,kind)
                X=(np.c_[skin_points(row,palm_ids,True),np.ones(len(palm_ids))]@np.asarray(gun.inverted()).T)[:,:3]
                near=[p for p in X if tree.find_nearest(Vector(p))[3]<.05]
                samples.append((np.asarray(near),smooth((t-.622)/.022)*(1-smooth((t-.673)/.021))))
        def palm_cost(v):
            depth=[]
            for X,w in samples:depth.extend(signed_depths(tree,X+v*(w*.001)))
            return 90*max(depth,default=0.)**2+.14*sum(d*d for d in depth)+.008*np.dot(v,v)
        seeds=[np.array(v,float) for v in product((-18.,0.,18.),repeat=3)]
        seeds.extend([np.array((0.,y,z)) for y in (-35.,-25.,25.,35.) for z in (-20.,0.,20.)]);p=min(seeds,key=palm_cost);score=palm_cost(p)
        for step in (7.,3.,1.):
            for axis in range(3):
                for sign in (-1,1):
                    v=p.copy();v[axis]=np.clip(v[axis]+step*sign,-40.,40.);cost_v=palm_cost(v)
                    if cost_v<score:p,score=v,cost_v
        stable_palm=Vector(p);(O/'stable_palm_return.json').write_text(json.dumps(p.tolist()));print('STABLE_PALM_RETURN',list(stable_palm),score,flush=True)
    records=clouds(kind)
    def cost(v):
        depth=[]
        for X,pivot,axis,weight in records:
            q=axis.rotation_difference(axis+Vector(v)*(.001*weight));R=np.asarray(q.to_matrix())
            corrected=X+((X-pivot)@(R-np.eye(3)).T)*thumb_mask[ids,None]
            depth.extend(signed_depths(tree,corrected))
        worst=max(depth,default=0.)
        return 90*worst**2+.3*sum(d*d for d in depth)+.004*np.dot(v,v)
    from itertools import product
    seeds=[np.array([a,b,c],float) for a,b,c in product((-18.,0.,18.),repeat=3)]
    seeds+= [np.array(v,float) for v in [(32,0,0),(-32,0,0),(0,32,0),(0,-32,0),(0,0,32),(0,0,-32)]]
    best=min(seeds,key=cost);score=cost(best)
    for step in (8.,4.,2.,1.):
        for _ in range(2):
            for axis in range(3):
                for sign in (-1,1):
                    v=best.copy();v[axis]=np.clip(v[axis]+step*sign,-34.,34.);value=cost(v)
                    if value<score:best,score=v,value
    result[kind]=best.tolist();print('RETURN_THUMB',kind,result[kind],'cost',score,flush=True)
(O/'thumb_return_offsets.json').write_text(json.dumps(result,indent=2))
