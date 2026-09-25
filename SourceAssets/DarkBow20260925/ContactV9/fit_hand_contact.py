"""Author a closed Bow hand surface and fit the hook to actual skinned pads.

No game playback or rendering. Geometry and weights remain in the native V7
reference pose. This is a Bow derivative; the shared accepted master is intact.
"""
import json, math
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
P=Path(__file__).parent;ROOT=P.parents[2]
source=ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json'
data=json.loads(source.read_text());inp=json.loads((P/'hand_authoring_input.json').read_text())
rest={n:np.array(m) for n,m in inp['rest'].items()};parent=inp['parent'];order=inp['order']
H=np.array(inp['hand']);R=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
verts=np.array(data['positions']);triangles=np.array(data['triangles'])
local={n:np.linalg.inv(rest[parent[n]])@rest[n] if parent[n] else rest[n] for n in order}
reference=json.loads((P.parent/'GripV5/grasp_native.json').read_text())
grasp={n:np.array(m) for n,m in reference['pose'].items()}
donor_local={n:np.linalg.inv(grasp[parent[n]])@grasp[n] for n in order
    if n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')}
anatomy={d['bone']:d for d in inp['anatomy']['digits']}
digits=('index','middle','ring')

def turn(axis,degrees):
    return Rotation.from_rotvec(np.asarray(axis)/np.linalg.norm(axis)*math.radians(degrees)).as_matrix()
def hand_pose(values):
    world={'hand_r':H.copy()}
    for n in order:
        if parent[n] not in world:continue
        w=world[parent[n]]@local[n]
        if n in donor_local and ('_metacarpal_' in n or n.startswith(('thumb_','pinky_'))):
            w=world[parent[n]]@donor_local[n]
        elif n in anatomy and n.split('_')[0] in digits:
            di=digits.index(n.split('_')[0]);seg=int(n.split('_')[1])-1
            delta=world[parent[n]][:3,:3]@rest[parent[n]][:3,:3].T
            rot=turn(delta@R@anatomy[n]['across'],values[di*4+seg])
            if seg==0:rot=turn(delta@R@anatomy[n]['dorsal'],values[di*4+3])@rot
            w[:3,:3]=rot@w[:3,:3]
        world[n]=w
    return world

def skin(vs,weights,world):
    out=np.zeros((len(vs),3));ps=np.c_[vs@R.T,np.ones(len(vs))]
    for n in world:
        ws=np.array([w.get(n,0.) for w in weights])
        if ws.max()>0:out+=(ps@(world[n]@np.linalg.inv(rest[n])).T)[:,:3]*ws[:,None]
    return out

# Source-surface samples at the distal crease, not wrist-origin placeholders.
pads={}
for digit in digits:
    n=digit+'_03_r';a=anatomy[n]
    point=np.array(a['head'])+np.array(a['axis'])*a['length']*.12-np.array(a['dorsal'])*a['radius']*.82
    allowed=np.array([sum(v for k,v in w.items() if k.startswith(digit+'_') and k.endswith('_r'))>.5 for w in data['weights']])
    dist=np.linalg.norm(verts-point,axis=1);dist[~allowed]=np.inf
    pads[digit]=np.argsort(dist)[:8].tolist()
rays={k:np.array(v) for k,v in inp['string_rays'].items()}
initial=np.array([8,54,28,1.5,4,60,30,0,12,57,30,-1,13.,-4.5,1.3],dtype=float)
lower=np.array([-8,35,15,-10,-8,35,15,-10,-8,35,15,-10,9,-8,.8])
upper=np.array([28,82,58,10,28,82,58,10,28,82,58,10,16,-1,2.2])
def residual(x):
    world=hand_pose(x);anchor=x[12:15];res=[]
    for di,digit in enumerate(digits):
        ids=pads[digit];pad=skin(verts[ids],[data['weights'][i] for i in ids],world).mean(0)
        n=digit+'_03_r'
        normal=-(world[n][:3,:3]@rest[n][:3,:3].T@R@anatomy[n]['dorsal'])
        pad+=normal/np.linalg.norm(normal)*.14 # 0.9 mm string radius plus surface clearance
        ray=rays['upper' if pad[2]>=anchor[2] else 'lower']
        target=anchor+ray*((pad[2]-anchor[2])/ray[2])
        res.extend((pad[:2]-target[:2])*5.)
        # The arrow passes between index and middle, not through a finger.
        gap=pad[2]-anchor[2] if di==0 else anchor[2]-pad[2]
        res.append(max(0.,1.15-gap)*4.)
    res.extend((x[:12]-initial[:12])*.014)
    res.extend((x[12:15]-initial[12:15])*.08)
    return np.array(res)
def string_blocker(world):
    # Constrain the complete string cylinder against the skin, not just three
    # averaged pad points. Keep the smallest outward adjustment of the fit.
    posed=skin(verts,data['weights'],world)
    selected=(np.array(data['triangle_materials'])==2)&(verts[triangles].mean(1)[:,0]>40)
    ts=triangles[selected];a=posed[ts[:,0]];e1=posed[ts[:,1]]-a;e2=posed[ts[:,2]]-a
    def crosses(origin,ray):
        h=np.cross(np.broadcast_to(ray,e2.shape),e2);det=(e1*h).sum(1)
        good=np.abs(det)>1e-9;f=np.divide(1.,det,out=np.zeros_like(det),where=good)
        s=origin-a;u=f*(s*h).sum(1);qc=np.cross(s,e1);v=f*(ray*qc).sum(1);t=f*(e2*qc).sum(1)
        return np.any(good&(u>=0)&(v>=0)&(u+v<=1)&(t>0)&(t<1))
    def blocked(center):
        for ray in rays.values():
            direction=ray/np.linalg.norm(ray);across=np.cross(direction,[1,0,0]);across/=np.linalg.norm(across);other=np.cross(direction,across)
            for angle in np.linspace(0,2*np.pi,8,endpoint=False):
                # String radius .09 cm plus .03 cm authoring clearance.
                offset=.12*(np.cos(angle)*across+np.sin(angle)*other)
                if crosses(center+offset,ray):return True
        return False
    return blocked

def project_string_clearance(x,world):
    blocked=string_blocker(world);start=x[12:15].copy()
    for shift in np.arange(0.,.81,.02):
        center=start+np.array([0.,shift,0.])
        if not blocked(center):x[12:15]=center;return float(shift)
    raise RuntimeError('Hook requires a different contact pose; do not publish penetration')

def close_outer_hooks(x):
    # Middle establishes the supported string surface. Bring index and ring
    # back onto that same string without reintroducing a skin intersection.
    amounts={}
    for digit,di in (('index',0),('ring',2)):
        sl=slice(di*4,di*4+4);base=x.copy()
        def objective(v):
            full=base.copy();full[sl]=v;return residual(full)
        opt=least_squares(objective,base[sl],bounds=(lower[sl],upper[sl]),max_nfev=100)
        target=base.copy();target[sl]=opt.x
        def clear(t):
            current=base+(target-base)*t
            return not string_blocker(hand_pose(current))(current[12:15])
        fraction=1.
        if not clear(1.):
            lo,hi=0.,1.
            for _ in range(8):
                mid=(lo+hi)*.5
                if clear(mid):lo=mid
                else:hi=mid
            fraction=lo
        x[:]=base+(target-base)*fraction;amounts[digit]=fraction
    return amounts

states=[]
for q in (0.,.5,1.):
    rays={k:np.array(v) for k,v in inp['string_rays_by_q'][str(q)].items()}
    fit=least_squares(residual,initial,bounds=(lower,upper),max_nfev=280,
        ftol=1e-9,xtol=1e-9,gtol=1e-9)
    clearance=project_string_clearance(fit.x,hand_pose(fit.x))
    closure=close_outer_hooks(fit.x)
    states.append({'q':q,'hook':{d:fit.x[i*4:i*4+4].tolist() for i,d in enumerate(digits)},
        'contact_in_hand_cm':fit.x[12:15].tolist(),'surface_clearance_shift_cm':clearance,
        'outer_hook_contact_fraction':closure})
    print('HOOK_PHASE_AUTHORED',q,'clearance shift cm',round(clearance,3))
world=hand_pose(fit.x)
result={'hook':{d:fit.x[i*4:i*4+4].tolist() for i,d in enumerate(digits)},
    'contact_in_hand_cm':fit.x[12:15].tolist(),'surface_pad_vertices':pads,
    'donor_locals':{n:m.tolist() for n,m in donor_local.items()
        if '_metacarpal_' in n or n.startswith(('thumb_','pinky_'))},
    'source':'V7 native hand surface; accepted M4 right-hand thumb/pinky/metacarpal support',
    'scope':'Authoring fit only; not a runtime or visual acceptance result','states':states}
for digit in digits:
    ids=pads[digit];result.setdefault('fitted_pads_cm',{})[digit]=skin(verts[ids],[data['weights'][i] for i in ids],world).mean(0).tolist()
(P/'hand_contact.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

# Weld coincident skin vertices in the hand only. UV and normal seams are per
# triangle-corner arrays, so this preserves texture/material boundaries.
mapping={};weld=list(range(len(verts)))
for i,v in enumerate(verts):
    if abs(v[0])>40:
        key=tuple(np.round(v,4));weld[i]=mapping.setdefault(key,i)
data['triangles']=[[weld[int(i)] for i in t] for t in triangles]
edges=defaultdict(list)
for ti,t in enumerate(data['triangles']):
    for a,b in zip(t,t[1:]+t[:1]):
        if a!=b:edges[tuple(sorted((a,b)))].append((ti,a,b))
boundary=[v[0] for v in edges.values() if len(v)==1 and data['triangle_materials'][v[0][0]]==2
    and min(abs(verts[i,0]) for i in v[0][1:])>40]
# Replace the small damaged patches, including surrounding valid facets. Merely
# flipping an inverted triangle leaves overlapping edges and a folded skin seam.
bad={ti for ti,a,b in boundary}
for ti,face in enumerate(data['triangles']):
    if data['triangle_materials'][ti]!=2:continue
    a,b,c=verts[face];normal=np.mean(data['normals'][ti],axis=0)
    if np.dot(np.cross(b-a,c-a),normal)>1e-8:bad.add(ti)
seed_vertices={v for ti in bad for v in data['triangles'][ti]}
patch={ti for ti,face in enumerate(data['triangles']) if data['triangle_materials'][ti]==2 and any(v in seed_vertices for v in face)}
vertex_faces=defaultdict(set)
for ti in patch:
    for v in data['triangles'][ti]:vertex_faces[v].add(ti)
remaining=set(patch);components=[]
while remaining:
    todo=[remaining.pop()];group=set(todo)
    while todo:
        ti=todo.pop()
        for v in data['triangles'][ti]:
            for tj in vertex_faces[v]&remaining:remaining.remove(tj);group.add(tj);todo.append(tj)
    components.append(group)
removed=set();added=[];patch_info=[]
for group in components:
    local_edges=defaultdict(list)
    for ti in group:
        f=data['triangles'][ti]
        for a,b in zip(f,f[1:]+f[:1]):local_edges[tuple(sorted((a,b)))].append((ti,a,b))
    boundary_edges=[v[0] for v in local_edges.values() if len(v)==1]
    adjacent=defaultdict(list)
    for ti,a,b in boundary_edges:adjacent[a].append(b);adjacent[b].append(a)
    if any(len(v)!=2 for v in adjacent.values()):raise RuntimeError('Palm patch boundary branches')
    unseen=set(adjacent);loops=[]
    while unseen:
        start=min(unseen);loop=[];prev=None;cur=start
        while cur in unseen:
            unseen.remove(cur);loop.append(cur)
            nxt=next(n for n in adjacent[cur] if n!=prev);prev,cur=cur,nxt
        loops.append(loop)
    # Keep the outer loop; the tiny interior opening is filled by this patch.
    loop=max(loops,key=lambda v:sum(np.linalg.norm(verts[a]-verts[b]) for a,b in zip(v,v[1:]+v[:1])))
    if np.ptp(verts[loop],axis=0).max()>2.:raise RuntimeError('Palm repair exceeds local defect region')
    center=len(data['positions']);data['positions'].append(verts[loop].mean(0).tolist())
    data['canonical_positions'].append(np.array(data['canonical_positions'])[loop].mean(0).tolist())
    weights=defaultdict(float)
    for vi in loop:
        for n,w in data['weights'][vi].items():weights[n]+=w/len(loop)
    weights={k:v for k,v in sorted(weights.items(),key=lambda p:p[1],reverse=True)[:8]};total=sum(weights.values())
    data['weights'].append({k:v/total for k,v in weights.items()})
    def corner(vi,key):
        rows=[data[key][ti][data['triangles'][ti].index(vi)] for ti in group if vi in data['triangles'][ti]]
        return np.mean(rows,axis=0)
    corner_values={key:{vi:corner(vi,key) for vi in loop} for key in ('uv','normals','canonical_normals')}
    center_values={key:np.mean(list(vals.values()),axis=0) for key,vals in corner_values.items()}
    for a,b in zip(loop,loop[1:]+loop[:1]):
        face=[a,b,center];normal=center_values['normals']
        if np.dot(np.cross(verts[b]-verts[a],np.array(data['positions'][center])-verts[a]),normal)>0:face=[b,a,center]
        added.append({'triangles':face,'triangle_materials':2,**{key:[corner_values[key][vi].tolist() if vi!=center else center_values[key].tolist() for vi in face] for key in corner_values}})
    removed.update(group);patch_info.append({'removed_faces':sorted(group),'boundary':loop,'center_vertex':center,'filled_inner_loops':len(loops)-1})
for key in ('triangles','triangle_materials','uv','normals','canonical_normals'):
    data[key]=[row for i,row in enumerate(data[key]) if i not in removed]+[row[key] for row in added]
data['contract']='Bow-only closed derivative of accepted V7; palm openings capped, corner data retained'
(P/'bow_closed_surface.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(P/'surface_repair.json').write_text(json.dumps({'patches':patch_info,'replaced_faces':len(removed),'new_faces':len(added),
    'source':str(source),'runtime_tested':False},indent=2),encoding='utf-8')
print('HOOK_AUTHORING',json.dumps(result['hook']))
print('ACTUAL_PAD_CONTACT_CM',result['contact_in_hand_cm'],result['fitted_pads_cm'])
print('PALM_REPAIR',len(components),'local patches;',len(removed),'old faces;',len(added),'new faces')
