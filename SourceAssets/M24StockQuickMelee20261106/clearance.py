"""Native V9 skin collision helpers for the two requested stock assemblies."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'surface','exec'))
geometry['native_front']=(geometry['native_body'][0],[list(reversed(f['vertices'])) for f in weapon['faces'] if f['material']==5])
LEFT=[n for n in names if under(n,'upperarm_l')];li={n:i for i,n in enumerate(LEFT)}
LW=np.zeros((len(V),len(LEFT)))
for i,weights in G['weights'].items():
    for n,w in weights.items():
        if n in li:LW[int(i),li[n]]=w
left_ids=np.where(LW.sum(1)>.985)[0];left_map={int(v):i for i,v in enumerate(left_ids)}
left_faces=[tuple(left_map[i] for i in f['vertices']) for f in G['faces'] if all(i in left_map for i in f['vertices'])]
left_inv=np.asarray([np.asarray(native[n].inverted()) for n in LEFT])
left_pre=np.einsum('vk,kij,vj->kvi',LW[left_ids],left_inv,V[left_ids],optimize=True)

def left_tree(row):
    mats=np.asarray([np.asarray(row[n]) for n in LEFT]);pts=np.einsum('kij,kvj->vi',mats,left_pre,optimize=True)[:,:3]
    return BVHTree.FromPolygons(pts.tolist(),left_faces,all_triangles=True)

def assembly_tree(stock,kind,magazine):
    parts=[]
    for name in (stock,'native_front' if stock.endswith('_native') else 'front','grip_'+kind,'native_body',magazine):
        p,f=geometry[name];used=sorted({i for face in f for i in face});points=np.asarray([p[i] for i in used])
        parts.append((BVHTree.FromPolygons(p,f,all_triangles=True),points.min(0),points.max(0)))
    return parts

part_distance=signed_distance
def signed_distance(tree,points,exact=False):
    if not isinstance(tree,list):return part_distance(tree,points,exact)
    X=np.asarray(points);result=np.full(len(X),float('inf'))
    for bv,lo,hi in tree:
        bounds_distance=np.linalg.norm(np.maximum(np.maximum(lo-X,X-hi),0),axis=1)
        d=bounds_distance*1000
        candidates=np.where(bounds_distance<.002)[0]
        if len(candidates):
            value=part_distance(bv,X[candidates],exact)
            outside=np.any((X[candidates]<lo-.000001)|(X[candidates]>hi+.000001),axis=1)
            value[outside]=np.abs(value[outside]);d[candidates]=value
        result=np.minimum(result,d)
    return result

def rest_row(row):
    root=rest['WPN_root']@row['WPN_root'].inverted()
    return {n:root@m for n,m in row.items()}

if __name__=='__main__':
    report={}
    for family in ('skeleton_base','skeleton_base_balanced','skeleton_base_phantom','skeleton_base_stable'):
        vals=[]
        for i in range(4,45):
            t=i/60;row,_=compose(entry(family,'quick_melee'),t)
            bv=left_tree(row);pts=skin_points(row,hand_ids[::5],True)
            d=signed_distance(bv,pts)
            if d.min()<-1:vals.append({'time':t,'min_mm':float(d.min()),'inside':int((d<-1).sum())})
        report[family]=vals
    (O/'before_arm_contact.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
