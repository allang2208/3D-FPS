"""Fit a dedicated eight-limb rig and author region-isolated surface weights."""
from pathlib import Path
import json
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parent
data=np.load(ROOT/'source_geometry.npz');v=data['unique'];edges=data['edges'];n=len(v)
bones=[]
def bone(name,head,tail,parent=None,region='body',deform=True):
    bones.append(dict(name=name,head=list(head),tail=list(tail),parent=parent,region=region,deform=deform))
bone('root',(0,0,0),(0,0,.16),deform=False)
bone('body_center',(0,0,.43),(.35,0,.43),'root')
bone('body_front',(.75,0,.46),(1.25,0,.43),'body_center')
bone('body_rear',(-.75,0,.43),(-1.35,0,.38),'body_center')
bone('rump',(-1.42,0,.36),(-1.88,0,.33),'body_rear')
bone('head',(1.38,0,.39),(1.94,0,.4),'body_front')
bone('jaw',(1.60,0,.225),(1.95,0,.145),'head','mouth')
bone('mouth_socket',(1.99,0,.28),(2.12,0,.28),'head','socket',False)
# Body mantle lobes get independent, restrained deformation; hardware follows
# the parent lobe/body, not nearby feet or the lower jaw.
for x,parent in [(1.08,'body_front'),(0.,'body_center'),(-1.02,'body_rear')]:
    for side,sgn in [('L',-1),('R',1)]:
        bone(f'mantle_{parent[5:]}_{side}',(x,sgn*.62,.72),(x,sgn*1.05,.62),parent,'mantle')

legs=[]
# Fitted from this GLB's horizontal slices and eight isolated foot pads.
rows=[[(1.39,.77,.49),(1.52,.91,.315),(1.65,.935,.145),(1.80,.94,.052)],
      [(.39,1.045,.53),(.40,1.29,.325),(.40,1.435,.14),(.40,1.565,.05)],
      [(-.60,1.04,.54),(-.61,1.29,.33),(-.61,1.535,.14),(-.61,1.71,.05)],
      [(-1.37,.83,.47),(-1.48,1.09,.30),(-1.51,1.31,.14),(-1.53,1.49,.05)]]
for side,sgn in [('L',-1),('R',1)]:
    for i,row in enumerate(rows):
        points=np.array(row)*[1,sgn,1];reg=f'leg_{i+1:02}_{side}'
        parent=['body_front','body_center','body_rear','rump'][i]
        names=[f'{reg}_upper',f'{reg}_lower',f'{reg}_foot']
        for j in range(3):bone(names[j],points[j],points[j+1],parent if j==0 else names[j-1],reg)
        # Two toe fan sectors retain the actual connected Meshy toe pads and
        # allow contact flexion without pretending the toes were retopologized.
        forward=points[3]-points[2];forward[2]=0;forward/=np.linalg.norm(forward)
        lateral=np.cross([0,0,1],forward)
        for label,offset in [('inner',-.09),('outer',.09)]:
            h=points[2]+forward*.07+lateral*offset;h[2]=.075
            t=h+forward*.14;t[2]=.04
            bone(f'{reg}_toes_{label}',h,t,names[2],reg)
        legs.append(dict(region=reg,points=points.tolist(),bones=names,parent=parent,side=side,pair=i+1))

deforms=[b for b in bones if b['deform']]; names=[b['name'] for b in deforms];idx={s:i for i,s in enumerate(names)}
w=np.zeros((n,len(names)),dtype=np.float32)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
centers=np.array([-1.60,-.75,0,.80,1.64]);body_names=['rump','body_rear','body_center','body_front','head']
body=np.exp(-((v[:,0,None]-centers[None,:])/.46)**2);body/=body.sum(axis=1,keepdims=True)
for j,name in enumerate(body_names):w[:,idx[name]]=body[:,j]

