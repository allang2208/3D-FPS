"""Author M-88's continuous anatomical corpse. No simulation or rendering.

The torso uses a filled tetrahedral field. Each appendage has its own swept
four-corner volume, joined to its actual parent by a local tetrahedral sleeve.
Nearby limbs and coiled tentacle stations never share nodes by proximity.
"""
from pathlib import Path
import itertools, json, re
import numpy as np
from scipy.ndimage import binary_fill_holes, label
from scipy.spatial import cKDTree

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/DeathV32')
SOURCE='/Game/Monsters/BoundCongregate/TentacleReachV29/SK_BoundCongregate_TentacleReachV29'
meta=json.loads((OUT/'surface.bin.skin.json').read_text(encoding='utf8'))
with (OUT/'surface.bin').open('rb') as f:
    count=int(np.fromfile(f,'<i4',1)[0]);raw=np.fromfile(f,'<f4').reshape(count,3)
points,first,inverse=np.unique(raw,axis=0,return_index=True,return_inverse=True)
points=points.astype(float)
names=meta['bones'];parents=meta['parents'];heads=np.array(meta['heads_m'])
skin=np.zeros((len(points),len(names)))
for i,row in enumerate(meta['weights']):
    for b,w in row:skin[inverse[i],b]+=w
skin/=skin.sum(1)[:,None]

def domain(name):
    match=re.match(r'(leg_[LR][1-5])_',name)
    if match:return match[1]
    for prefix in ('attack_tentacle','scent','grasp','curl','feeler'):
        if name.startswith(prefix+'_'):return prefix
    return 'body'

groups={}
for i,n in enumerate(names):groups.setdefault(domain(n),[]).append(i)
regions=list(groups)
mass=np.column_stack([skin[:,groups[r]].sum(1) for r in regions])
chosen=mass.argmax(1)
chosen[mass.max(1)<.6]=regions.index('body')
present=[r for k,r in enumerate(regions) if r!='body' and np.any(chosen==k)]

nodes=[];tets=[];bindings=[];domain_nodes={};domain_tets={}
embed_ids=np.zeros((len(points),4),int);embed_weights=np.zeros((len(points),4))

def add_node(p,weights=()):
    nodes.append(np.asarray(p));bindings.append(list(weights));return len(nodes)-1

def add_tet(ids):
    ids=list(map(int,ids));p=np.array([nodes[i] for i in ids])
    det=np.linalg.det((p[1:]-p[0]).T)
    if abs(det)<1.e-12:return None
    if det<0:ids[1],ids[2]=ids[2],ids[1]
    tets.append(ids);return len(tets)-1

def prism(a,b):
    # Consistent diagonal on every station; neighbouring cells share faces.
    vertices=list(a)+list(b);result=[]
    for axes in itertools.permutations((0,1,2)):
        corner=0;ids=[vertices[0]]
        for axis in axes:corner+=1<<axis;ids.append(vertices[corner])
        index=add_tet(ids)
        if index is not None:result.append(index)
    return result

def station_plan(region):
    bones=groups[region]
    # Native export gives parent-first order, including the 57 whip stations.
    centres=heads[bones].copy()
    if len(centres)<2:raise RuntimeError('Expected a chain: '+region)
    direction=centres[-1]-centres[-2];direction/=max(np.linalg.norm(direction),1.e-8)
    cloud=points[chosen==regions.index(region)]
    extension=max(.025,float(np.max((cloud-centres[-1])@direction)))
    centres=np.vstack([centres,centres[-1]+direction*extension])
    # The first skin segment includes flesh proximal to the joint. Its field
    # must start behind that tissue, not at the bone head's clipping plane.
    if region!='attack_tentacle':
        first_axis=centres[1]-centres[0];first_axis/=np.linalg.norm(first_axis)
        proximal=float(np.min((cloud-centres[0])@first_axis))
        centres[0]+=first_axis*min(0.,proximal-.012)
    weights=[[(int(b),1.)] for b in bones]+[[(int(bones[-1]),1.)]]
    indices=list(map(float,range(len(bones))))+[float(len(bones))]
    return centres,weights,np.array(indices)

plans={r:station_plan(r) for r in present}
tube_count=sum(len(p[0])*4 for p in plans.values())
body_budget=700-tube_count
if body_budget<100:raise RuntimeError('Anatomical stations exceed the corpse budget')

