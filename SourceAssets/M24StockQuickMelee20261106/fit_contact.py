"""Fit a power grasp on the shared forward neck of both installed stocks."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'current native skin','exec'))
trees=[BVHTree.FromPolygons(*geometry[k],all_triangles=True) for k in ('stock','carbon','stock_native','carbon_native')]
grip_trees=[BVHTree.FromPolygons(*geometry['grip_'+k],all_triangles=True) for k in ('Default','balanced','phantom','stable')]
tree=ast.parse((S/'M24QuickMeleeRightHandR3_20261104/release_arc.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='move_hand')),'fixed-length transport','exec'))
owned=['clavicle_r',*[n for n in names if under(n,'upperarm_r')],'ik_hand_r']
original,_=compose(entry('skeleton_base','quick_melee'),.25)
bind=rest['WPN_root']@original['WPN_root'].inverted()
reference={n:bind@m for n,m in original.items()}
H0=reference['hand_r'].copy();digits=[f'{d}_{i:02d}_r' for d in ('index','middle','ring','pinky','thumb') for i in (1,2,3)]
initial={n:local(reference,n).to_quaternion() for n in digits}
handbones=[n for n in names if under(n,'hand_r')]
handlocals={n:local(reference,n) for n in handbones}
ids=hand_ids[::7]
Wpre=np.einsum('vk,kij,vj->kvi',W[ids],inverses,V[ids],optimize=True)
dominant=W[ids].argmax(1)
palm=np.isin(dominant,[ri[n] for n in RIGHT if n=='hand_r' or 'metacarpal' in n])
tips={d:np.isin(dominant,[ri[f'{d}_{i:02d}_r'] for i in (2,3)]) for d in ('index','middle','ring','pinky','thumb')}

def make(v,angles):
    row=clone(reference)
    q=Euler(tuple(math.radians(x) for x in v[3:]),'XYZ').to_quaternion()
    pivot=H0.translation+Vector((.04,0,.06))
    target=Matrix.LocRotScale(pivot+Vector(v[:3])*.001-q@(pivot-H0.translation),q@H0.to_quaternion(),H0.to_scale())
    row=move_hand(reference,target.translation-H0.translation)
    row['hand_r']=target
    for n in handbones:
        if n=='hand_r':continue
        p,q,s=handlocals[n].decompose()
        if n in angles:q=initial[n]@Quaternion((0,0,1),math.radians(angles[n]))
        row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,s)
    return row

def cost(v,angles):
    row=make(v,angles)
    pts=skin_points(row,ids,True)
    score=0.
    for bv in trees:
        d=signed_distance(bv,pts)
        penetration=np.maximum(.6-d,0)
        score+=25*float(np.mean(penetration**2))+25*float(penetration.max()**2)
        pd=np.sort(np.abs(d[palm]))[:12]
        score+=.55*float(np.mean((pd-1.5)**2))
        for digit,mask in tips.items():
            near=np.sort(np.abs(d[mask]))[:5]
            score+=.28*float(np.mean((near-1.5)**2))
    for bv in grip_trees:
        d=signed_distance(bv,pts)
        penetration=np.maximum(.8-d,0)
        score+=30*float(np.mean(penetration**2))+35*float(penetration.max()**2)
    score+=.004*(v[0]**2+(v[1]-38)**2+v[2]**2)+.07*sum(x*x for x in v[3:])
    score+=.03*sum(x*x for x in angles.values())
    return score

prior=json.loads((O/'contact.json').read_text()) if (O/'contact.json').exists() else None
angles=prior['digit_angles'] if prior else {n:0. for n in digits}
v=prior['translation_rotation'] if prior else [0.,38.,0.,0.,0.,0.];best=cost(v,angles)
for y in (20.,30.,40.,50.,60.):
    for z in (-15.,-5.,5.,15.):
        trial=[0.,y,z,0.,0.,0.];value=cost(trial,angles)
        if value<best:v,best=trial,value
for round in range(3):
    for step in (8.,4.,2.,1.):
        for axis in range(6):
            for sign in (-1,1):
                a=v.copy();a[axis]+=sign*step
                lo,hi=((-25,25) if axis in (0,2) else (15,65) if axis==1 else (-18,18))
                a[axis]=max(lo,min(hi,a[axis]));value=cost(a,angles)
                if value<best:v,best=a,value
        for n in digits:
            for sign in (-1,1):
                a=dict(angles);a[n]=max(-18,min(18,a[n]+sign*step));value=cost(v,a)
                if value<best:angles,best=a,value
    print('CONTACT_ROUND',round,v,best,flush=True)
row=make(v,angles)
(O/'contact.json').write_text(json.dumps({'hand':[list(v) for v in row['hand_r']],'rotations':{n:list(local(row,n).to_quaternion()) for n in digits},'translation_rotation':v,'digit_angles':angles,'cost':best,'shared_region':'forward stock neck; fitted simultaneously to carbon and skeleton surfaces'},indent=2))
print('CONTACT_READY',flush=True)
