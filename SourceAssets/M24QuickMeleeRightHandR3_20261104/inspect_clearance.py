from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'surface','exec'))
base=json.load(gzip.open(O/'digit_path_patch.json.gz','rt'));final=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
for family,t in [('skeleton_base',.4666666666666667),('skeleton_base_stable',.8833333333333333),('skeleton_base',.11666666666666667),('skeleton_base',.25)]:
    kind='stable' if 'stable' in family else 'Default';bv=weapon_tree(kind,'mag5');a=compose(base[family],t)[0];b=compose(final[family],t)[0];ids=np.r_[hand_ids[::3],arm_ids[::15]];inv=rest['WPN_root']@b['WPN_root'].inverted()
    def cloud(row):return (np.c_[skin_points(row,ids,True),np.ones(len(ids))]@np.asarray(inv).T)[:,:3]
    A=cloud(a);B=cloud(b);ds=signed_distance(bv,B,True);k=int(np.argmin(ds));v=Vector(B[k]);print('FIT',family,t,RIGHT[int(W[ids[k]].argmax())],(B[k]-A[k])*1000,'inside',ds[k],flush=True)
    for name in ('stock','grip_'+kind,'native_body','front','mag5'):
        vs,fs=geometry[name];tree=BVHTree.FromPolygons(vs,fs,all_triangles=True);p,n,_,d=tree.find_nearest(v)
        print(name,round(d*1000,2),'side',round((v-p).dot(n)*1000,2),'normal',[round(x,2) for x in n],'signed',signed_distance(tree,[v],True),flush=True)
