"""Author source-preserving semantic parts and restrained local clearances for M09."""
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
a=np.load(ROOT/"Authoring/source_arrays.npz")
p=a["positions"].astype(float);f=a["faces"].astype(np.int32);first=a["first"];weld=a["weld_ids"];e=a["edges"];wp=p[first];wf=weld[f];N=len(wp)
x,y,z=wp.T;ax=abs(x)
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def sd(q,a,b):
 a=np.asarray(a);d=np.asarray(b)-a;t=np.clip((q-a)@d/(d@d),0,1);return np.linalg.norm(q-a-t[:,None]*d,axis=1)
# Explicit anatomical envelopes derive from the original mesh and its source coordinates.
trunk=((x/.107)**2+((z-.13)/.145)**2<1.0)&(y<.32)&(y>-.51)
central=(ax<.060)&(y<.34)&(y>-.53)
head=(ax<.158)&(y<-.49)&(z>-.023)
body=trunk|central|head|(y>.30)
small_curves={}
for side,s in [("L",1),("R",-1)]:
 small_curves[side]=np.array([[s*.131,-.118,.224],[s*.07,-.218,.275],[-s*.064,-.319,.290],[-s*.117,-.379,.254],[-s*.153,-.425,.225]])
 dist=np.min(np.stack([sd(wp,aa,bb) for aa,bb in zip(small_curves[side][:-1],small_curves[side][1:])]),axis=0)
 body|=(dist<.052)&(z>.19)
# Preserve narrow attached root strip. Distal membranes are classified by intrinsic paths.
candidate=(~body)&(y<.30)&(y>-.88)&(ax>.075)
ee=e[candidate[e[:,0]]&candidate[e[:,1]]]
length=np.linalg.norm(wp[ee[:,0]]-wp[ee[:,1]],axis=1)
# Weighted path follows the actual surface, with creases resisting cross-layer propagation.
wn=np.zeros_like(wp)
for k in range(3):wn[:,k]=np.bincount(weld,weights=a["normals"][:,k],minlength=N)
wn/=np.maximum(np.linalg.norm(wn,axis=1,keepdims=True),1e-9)
dot=np.sum(wn[ee[:,0]]*wn[ee[:,1]],axis=1)
cost=length*(1+12*np.clip(1-dot,0,2)**2)
graph=coo_matrix((np.r_[cost,cost],(np.r_[ee[:,0],ee[:,1]],np.r_[ee[:,1],ee[:,0]])),shape=(N,N)).tocsr()
# Authored lobar landmarks use depth as well as silhouette and surface connectivity.
target_groups=[
 [[.27,.105,.080],[.35,.045,.050],[.405,-.115,.018]],
 [[.36,-.205,.176],[.447,-.302,.151],[.50,-.38,.104]],
 [[.30,-.52,-.132],[.321,-.59,-.153],[.255,-.715,-.183]]
]
names=["M09_Body_RootBand"];seed_records=[];distance=[]
for side,s in [("L",1),("R",-1)]:
 ids=np.flatnonzero(candidate&(x*s>0));tree=cKDTree(wp[ids])
 for layer,targets in enumerate(target_groups,1):
  tt=np.array(targets)*[s,1,1];_,near=tree.query(tt);seeds=np.unique(ids[near])
  d=dijkstra(graph,directed=False,indices=seeds,min_only=True)
  d[x*s<0]=np.inf;distance.append(d)
  names.append("M09_Membrane_"+side+str(layer))
  seed_records.append({"name":names[-1],"landmarks_source":wp[seeds].tolist(),"method":"multi-landmark intrinsic distance with crease cost"})
