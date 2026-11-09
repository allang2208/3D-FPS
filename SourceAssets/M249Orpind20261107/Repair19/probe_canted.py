"""Fit the existing canted idle index knuckle so reload can return without clipping."""
from pathlib import Path
exec(compile((Path(__file__).parent/'dense_bvh.py').read_text().split('for key,data in cache.items():')[0],__file__,'exec'))
w0=cache['reload_canted']['world'][-1];root=w0[ix['WPN_root']];rr=root[:3,:3]/100;chain=[ix[n] for n in ('index_metacarpal_l','index_01_l','index_02_l','index_03_l')];best=[]
for length in np.arange(.1,1.21,.1):
    found=[]
    for direction in ([1,0,0],[0,1,0],[0,0,-1],[1,0,-1],[0,1,-1],[1,1,0]):
        delta=np.array(direction,dtype=float);delta=delta/np.linalg.norm(delta)*length;w=w0.copy()
        for b in chain:w[b,:3,3]+=rr@delta
        xf=w@ib;p=np.zeros_like(v)
        for b,js,pts in groups:p[js]+=pts@xf[b,:3,:].T
        local=(p-root[:3,3])@rr;hand=BVHTree.FromPolygons(local.tolist(),ff.tolist(),all_triangles=True);count=len(hand.overlap(trees['Receiver']))
        if count==0:found.append(delta)
    if found:best=found;break
if not best:raise RuntimeError('No small knuckle clearance')
delta=best[0];parent=w0[ix['hand_l']];local=np.linalg.inv(parent[:3,:3])@rr@delta
(r/'canted_index_fix.json').write_text(json.dumps(dict(root_delta_cm=delta.tolist(),local_delta=local.tolist(),bone='index_metacarpal_l'),indent=2));print('CANTED_INDEX_CLEARANCE',delta.tolist(),flush=True)
