"""Author semantic texture displacement and joint weights on welded source geometry."""
from pathlib import Path
import json,copy
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import maximum_flow, breadth_first_order
from scipy.ndimage import gaussian_filter,maximum_filter,distance_transform_edt
from PIL import Image
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1'
ROOT.mkdir(exist_ok=True)
d=np.load(BASE/'source_geometry.npz');v=d['unique'];edges=d['edges'];inv=d['inverse'];uv=d['uv'];n=len(v)
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf-8'));cfg=copy.deepcopy(cfg)
old=np.load(BASE/'authored_weights.npz');names=list(old['bone_names']);idx={s:i for i,s in enumerate(names)}
oldw=np.zeros((n,len(names)),np.float32);np.put_along_axis(oldw,old['bone_indices'],old['weights'],axis=1)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]]
cost=np.linalg.norm(v[a]-v[b],axis=1);ew=1/np.maximum(cost,.002)
degree=np.bincount(a,weights=ew,minlength=n)
graph=coo_matrix((ew/np.maximum(degree[a],1e-12),(a,b)),shape=(n,n)).tocsr()

# Source color is an anatomical cue, not a direct grayscale height function.
rgb=np.asarray(Image.open(BASE/'BaseColor.png').convert('RGB'),np.float32)/255
sample=rgb[np.clip((uv[:,1]*rgb.shape[0]).astype(int),0,rgb.shape[0]-1),np.clip((uv[:,0]*rgb.shape[1]).astype(int),0,rgb.shape[1]-1)]
counts=np.bincount(inv,minlength=n);color=np.stack([np.bincount(inv,weights=sample[:,j],minlength=n)/counts for j in range(3)],axis=1)
lum=color@np.array([.2126,.7152,.0722]);light=lum.copy()
for _ in range(3):light=.6*light+.4*(graph@light)
x,y,z=v.T
face=smooth(1.51,1.77,x)*smooth(.195,.230,z)*(1-smooth(.62,.77,z))*(1-smooth(.57,.72,abs(y)))
eyes=json.loads((ROOT.parent/'CombatV3/eye_regions.json').read_text(encoding='utf-8'))['eyes']
height=np.zeros(n);eye_area=np.zeros(n)
for eye in eyes:
    ex,ey,ez=eye['blender_center_m'];_,ry,rz=np.array(eye['radii_cm'])/100
    r=np.sqrt(((y-ey)/(ry*1.24))**2+((z-ez)/(rz*1.24))**2)
    gate=smooth(ex-.10,ex-.02,x)
    # Raised eyeball dome, recessed socket crease, outer fleshy eyelid rim.
    h=.024*np.exp(-(r/.78)**2)-.010*np.exp(-((r-1.15)/.20)**2)+.009*np.exp(-((r-1.57)/.26)**2)
    h*=gate*(1-smooth(1.9,2.25,r));height+=h;eye_area=np.maximum(eye_area,(1-smooth(1.6,2.2,r))*gate)
r=np.sqrt((y/.39)**2+((z-.323)/.139)**2)
cavity=(1-smooth(.80,1.04,r))*face
teeth=smooth(.40,.68,light)*cavity
# Follow the connected gum surface to each tooth root. A world-height cut can
# split long upper/lower teeth and stretch their tips when the jaw opens.
mouth_domain=(x>1.60)&(abs(y)<.49)&(z>.14)&(z<.51)
mouth_edges=edges[mouth_domain[edges].all(axis=1)]
edge_len=np.linalg.norm(v[mouth_edges[:,0]]-v[mouth_edges[:,1]],axis=1)
upper_root=mouth_domain&(x>1.72)&(z>.425-.105*(np.minimum(abs(y),.38)/.38)**2)
lower_root=mouth_domain&(x>1.72)&(z<.220+.082*(np.minimum(abs(y),.38)/.38)**2)
# A surface cut avoids the bright enamel and runs through dark mouth recesses.
# Distances alone can still put a transition through the tip of a long tooth.
selected=np.flatnonzero(mouth_domain);lookup=np.full(n,-1);lookup[selected]=np.arange(len(selected))
local=lookup[mouth_edges];count=len(selected);source=count;sink=count+1
brightness=np.minimum(light[mouth_edges[:,0]],light[mouth_edges[:,1]])
capacity=np.maximum(1,np.round(100*(.001+brightness**6*30)/np.maximum(edge_len,.001))).astype(np.int64)
us=lookup[np.flatnonzero(upper_root)];ls=lookup[np.flatnonzero(lower_root)]
rows=np.r_[local[:,0],local[:,1],np.full(len(us),source),ls]
cols=np.r_[local[:,1],local[:,0],us,np.full(len(ls),sink)]
caps=np.r_[capacity,capacity,np.full(len(us)+len(ls),100000000,np.int64)]
network=coo_matrix((caps,(rows,cols)),shape=(count+2,count+2)).tocsr()
flow=maximum_flow(network,source,sink);residual=network-flow.flow;residual.data=(residual.data>0).astype(np.int64);residual.eliminate_zeros()
upper_side=breadth_first_order(residual,source,directed=True,return_predecessors=False)
tooth_jaw=np.ones(n);tooth_jaw[selected[upper_side[upper_side<count]]]=0
tooth_strength=smooth(1.61,1.70,x)*(1-smooth(.33,.44,abs(y)))*(1-smooth(.97,1.15,r))*mouth_domain
dark=(1-smooth(.20,.40,light))*cavity
lip=np.exp(-((r-1.07)/.14)**2)*face
height+=(.016*teeth-.048*dark+.014*lip)*(1-eye_area)
# Low amplitude folds follow texture, with UV seams welded before smoothing.
height+=np.clip(lum-light,-.15,.15)*.012*face*(1-eye_area)
for _ in range(4):height=.7*height+.3*(graph@height)
height*=face

