"""Current native right-skin samples and actual assembled-weapon surfaces."""
exec(compile((Path(__file__).parent/'right.py').read_text().split("if __name__=='__main__':")[0],'native right helpers','exec'))
geometry=setup_geometry()
weapon=json.loads((S/'M24AcceptedGrip20261103/Review/weapon_geometry.json').read_text())
geometry['native_body']=([Vector((p[0]*.01,-p[1]*.01,p[2]*.01)) for p in weapon['positions']],
                         [list(reversed(f['vertices'])) for f in weapon['faces'] if f['material']==2])
geometry['mag5']=([Vector((p[0]*.01,-p[1]*.01,p[2]*.01)) for p in weapon['positions']],
                  [list(reversed(f['vertices'])) for f in weapon['faces'] if f['material']==3])
with bpy.data.libraries.load(str(S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),link=False) as (src,dst):
    dst.objects=['M24_Magazine10']
mag=dst.objects[0];mag.data.calc_loop_triangles()
geometry['mag10']=([v.co.copy() for v in mag.data.vertices],[tuple(t.vertices) for t in mag.data.loop_triangles])
def weapon_tree(kind,magazine):
    points=[];faces=[]
    for name in ('stock','front','grip_'+kind,'native_body',magazine):
        p,f=geometry[name];off=len(points);points.extend(p);faces.extend([tuple(off+i for i in face) for face in f])
    return BVHTree.FromPolygons(points,faces,all_triangles=True)
V=np.asarray([[p[0]*.01,-p[1]*.01,p[2]*.01,1.] for p in G['positions']])
RIGHT=[n for n in names if under(n,'upperarm_r')];ri={n:i for i,n in enumerate(RIGHT)}
W=np.zeros((len(V),len(RIGHT)))
for i,ws in G['weights'].items():
    for n,w in ws.items():
        if n in ri:W[int(i),ri[n]]=w
handbones=[n for n in RIGHT if under(n,'hand_r')]
hand_ids=np.where(W[:,[ri[n] for n in handbones]].sum(1)>.985)[0]
right_ids=np.where(W.sum(1)>.985)[0]
arm_ids=np.setdiff1d(right_ids,hand_ids)
inverses=np.asarray([np.asarray(native[n].inverted()) for n in RIGHT])
morph=np.load(S/'M24ThumbRootRoute20261102/native_correctives.npz')
morph_cache={}
exec(compile((S/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'current joint correctives','exec'))
def skin_points(row,ids,correctives=False):
    points=V[ids].copy()
    if correctives:
        values,_=corrective_weights(row,morph.files)
        for n,w in values.items():
            if n not in morph_cache:morph_cache[n]=morph[n]
            points[:,:3]+=morph_cache[n][ids]*w
    mats=np.asarray([np.asarray(row[n]) for n in RIGHT])@inverses
    blend=np.einsum('vk,kij->vij',W[ids],mats,optimize=True)
    return np.einsum('vij,vj->vi',blend,points,optimize=True)[:,:3]
rays=[Vector(v).normalized() for v in ((1,.073,.047),(.031,1,.051),(.047,.061,1))]
def signed_distance(bv,X,exact=False):
    out=[]
    for x in X:
        p=Vector(x);nearest,nearest_normal,_,dist=bv.find_nearest(p);votes=0
        if dist<.04:
            for direction in rays:
                if not exact:
                    hit,n,_,_=bv.ray_cast(p,direction);votes+=hit is not None and n.dot(direction)>0
                else:
                    origin=p;count=0
                    for _ in range(40):
                        hit,_,_,_=bv.ray_cast(origin,direction)
                        if hit is None:break
                        count+=1;origin=hit+direction*.000002
                    votes+=count%2
        if exact and votes>=2:
            # Open grip cavities can give odd ray counts outside the surface.
            # Require the directional surface normals to agree as well.
            normal_votes=0
            for direction in rays:
                hit,n,_,_=bv.ray_cast(p,direction);normal_votes+=hit is not None and n.dot(direction)>0
            if normal_votes<2:votes=0
        # Multiple open attachment shells can make ray-only classification
        # report distant exterior skin as inside. Require the nearest face's
        # side to agree, as in the previous native-skin review workflow.
        # At an open cut edge a skin point can be tangent to the face plane
        # while far from the edge. Floating-point noise then flips the sign
        # of a millimetre-scale nearest-edge distance. Do not call that a
        # penetration without a measurable inward face-normal component.
        inward=-(p-nearest).dot(nearest_normal)
        if inward<max(.0001,.15*dist):votes=0
        out.append(dist*1000*(-1 if votes>=2 else 1))
    return np.asarray(out)
def surface_penalty(row,bv,include_arm=False):
    ids=hand_ids[::7] if not include_arm else np.r_[hand_ids[::9],arm_ids[::20]]
    native_row={n:rest['WPN_root']@row['WPN_root'].inverted()@m for n,m in row.items()}
    X=skin_points(native_row,ids,True)
    d=signed_distance(bv,X)
    p=np.maximum(-d-.6,0.)
    return float(25*np.mean(p*p)+15*np.max(p)**2)