# Surface-distance partition uses welded geometric positions, not UV islands.
# It keeps neighboring feet independent even where Euclidean envelopes overlap.
cost=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
graph=coo_matrix((np.r_[cost,cost],(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(n,n)).tocsr()
distances=[]
for leg in legs:
    foot=np.array(leg['points'][3]);seed=int(np.argmin(np.linalg.norm(v-foot,axis=1)))
    distances.append(dijkstra(graph,directed=False,indices=seed,limit=2.))
    print('SURFACE_PARTITION',leg['region'],flush=True)
dist=np.array(distances);closest=dist.argmin(axis=0)
for k,leg in enumerate(legs):
    pts=np.array(leg['points']); sign=1 if leg['side']=='R' else -1
    root=pts[0];pad=pts[3]
    side_gate=smooth(abs(root[1])-.18,abs(root[1])+.06,abs(v[:,1]))
    longitudinal=np.exp(-((v[:,0]-np.interp(v[:,2],[0,root[2]],[pad[0],root[0]]))/.29)**6)
    leg_amount=side_gate*(1-smooth(root[2]-.15,root[2]+.10,v[:,2]))*longitudinal
    leg_amount*=((closest==k)&(v[:,1]*sign>0)).astype(float)
    # Lock the independently connected low toe pads to their own chain.
    leg_amount=np.maximum(leg_amount,((closest==k)&(dist[k]<.25)&(v[:,2]<.12)).astype(float))
    weights=np.zeros((n,5),dtype=np.float64)
    for j in range(3):
        a,b=pts[j],pts[j+1]; ab=b-a;t=np.clip(((v-a)@ab)/(ab@ab),0,1)
        d=np.linalg.norm(v-(a+t[:,None]*ab),axis=1)
        weights[:,j]=np.exp(-(d/.19)**2)
    toe_amount=(1-smooth(.075,.14,v[:,2]))*smooth(0,.13,(v-pts[2])@((pts[3]-pts[2])/np.linalg.norm(pts[3]-pts[2])))
    forward=pts[3]-pts[2];forward[2]=0;forward/=np.linalg.norm(forward);lat=np.cross([0,0,1],forward)
    fan=smooth(-.075,.075,(v-pts[2])@lat)
    weights[:,:3]/=np.maximum(weights[:,:3].sum(axis=1,keepdims=True),1e-20)
    weights[:,:3]*=(1-toe_amount[:,None]);weights[:,3]=toe_amount*(1-fan);weights[:,4]=toe_amount*fan
    w*=(1-leg_amount[:,None])
    for j,name in enumerate(leg['bones']+[leg['region']+'_toes_inner',leg['region']+'_toes_outer']):w[:,idx[name]]+=weights[:,j]*leg_amount

# Lower jaw, lower teeth and jaw plate rotate together around a hinge. A smooth
# side-lip transition stays on the same continuous original face.
mouth_width=.57
jaw=smooth(1.61,1.78,v[:,0])*(1-smooth(.23,.32,v[:,2]))*(1-smooth(mouth_width,mouth_width+.13,abs(v[:,1])))
w*=(1-jaw[:,None]);w[:,idx['jaw']]+=jaw
for b in deforms:
    if b['region']!='mantle':continue
    h=np.array(b['head']);sgn=np.sign(h[1]);amount=.5*smooth(.45,.72,v[:,2])*smooth(.42,.84,abs(v[:,1]))*np.exp(-((v[:,0]-h[0])/.65)**4)*(v[:,1]*sgn>0)
    w*=(1-amount[:,None]);w[:,idx[b['name']]]+=amount

# Smooth only along surface edges, maintaining limb and jaw region ownership.
source=w.copy(); a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]]
ew=1/np.maximum(np.r_[cost,cost],.0015);degree=np.bincount(a,weights=ew,minlength=n)
allowed=source>1e-5
for iteration in range(4):
    for j in range(len(names)):
        neighbor=np.bincount(a,weights=w[b,j]*ew,minlength=n)/np.maximum(degree,1e-12)
        w[:,j]=(.72*w[:,j]+.28*neighbor)*allowed[:,j]
    w/=np.maximum(w.sum(axis=1,keepdims=True),1e-12)
order=np.argsort(w,axis=1)[:,-4:];values=np.take_along_axis(w,order,axis=1);values/=values.sum(axis=1,keepdims=True)
np.savez_compressed(ROOT/'authored_weights.npz',vertices=v,bone_indices=order.astype(np.int16),weights=values.astype(np.float32),bone_names=np.array(names))
definition={'identity':'M-10 / 沉匣','source':'M10_Meshy_original.glb','units':'meters','forward_axis':'+X','up_axis':'+Z','length_m':4.2,'preserve_source_proportions':True,'source_height_m':float(v[:,2].max()),'bones':bones,'legs':legs,'max_influences':4,'toe_contract':'Two flexion fan sectors per foot. Original connected toe geometry retained; no claim of separate digit topology.','weight_method':'Welded-surface geodesic limb isolation, joint-segment envelopes, jaw hinge mask, mantle gates, constrained surface smoothing, normalized top four influences.','runtime_tested':False}
(ROOT/'rig_definition.json').write_text(json.dumps(definition,ensure_ascii=False,indent=2),encoding='utf-8')
print('M10_WEIGHTS_AUTHORED',len(bones),'bones',len(v),'geometric vertices',flush=True)