# Store the scalar height in the original UV atlas, then sample that actual map
# back onto vertices. 0.5 = no displacement; full signed range +/- 6 cm.
size=rgb.shape[0];atlas=np.full((size,size),np.nan,np.float32)
faces=d['faces'];active=faces[(np.abs(height[inv[faces]]).max(axis=1)>1e-5)]
hu=height[inv]
for tri in active:
    q=uv[tri]*size-.5;lo=np.maximum(np.floor(q.min(0)).astype(int),0);hi=np.minimum(np.ceil(q.max(0)).astype(int),size-1)
    if np.any(hi<lo):continue
    gx,gy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
    a0,b0,c0=q;den=(b0[1]-c0[1])*(a0[0]-c0[0])+(c0[0]-b0[0])*(a0[1]-c0[1])
    if abs(den)<1e-9:continue
    w0=((b0[1]-c0[1])*(gx-c0[0])+(c0[0]-b0[0])*(gy-c0[1]))/den
    w1=((c0[1]-a0[1])*(gx-c0[0])+(a0[0]-c0[0])*(gy-c0[1]))/den;w2=1-w0-w1
    mask=(w0>=-.005)&(w1>=-.005)&(w2>=-.005)
    block=atlas[lo[1]:hi[1]+1,lo[0]:hi[0]+1];value=w0*hu[tri[0]]+w1*hu[tri[1]]+w2*hu[tri[2]];block[mask]=value[mask]
valid=np.isfinite(atlas);distance,nearest=distance_transform_edt(~valid,return_indices=True)
atlas[~valid]=0;pad=(~valid)&(distance<=3);atlas[pad]=atlas[tuple(nearest[:,pad])]
height16=np.round(np.clip(.5+atlas/.12,0,1)*65535).astype(np.uint16)
Image.fromarray(height16).save(ROOT/'M10_FaceHeight16.png')
sampled=(height16[np.clip((uv[:,1]*size).astype(int),0,size-1),np.clip((uv[:,0]*size).astype(int),0,size-1)].astype(float)/65535-.5)*.12
sampled=np.bincount(inv,weights=sampled,minlength=n)/counts
# Keep only the authored face patch and remove sub-pixel UV quantization spikes.
sampled*=face
for _ in range(2):sampled=.7*sampled+.3*(graph@sampled)
displacement=np.zeros_like(v);displacement[:,0]=sampled

# Corrective shapes live on this same connected mesh, in pre-skin space.
corner=np.exp(-((abs(y)-.39)/.095)**2-((z-.31)/.13)**2)*face*(1-eye_area)
upper=lip*smooth(.33,.46,z)*(1-eye_area)
lower=lip*(1-smooth(.23,.31,z))
open_delta=np.zeros_like(v);wide_delta=np.zeros_like(v)
open_delta[:,0]=.018*lower-.008*corner
open_delta[:,1]=np.sign(y)*.015*corner
open_delta[:,2]=.010*upper-.008*corner
wide_delta[:,0]=.012*upper+.012*lower
wide_delta[:,1]=np.sign(y)*.020*corner
wide_delta[:,2]=.016*upper-.008*corner
open_delta*=1-tooth_strength[:,None];wide_delta*=1-tooth_strength[:,None]

