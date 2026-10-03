"""Offline native skin data and solid queries for the authored cocking hand."""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent
SA=O.parent/'RSH12SingleAction20261003'

def context(family='single'):
    scope={'__file__':str(SA/'author_single_action.py'),'__name__':'cock_fit_setup'}
    sys.argv=['cock_fit','--',family]
    exec((SA/'author_single_action.py').read_text().split('for kind in jobs:')[0],scope)
    rig=scope['r'];profile=scope['PROFILE'];data=scope['D']
    entry=next(c for c in profile['clips'] if c['kind']=='idle')
    base=scope['native_pose'](scope['apply_profile']({n:scope['matrix'](v) for n,v in data['clips']['idle']['samples'][0]['local'].items()},entry))
    canonical=(base['WPN_root']@scope['alignment']).inverted()
    p={n:canonical@m for n,m in base.items()}
    side=scope['side'];rest=scope['rest'];ob=next(o for o in bpy.data.objects if o.type=='MESH')
    groups={g.index:g.name for g in ob.vertex_groups};samples=[]
    for v in ob.data.vertices:
        weights=[(groups[g.group],g.weight) for g in v.groups if groups[g.group] in rest and g.weight>.001]
        label=max(weights,key=lambda a:a[1])[0] if weights else ''
        # Palm and metacarpal skin often shares several sub-0.5 weights.
        # Include its dominant label rather than requiring one rigid influence.
        if label.endswith('_'+side) and label.startswith(('hand','thumb','index','middle','ring','pinky')):samples.append((rig.matrix_world.inverted()@ob.matrix_world@v.co,weights))
    used=list({n for _,weights in samples for n,w in weights})
    bind={n:np.array(rest[n].inverted()) for n in used}
    coords=np.array([[*pt,1.] for pt,weights in samples]);weights=np.array([[dict(ww).get(n,0.) for n in used] for pt,ww in samples]);weights/=weights.sum(axis=1)[:,None]
    labels=[max(ww,key=lambda nw:nw[1])[0] for pt,ww in samples]
    raw=json.loads((scope['B']/'canonical_parts.json').read_text());solids={}
    for part in raw:
        if part['name'] not in ('9_l','7_l','11_l'):continue
        vv=[Vector(v) for v in part['verts']];solids[part['name']]=solid(vv,part['faces'])
    hammer=next(part for part in raw if part['name']=='8_l')
    hammer_local=[scope['hammer_geometry_bind'].inverted()@scope['root_rest']@scope['alignment']@Vector(v) for v in hammer['verts']]
    return dict(scope=scope,base=p,side=side,used=used,bind=bind,coords=coords,weights=weights,labels=labels,solids=solids,hammer_local=hammer_local,hammer_faces=hammer['faces'])

def solid(vv,faces):
    lo=Vector(tuple(min(v[a] for v in vv) for a in range(3)));hi=Vector(tuple(max(v[a] for v in vv) for a in range(3)))
    return BVHTree.FromPolygons(vv,faces),lo,hi

direction=Vector((.371,.691,.591)).normalized()
def inside_depth(pt,entry):
    tree,lo,hi=entry
    if any(pt[a]<lo[a] or pt[a]>hi[a] for a in range(3)):return 0.
    origin=pt+direction*1e-7;count=0
    for _ in range(20):
        hit,_,_,_=tree.ray_cast(origin,direction,.5)
        if hit is None:break
        count+=1;origin=hit+direction*1e-6
    return tree.find_nearest(pt)[3]*1000 if count%2 else 0.

def skin(c,p):
    matrices=np.stack([np.array(p[n])@c['bind'][n] for n in c['used']])
    return np.einsum('pbij,pj,pb->pi',np.broadcast_to(matrices,(len(c['coords']),*matrices.shape)),c['coords'],c['weights'],optimize=True)[:,:3]

if __name__=='__main__':
    c=context();p=c['base']
    for n in ('hand_r','thumb_01_r','thumb_02_r','thumb_03_r','index_metacarpal_r','index_01_r','index_03_r','middle_01_r','middle_03_r','ring_03_r','pinky_03_r','WPN_Hammer'):
        print('CANONICAL_BONE',n,list(p[n].translation),flush=True)
    print('CANONICAL_SPUR',list(p['WPN_Hammer']@c['scope']['spur_local']),flush=True)
