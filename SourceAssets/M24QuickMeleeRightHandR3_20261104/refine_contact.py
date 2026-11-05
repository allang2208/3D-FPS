"""Fit held contact with actual JC deformation, preserving the natural thumb."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'surface','exec'))
g=json.loads((O/'stock_grip.json').read_text());H0=Matrix(g['hand']);Q0={n:Quaternion(q) for n,q in g['rotations'].items()}
samples=[compose(entry('skeleton_base','quick_melee'),t)[0] for t in (.15,.25,.325,.46)]
ref=samples[1];loc={n:local(ref,n) for n in handbones if n!='hand_r'}
bv=BVHTree.FromPolygons(*geometry['stock'],all_triangles=True);ids=hand_ids[::4]
def candidate(v):
    H=H0.copy();H.translation+=Vector(v[:3])*.001
    qs=dict(Q0)
    qs['thumb_01_r']=Q0['thumb_01_r']@Euler(tuple(math.radians(x) for x in v[3:6]),'XYZ').to_quaternion()
    for i in (2,3):qs[f'thumb_{i:02d}_r']=Q0[f'thumb_{i:02d}_r']@Quaternion((0,0,1),math.radians(v[i+4]))
    return H,qs
def score(v,detail=False):
    H,qs=candidate(v);total=0.;worst=0.
    for reference in samples:
        row=clone(reference);root=reference['WPN_root']@rest['WPN_root'].inverted();row['hand_r']=root@H
        for n in handbones:
            if n=='hand_r':continue
            p,q,s=loc[n].decompose();row[n]=row[parents[n]]@Matrix.LocRotScale(p,qs.get(n,q),s)
        row,info=fit_arm(reference,row,cap=45.)
        X=skin_points(row,ids,True);X=(np.c_[X,np.ones(len(X))]@np.asarray(root.inverted()).T)[:,:3]
        ds=signed_distance(bv,X);pen=np.maximum(-ds-.25,0.)
        worst=max(worst,float(max(pen)));total+=40*np.mean(pen*pen)+35*max(pen)**2
        # Preserve broadly distributed contact instead of a single touching tip.
        for digit in ('index','middle','ring','pinky','thumb'):
            mask=W[ids,ri[digit+'_03_r']]+W[ids,ri[digit+'_02_r']]>.5
            if np.any(mask):total+=.4*np.mean((np.sort(abs(ds[mask]))[:6]-1.)**2)
        total+=info['score']*.04
    total+=.08*sum(x*x for x in v[:3])+.1*sum(x*x for x in v[3:])
    return {'score':float(total),'sampled_penetration_over_margin_mm':worst} if detail else float(total)
v=[0.]*8;value=score(v)
for step in (4.,2.,1.,.5):
    for _ in range(2):
        for axis in range(8):
            for sign in (-1,1):
                trial=v.copy();trial[axis]=max(-8.,min(8.,trial[axis]+step*sign));s=score(trial)
                if s<value:v,value=trial,s
H,qs=candidate(v);g['hand']=[list(r) for r in H];g['rotations']={n:list(q) for n,q in qs.items()}
g['corrected_skin_refinement']={'parameters':v,**score(v,True)}
(O/'stock_grip.json').write_text(json.dumps(g,indent=2));print('CORRECTED_CONTACT_FIT',g['corrected_skin_refinement'],flush=True)