# Give each knee a real bend plane while preserving all contact/root positions.
by_name={spec['name']:spec for spec in cfg['bones']};diagnosis=[]
for leg in cfg['legs']:
    pts=np.array(leg['points']);before=np.linalg.norm(pts[2]-pts[0])/np.linalg.norm(np.diff(pts[:3],axis=0),axis=1).sum()
    pts[1]+=np.array([.09 if leg['pair']<3 else -.09,0,.035])
    after=np.linalg.norm(pts[2]-pts[0])/np.linalg.norm(np.diff(pts[:3],axis=0),axis=1).sum()
    leg['points']=pts.tolist();upper,lower_b,foot=leg['bones']
    by_name[upper]['tail']=pts[1].tolist();by_name[lower_b]['head']=pts[1].tolist()
    helper=leg['region']+'_socket';names.append(helper)
    cfg['bones'].append(dict(name=helper,head=pts[0].tolist(),tail=pts[1].tolist(),parent=leg['parent'],region='socket_tissue',deform=True))
    diagnosis.append(dict(leg=leg['region'],straightness_before=before,straightness_after=after))
idx={s:i for i,s in enumerate(names)};w=np.pad(oldw,((0,0),(0,8)))
for leg in cfg['legs']:
    pts=np.array(leg['points']);chain=leg['bones']+[leg['region']+'_toes_inner',leg['region']+'_toes_outer'];indices=[idx[s] for s in chain]
    amount=oldw[:,indices].sum(axis=1)
    for _ in range(10):amount=.65*amount+.35*(graph@amount)
    chosen=np.flatnonzero(amount>1e-5);p=v[chosen];pts0=pts[:-1];delta=pts[1:]-pts0
    seg_t=np.clip(((p[:,None,:]-pts0)*delta).sum(axis=2)/(delta*delta).sum(axis=1),0,1)
    dist=np.linalg.norm(p[:,None,:]-(pts0+seg_t[:,:,None]*delta),axis=2);seg=dist.argmin(axis=1)
    s=seg+seg_t[np.arange(len(seg)),seg]
    down=smooth(.72,1.28,s);ankle=smooth(1.72,2.25,s)
    local=np.stack([1-down,down*(1-ankle),down*ankle],axis=1)
    toe_sum=oldw[chosen][:,indices[3:]].sum(axis=1);toe_fraction=np.clip(toe_sum/np.maximum(amount[chosen],1e-8),0,1)
    local*=1-toe_fraction[:,None]
    socket_fraction=.67*np.exp(-((s+.05)/.60)**2)
    socket_weight=local[:,0]*socket_fraction;local[:,0]*=1-socket_fraction
    # Remove only this chain; retain adjacent body, face, mantle and toe ownership.
    w[:,indices[:3]]=0;w[chosen[:,None],np.array(indices[:3])]=local*amount[chosen,None]
    w[chosen,idx[leg['region']+'_socket']]=socket_weight*amount[chosen]
    # Toe fraction was retained as the original connected pads.
    remaining=np.maximum(0,1-w.sum(axis=1));w[:,idx[leg['parent']]]+=remaining

# Redistribute jaw transition across the lower lip and corners, not a sharp Z cut.
jaw_gate=smooth(1.58,1.80,x)*(1-smooth(.48,.64,abs(y)))
jaw_amount=(1-smooth(.22,.385,z))*jaw_gate
mouth_patch=face*(1-smooth(.45,.53,z))*(1-eye_area)
jaw_target=oldw[:,idx['jaw']]*(1-mouth_patch)+jaw_amount*mouth_patch
jaw_target=np.clip(jaw_target*(1-tooth_strength)+tooth_jaw*tooth_strength,0,1)
nonjaw=1-w[:,idx['jaw']];w[:,idx['jaw']]=0
empty=nonjaw<1e-8;w[empty,idx['head']]=1;nonjaw[empty]=1
w*=((1-jaw_target)/np.maximum(nonjaw,1e-8))[:,None];w[:,idx['jaw']]=jaw_target
order=np.argsort(w,axis=1)[:,-4:];values=np.take_along_axis(w,order,axis=1);values/=values.sum(axis=1,keepdims=True)
np.savez_compressed(ROOT/'surface_rig_data.npz',vertices=v,displacement=displacement,open_delta=open_delta,wide_delta=wide_delta,tooth_region=tooth_strength,bone_indices=order.astype(np.int16),weights=values.astype(np.float32),bone_names=np.array(names))
cfg.update(identity='M-10 / 沉匣 SurfaceRigV5',max_influences=4,weight_method='Bent knee reference, ordered joint blending, eight intermediate socket bones, welded texture displacement and jaw tissue correctives')
(ROOT/'rig_definition.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
report={'legs':diagnosis,'displacement_cm':[float(sampled.min()*100),float(sampled.max()*100)],'displaced_vertices':int((abs(sampled)>.0001).sum()),'bones':len(cfg['bones']),'morphs':['M10_MouthOpenTissue','M10_MouthWideTissue'],'source_topology_preserved':True,'source_triangles':len(faces),'source_analysis':True,'game_tested':False}
(ROOT/'source_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