D=np.array(distance)
wl=(np.argmin(D,axis=0)+1).astype(np.int16)
wl[~candidate|~np.isfinite(D.min(0))]=0
# Face ownership is conservative at the body connection; source triangle IDs survive.
vl=wl[wf];fl=np.zeros(len(f),np.int16)
mask=(vl!=0).all(1)
votes=np.stack([(vl==i).sum(1) for i in range(1,7)],axis=1)
fl[mask]=np.argmax(votes[mask],axis=1)+1
# Keep one principal connected surface per lobe. Reassign tiny boundary slivers locally.
for label in range(1,7):
 ids=np.flatnonzero(fl==label)
 if not len(ids):continue
 ff=wf[ids];edges=np.r_[ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]
 gr=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(N,N)).tocsr()
 _,cc=connected_components(gr,directed=False)
 fc=cc[ff[:,0]];hist=np.bincount(fc);largest=int(np.argmax(hist))
 slivers=ids[fc!=largest]
 # Unattached classification slivers stay on the body so no visible source face is discarded.
 fl[slivers]=0
centres=p[f].mean(1)
# Semantic crown cut below the flexible neck; surrounding leaves retain their ownership.
names.append("M09_EyeCrown");crown_id=len(names)-1
fcx,fcy,fcz=centres.T
fl[(fl==0)&(fcy<-.475)&(abs(fcx)<.168)&(fcz>-.022)]=crown_id
# Split front small arms with curve-following ownership. Original shoulder seams stay fixed.
arm_ids={}
armdist=[]
for side in ["L","R"]:
 curve=small_curves[side]
 armdist.append(np.min(np.stack([sd(centres,aa,bb) for aa,bb in zip(curve[:-1],curve[1:])]),axis=0))
ad=np.array(armdist);arm_owner=ad.argmin(0)
for j,side in enumerate(["L","R"]):
 names.append("M09_SmallArm_"+side);label=len(names)-1;arm_ids[side]=label
 take=(fl==0)&(arm_owner==j)&(ad[j]<.046)&(fcy<-.135)&(fcy>-.47)&(fcz>.210)
 fl[take]=label
# Each main eye keeps the visible source dome and its original iris UV; unseen backs are authored later.
eye_specs=[
 ("01",[-.063,-.579],.044,.040),
 ("02",[.057,-.665],.046,.041),
 ("03",[-.062,-.733],.037,.033),
 ("04",[.035,-.786],.032,.028),
 ("05",[-.035,-.845],.026,.024)
]
eye_ids=[]
for name,xy,rx,ry in eye_specs:
 names.append("M09_MainEye_"+name);label=len(names)-1;eye_ids.append(label)
 take=(fl==crown_id)&(((fcx-xy[0])/rx)**2+((fcy-xy[1])/ry)**2<1)&(fcz>.210)
 fl[take]=label
# Upper cuffs become their own hard-surface regions following oblique wrist sections.
cuff_ids={}
for side,s in [("L",1),("R",-1)]:
 names.append("M09_Cuff_"+side);label=len(names)-1;cuff_ids[side]=label
 # Cuff axis through observed wrist, tilted inward as it rises.
 axis=np.array([-s*.075,.13,.018]);axis/=np.linalg.norm(axis)
 cc=np.array([s*.217,.682,.145])
 t=(centres-cc)@axis
 take=(fl==0)&(fcx*s>0)&(abs(t)<.039)&(fcy>.62)&(fcy<.74)
 # Cuffs remain on the original continuous body to preserve wrist skin.
# Define five actual curled finger lanes, following hand proportions and source depth.
digit_ids=[];digit_guides={}
for side,s in [("L",1),("R",-1)]:
 use=(fl==0)&(fcx*s>0)&(fcy>.805)
 ids=np.flatnonzero(use)
 if not len(ids):continue
 # Medial thumb to lateral little finger, an arced knuckle row.
 targets=np.array([[.100,.892,.172],[.131,.926,.174],[.172,.940,.183],[.217,.922,.188],[.248,.899,.176]])*[s,1,1]
 targets[:,2]=np.array([.176,.180,.187,.190,.179])
 # Distance to a curved phalange path instead of vertical X strips.
 paths=[]
 base_x=[.128,.145,.168,.188,.202]
 for k,tip in enumerate(targets):
  base=np.array([s*base_x[k],.805,.167])
  bend=np.array([s*(abs(tip[0])*.75+base_x[k]*.25),tip[1]-.028,.145])
  paths.append(np.stack([base,bend,tip,tip+np.array([s*.003,-.022,.026])]))
 dd=np.array([np.min(np.stack([sd(centres[ids],aa,bb) for aa,bb in zip(path[:-1],path[1:])]),axis=0) for path in paths])
 owner=dd.argmin(0)
 for k,path in enumerate(paths):
  names.append("M09_HookFinger_"+side+"_"+str(k+1).zfill(2));label=len(names)-1;digit_ids.append(label);digit_guides[label]=path
  fl[ids[owner==k]]=label