# Filled torso field, with identical positions receiving identical embeddings.
body_rows=np.flatnonzero(chosen==regions.index('body'));cloud=points[body_rows]
spacing=max(float(np.ptp(cloud,axis=0).max())/12.,.025)
offsets=np.array(list(itertools.product((0,1),repeat=3)),int)
while True:
    origin=np.floor(cloud.min(0)/spacing)*spacing-spacing*.05
    q=(cloud-origin)/spacing;cells=np.floor(q).astype(int)
    occupied=np.zeros(tuple(cells.max(0)+1),bool);occupied[tuple(cells.T)]=True
    occupied=binary_fill_holes(occupied)
    # Join only body/garment islands, never a limb or a tentacle station.
    labels,number=label(occupied)
    sizes=np.bincount(labels.ravel());sizes[0]=0
    joined=np.argwhere(labels==sizes.argmax())
    for k in np.argsort(-sizes):
        if k==0 or k==sizes.argmax():continue
        island=np.argwhere(labels==k)
        distances,nearest=cKDTree(joined).query(island);j=distances.argmin()
        a,b=island[j],joined[nearest[j]]
        bridge=np.rint(np.linspace(a,b,int(np.abs(a-b).max())+1)).astype(int)
        occupied[tuple(bridge.T)]=True;joined=np.concatenate([joined,island,bridge])
    full=np.argwhere(occupied);grid=np.unique((full[:,None,:]+offsets).reshape(-1,3),axis=0)
    if len(grid)<=body_budget:break
    spacing*=1.06
lookup={tuple(v):add_node(origin+v*spacing) for v in grid}
domain_nodes['body']=list(range(len(nodes)));domain_tets['body']=[]
for cell in full:
    for axes in itertools.permutations(range(3)):
        corner=np.zeros(3,int);ids=[lookup[tuple(cell)]]
        for axis in axes:
            corner=corner.copy();corner[axis]+=1;ids.append(lookup[tuple(cell+corner)])
        domain_tets['body'].append(add_tet(ids))
fraction=q-cells;axes=np.argsort(-fraction,axis=1,kind='stable');f=np.take_along_axis(fraction,axes,axis=1)
embed_weights[body_rows]=np.column_stack([1-f[:,0],f[:,0]-f[:,1],f[:,1]-f[:,2],f[:,2]])
for j,(cell,axis) in enumerate(zip(cells,axes)):
    corner=np.zeros(3,int);ids=[lookup[tuple(cell)]]
    for a in axis:corner=corner.copy();corner[a]+=1;ids.append(lookup[tuple(cell+corner)])
    embed_ids[body_rows[j]]=ids

roots={};region_reports=[]
for region in present:
    start=len(nodes);centres,weights,station_indices=plans[region]
    rows=np.flatnonzero(chosen==regions.index(region));p=points[rows];bones=groups[region]
    sw=skin[rows][:,bones];expected=(sw@np.arange(len(bones)))/sw.sum(1)
    # Locate along the actual chain rather than whichever coil is closest.
    delta=np.diff(centres,axis=0);length2=np.einsum('ij,ij->i',delta,delta)
    differences=p[:,None,:]-centres[None,:-1,:]
    t=np.clip(np.einsum('vsi,si->vs',differences,delta)/length2,0,1)
    closest=centres[None,:-1,:]+t[:,:,None]*delta
    distance=np.linalg.norm(p[:,None,:]-closest,axis=2)
    allowed=np.abs(expected[:,None]-(station_indices[:-1]+station_indices[1:])[None,:]*.5)<=2.5
    best=np.argmin(np.where(allowed,distance,np.inf),axis=1)
    tangent=np.gradient(centres,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    rings=[];last=None
    for i,c in enumerate(centres):
        if last is None:
            seed=np.array([0.,0.,1.]) if abs(tangent[i,2])<.95 else np.array([0.,1.,0.])
            a=seed-tangent[i]*np.dot(seed,tangent[i])
        else:a=last-tangent[i]*np.dot(last,tangent[i])
        if np.linalg.norm(a)<1.e-7:a=np.cross(tangent[i],np.eye(3)[np.argmin(np.abs(tangent[i]))])
        a/=np.linalg.norm(a);b=np.cross(tangent[i],a);last=a
        local=p[np.abs(best-i)<=1]-c
        if not len(local):local=p[np.argmin(np.linalg.norm(p-c,axis=1))][None,:]-c
        uv=np.column_stack([local@a,local@b])
        lo=np.minimum(uv.min(0)-.012,-.012);hi=np.maximum(uv.max(0)+.012,.012)
        rings.append([add_node(c+x*a+y*b,weights[i]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])])
    segment_tets=[prism(a,b) for a,b in zip(rings,rings[1:])]
    domain_nodes[region]=list(range(start,len(nodes)));domain_tets[region]=sum(segment_tets,[])
    roots[region]=rings[0]
    # Positive four-node interpolation inside the local swept volume.
    for fitting_step in range(9):
        best_score=np.full(len(p),np.inf)
        for shift in (-2,-1,0,1,2):
            segments=np.clip(best+shift,0,len(segment_tets)-1)
            for which in range(6):
                candidates=np.array([segment_tets[s][min(which,len(segment_tets[s])-1)] for s in segments])
                ids=np.array(tets)[candidates];corners=np.array(nodes)[ids]
                matrix=np.transpose(corners[:,1:]-corners[:,:1],(0,2,1))
                tail=np.linalg.solve(matrix,(p-corners[:,0])[...,None])[...,0]
                bary=np.column_stack([1-tail.sum(1),tail]);positive=np.maximum(bary,0);positive/=positive.sum(1)[:,None]
                residual=np.linalg.norm(np.einsum('vi,vij->vj',positive,corners)-p,axis=1)
                score=residual+np.maximum(-bary,0).sum(1)*.001
                use=score<best_score;best_score[use]=score[use]
                embed_ids[rows[use]]=ids[use];embed_weights[rows[use]]=positive[use]
        outside=best_score>.0001
        if not outside.any() or fitting_step==8:break
        # Fit only the support rings of uncovered tissue. No new particles or
        # links across other limbs; this is source-cage construction, not a sim.
        affected=set()
        for segment in np.unique(best[outside]):affected.update((int(segment),int(segment)+1))
        for i in affected:
            for node in rings[i]:nodes[node]=centres[i]+(nodes[node]-centres[i])*1.08
    if best_score.max()>.0001:raise RuntimeError('Uncovered anatomical surface: '+region)
    region_reports.append(dict(region=region,stations=len(rings),nodes=len(nodes)-start,vertices=len(rows),
        fitting_steps=fitting_step,max_embedding_residual_m=float(best_score.max()),
        embedding_residual_p99_m=float(np.quantile(best_score,.99))))

# Join each branch only to its anatomical parent, through a short volume.
join_reports=[]
for region in present:
    parent=parents[groups[region][0]];parent_region=domain(names[parent]) if parent>=0 else 'body'
    if parent_region not in domain_tets:parent_region='body'
    head=plans[region][0][0];candidate=np.array(domain_tets[parent_region],int)
    corners=np.array(nodes)[np.array(tets)[candidate]]
    chosen_tet=candidate[np.linalg.norm(corners.mean(1)-head,axis=1).argmin()]
    ids=tets[chosen_tet]
    # Pick a ring correspondence with the shortest local sleeve.
    root=roots[region]
    ordered=min(itertools.permutations(ids),key=lambda f:sum(np.linalg.norm(nodes[a]-nodes[b]) for a,b in zip(f,root)))
    added=prism(ordered,root)
    if not added:raise RuntimeError('Degenerate parent join '+region)
    join_reports.append(dict(region=region,parent=parent_region,max_join_m=float(max(np.linalg.norm(nodes[a]-nodes[b]) for a in ordered for b in root))))

for tet in tets:
    p=np.array(nodes)[tet]
    if np.linalg.det((p[1:]-p[0]).T)<0:tet[1],tet[2]=tet[2],tet[1]
records=np.column_stack([points,embed_ids,embed_weights,np.full(len(points),-1),np.zeros(len(points))]).astype('<f4')
with (OUT/'embedding.bin').open('wb') as f:np.array(records.shape,dtype='<i4').tofile(f);records.tofile(f)
cage=dict(coordinates='mesh_m',spacing_m=.10,nodes=np.array(nodes).tolist(),soft_node_count=len(nodes),
    tetrahedra=tets,hardware=[],node_source_weights=bindings,source=SOURCE,
    embedding='continuous anatomical torso and swept appendages, positive local weights')
(OUT/'cage.json').write_text(json.dumps(cage,separators=(',',':'))+'\n',encoding='utf8')
report=dict(complete=True,source=SOURCE,nodes=len(nodes),tetrahedra=len(tets),body_nodes=len(domain_nodes['body']),
    body_spacing_cm=spacing*100,source_vertices=count,surface_rows=len(points),regions=region_reports,joins=join_reports,
    scheme='M14 V19 continuous XPBD; anatomical M88 V32 cage; 120 Hz shared solver',tested=False,rendered=False)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('BOUND_DEATH_V32_AUTHORED '+json.dumps(dict(nodes=len(nodes),tetrahedra=len(tets),regions=len(present))),flush=True)