# Production attributes are calculated from part incidence and used directly in authoring.
incidence=np.zeros((N,7),bool)
for label in range(7):
 ids=np.unique(wf[fl==label]);incidence[ids,label]=True
deltas=np.zeros((7,N,3),np.float32)
root_weight=np.ones((7,N),np.float32)
panel_info=[]
for label in range(1,7):
 ids=np.flatnonzero(fl==label);verts=np.unique(wf[ids]);ff=wf[ids]
 side=1 if label<=3 else -1;layer=(label-1)%3
 # Keep every source seam fixed. Free regions gain millimetric spacing without tearing roots.
 boundary=verts[incidence[verts,0]]
 # Keep only the anatomical attached upper strip fixed; inter-leaf margins remain free.
 anatomical=boundary[(wp[boundary,1]>.08)&(np.abs(wp[boundary,0])<.235)]
 if len(anatomical)==0:
  anatomical=boundary[wp[boundary,1]>=np.quantile(wp[boundary,1],.9)] if len(boundary) else np.array([verts[np.argmax(wp[verts,1])]])
 boundary=anatomical
 localedges=np.r_[ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]];localedges.sort(1);localedges=np.unique(localedges,axis=0)
 lengths=np.linalg.norm(wp[localedges[:,0]]-wp[localedges[:,1]],axis=1)
 gg=coo_matrix((np.r_[lengths,lengths],(np.r_[localedges[:,0],localedges[:,1]],np.r_[localedges[:,1],localedges[:,0]])),shape=(N,N)).tocsr()
 dist=dijkstra(gg,indices=boundary,directed=False,min_only=True)
 weight=smooth((dist[verts]-.015)/.12)
 offset=np.array([side*[.007,.004,.002][layer],0,[.011,.001,-.009][layer]])
 deltas[label,verts]=weight[:,None]*offset
 root_weight[label,verts]=1-smooth((dist[verts]-.015)/.06)
 panel_info.append({"name":names[label],"source_faces":int(len(ids)),"fixed_seam_vertices":int(len(boundary)),"free_clearance_offset_source":offset.tolist(),"root_invariant":"anatomical root strip fixed; inter-leaf cut edges free and independently closed"})
# Preserve geometry behind eye sockets and all material detail while freeing arm/digit interfaces in assembly.
np.savez_compressed(ROOT/"Authoring"/"semantic_parts_v02.npz",face_labels=fl,membrane_delta=deltas,root_weight=root_weight)
partcounts=[{"id":i,"name":name,"source_faces":int(np.count_nonzero(fl==i))} for i,name in enumerate(names)]
spec={"version":"M09_SourceSeparation_V02","part_names":names,"parts":partcounts,"membranes":panel_info,"membrane_seeds":seed_records,"small_arm_ids":arm_ids,"small_arm_guides_source":{k:v.tolist() for k,v in small_curves.items()},"crown_id":crown_id,"eye_ids":eye_ids,"eye_specs":eye_specs,"cuff_ids":cuff_ids,"digit_ids":digit_ids,"digit_guides_source":{str(k):v.tolist() for k,v in digit_guides.items()},"claimed_exact_organ_cut":False,"method":"source-face semantic partition; new hidden closure surfaces explicitly separate","testing_performed":False}
(ROOT/"Records"/"parts_recipe_v02.json").write_text(json.dumps(spec,indent=2),encoding="utf8")
print(json.dumps({"authored_parts":partcounts,"membranes":panel_info},indent=2),flush=True)
