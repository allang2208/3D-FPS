"""Author M09 semantic skeleton and normalized four-influence weights.
Works on V02 parts. No pose probes, renders, reimports or engine tests.
"""
from pathlib import Path
import json,numpy as np
from scipy.spatial import cKDTree
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
OUT=ROOT/"RigV03"
a=np.load(OUT/"Work/rig_input.npz")
meta=json.loads((OUT/"Work/rig_input.json").read_text())
manifest=json.loads((ROOT/"Records/source_manifest.json").read_text())
parts_recipe=json.loads((ROOT/"Records/parts_recipe_v02.json").read_text())
source=np.load(ROOT/"Authoring/source_arrays.npz")
source_weld=source["weld_ids"];source_positions=source["positions"]
S=manifest["scale_to_280cm"];BOTTOM=manifest["source_min_y"]
def world(p):
 p=np.asarray(p,dtype=float);return np.stack([p[...,0]*S,-p[...,2]*S,(p[...,1]-BOTTOM)*S],axis=-1)
def src(p):
 p=np.asarray(p,dtype=float);return np.stack([p[...,0]/S,p[...,2]/S+BOTTOM,-p[...,1]/S],axis=-1)
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
bones=[];index={};chains={};controls=[]
def bone(name,head,tail,parent=None,group="Body",deform=True):
 index[name]=len(bones)
 bones.append(dict(name=name,head=np.asarray(head).tolist(),tail=np.asarray(tail).tolist(),
                   parent=parent,group=group,deform=deform))
 return name
def make_chain(stem,points,parent,group):
 names=[]
 for j in range(len(points)-1):
  name=f"{stem}_{j+1:02d}";bone(name,points[j],points[j+1],parent,group);parent=name;names.append(name)
 chains[stem]={"points":np.asarray(points),"names":names}
 return names
def small_delta(p,side):
 p=np.asarray(p,dtype=float).copy();sgn=1 if side=="L" else -1
 t=smooth((-p[...,1]-.135)/.22);p[...,0]+=sgn*.012*t;p[...,2]+=(.025 if side=="L" else .008)*t
 return p
bone("root",[0,0,0],[0,0,.15])
bone("suspension",world([0,.805,.16]),world([0,.285,.125]),"root")
spine_points=world([[0,.285,.125],[0,.10,.12],[0,-.10,.13],[0,-.30,.15],[0,-.475,.16]])
spine_names=make_chain("spine",spine_points,"suspension","Body")
# Arms are custom chains; the lower body has no pelvis/legs to force into a humanoid skeleton.
small_paths={}
for side,sgn in [("L",1),("R",-1)]:
 points=world([[0,.285,.125],[sgn*.140,.323,.13],[sgn*.355,.515,.111],[sgn*.173,.760,.153],[sgn*.167,.813,.174]])
 big_names=[]
 for k,label in enumerate(["clavicle","upperarm","forearm","hand"]):
  name=f"big_{label}_{side}";bone(name,points[k],points[k+1],spine_names[0] if k==0 else big_names[-1],"Suspension arms");big_names.append(name)
 chains["big_"+side]={"points":points,"names":big_names}
 # A helper for the soft proximal forearm; the cuff region is explicitly excluded in weighting.
 t0=points[2]*.5+points[3]*.5
 bone(f"big_forearm_twist_{side}",t0,points[3],big_names[2],"Suspension arms")
 for k in range(5):
  pid=17+k+(5 if side=="R" else 0)
  path=np.array(parts_recipe["digit_guides_source"][str(pid)],float)
  w=smooth((path[:,1]-.805)/.08);path[:,0]+=sgn*(k-2)*.0028*w;path[:,2]+=(.0015 if k%2 else -.0015)*w
  make_chain(f"hook_{side}_{k+1:02d}",world(path),big_names[-1],"Hook fingers")
 sp=np.array([[sgn*.120,-.105,.219],[sgn*.127,-.168,.251],[-sgn*.041,-.286,.287],[-sgn*.085,-.341,.287]])
 sp=small_delta(sp,side);sw=world(sp);sn=[]
 for k,label in enumerate(["upperarm","forearm","hand"]):
  name=f"small_{label}_{side}";bone(name,sw[k],sw[k+1],spine_names[2] if k==0 else sn[-1],"Small arms");sn.append(name)
 chains["small_"+side]={"points":sw,"names":sn};small_paths[side]=sw
 # Authored digit centre lines, including the source finger remnants on the body object.
 # Fit terminal positions to the original local hand surface without introducing new geometry.
 left_digits=[
  [[-.088,-.319,.283],[-.132,-.322,.280],[-.164,-.334,.267],[-.186,-.346,.253]],
  [[-.105,-.342,.283],[-.136,-.358,.274],[-.165,-.380,.249],[-.182,-.392,.230]],
  [[-.095,-.352,.279],[-.120,-.385,.270],[-.137,-.420,.245],[-.139,-.447,.218]],
  [[-.076,-.353,.284],[-.098,-.385,.282],[-.111,-.413,.269],[-.117,-.430,.245]],
  [[-.057,-.344,.295],[-.057,-.369,.297],[-.050,-.392,.281],[-.041,-.405,.264]],
 ]
 pp=source_positions
 region=(pp[:,0]*sgn<-.010)&(pp[:,0]*sgn>-.215)&(pp[:,1]<-.305)&(pp[:,1]>-.466)&(pp[:,2]>.205)
 cloud=pp[region];tree=cKDTree(cloud)
 for k,pts in enumerate(left_digits):
  path=np.asarray(pts,float)*[sgn,1,1]
  # The right palm has shorter, differently angled fingers.
  if side=="R":
   path[:,1]=-.30+(path[:,1]+.30)*.84
  for j in range(1,4):
   dd,ii=tree.query(path[j],k=16)
   local=cloud[ii]
   # Keep the artist-authored centre line, correcting only toward nearby source tissue.
   centre=local.mean(0)
   if dd[0]<.032:
    path[j]=path[j]*.25+centre*.75
  path=small_delta(path,side)
  make_chain(f"smallfinger_{side}_{k+1:02d}",world(path),sn[-1],"Small fingers")
 # Editable IK, off in the stored rest pose, with a geometric pole outside each arm.
 for kind,cp,cn in [("big",points[1:4],big_names[1:3]),("small",sw[:3],sn[:2])]:
  shoulder,elbow,wrist=cp
  axis=wrist-shoulder;proj=shoulder+axis*np.dot(elbow-shoulder,axis)/np.dot(axis,axis)
  bend=elbow-proj;bend/=max(np.linalg.norm(bend),1e-8)
  pole=elbow+bend*(.32 if kind=="big" else .16)
  hand=bones[index[f"{kind}_hand_{side}"]]
  ctrl=f"CTRL_{kind}_grip_{side}";polename=f"CTRL_{kind}_elbow_{side}"
  bone(ctrl,hand["head"],hand["tail"],"root","IK controls",False)
  bone(polename,pole,pole+np.array([0,0,.07]),"root","IK controls",False)
  controls.append(dict(kind=kind,side=side,target=ctrl,pole=polename,upper=cn[0],forearm=cn[1],
                       hand=f"{kind}_hand_{side}",property=f"IK_{kind}_{side}",default=0.0))
# Each membrane gets a four-bone flex chain fitted to the actual part, not a mirrored generic wing.
membrane_names={}
for part in meta["parts"]:
 pid=part["id"]
 if not 1<=pid<=6:continue
 name=part["name"];p=a[f"p{pid}_positions"].astype(float);ids=a[f"p{pid}_source_ids"]
 pp=p[ids>=0];root=np.array(meta["guides"][name+"_ROOT"])
 direction=pp.mean(0)-root;direction/=np.linalg.norm(direction);proj=(pp-root)@direction
 end=pp[proj>=np.quantile(proj,.99)].mean(0)
 extent=np.dot(end-root,direction)
 points=[root]
 for t in [.25,.50,.75]:
  select=np.abs(proj/extent-t)<.075
  centre=pp[select].mean(0) if select.any() else root+(end-root)*t
  # Keep the rib inside the panel but avoid an irregular silhouette dictating a zigzag skeleton.
  points.append(centre*.65+(root+(end-root)*t)*.35)
 points.append(end)
 sy=src(root)[1]
 par=spine_names[0 if sy>.10 else 1 if sy>-.10 else 2 if sy>-.30 else 3]
 tag=name.replace("M09_Membrane_","")
 membrane_names[pid]=make_chain("membrane_"+tag,np.array(points),par,"Membrane "+tag)
# Crown pendulum: rigid eye-bearing mass, flexible attachment collar, five separate aiming bones.
bone("crown_neck",world([0,-.468,.16]),world([0,-.555,.158]),spine_names[-1],"Eye crown")
bone("eye_crown",world([0,-.555,.158]),world([0,-.925,.11]),"crown_neck","Eye crown")
for k in range(1,6):
 head=np.array(meta["guides"][f"M09_MainEye_{k:02d}_Pivot"])
 bone(f"eye_{k:02d}",head,head+np.array([0,-.06,0]),"eye_crown","Main eyes")
# Skin authoring: capsule projection within an explicit anatomical owner, not all-bone nearest binding.
B=len(bones)
def empty(n):return np.zeros((n,B),np.float32)
def chain_weights(p,chain,width=.055):
 c=chains[chain];q=c["points"];d=q[1:]-q[:-1];length=np.linalg.norm(d,axis=1)
 t=np.clip(np.einsum("nkj,kj->nk",p[:,None,:]-q[:-1],d)/np.maximum(length**2,1e-12),0,1)
 closest=q[:-1]+t[:,:,None]*d
 ds=np.sum((p[:,None,:]-closest)**2,axis=2);j=ds.argmin(1)
 offsets=np.r_[0,np.cumsum(length)]
 along=offsets[j]+t[np.arange(len(p)),j]*length[j]
 out=empty(len(p));out[np.arange(len(p)),[index[c["names"][i]] for i in j]]=1
 for k in range(1,len(c["names"])):
  half=min(width,length[k-1]*.30,length[k]*.30)
  near=np.abs(along-offsets[k])<half
  blend=smooth((along[near]-offsets[k]+half)/(2*half))
  out[near]=0;out[near,index[c["names"][k-1]]]=1-blend;out[near,index[c["names"][k]]]=blend
 return out,np.sqrt(ds.min(1)),along
def spine_weights(p):
 # Vertical source bands ensure consistent attachment weights across independently capped parts.
 return chain_weights(p,"spine",width=.065)[0]
def arm_weights(p,side):
 out,dist,along=chain_weights(p,"big_"+side,.063)
 ps=src(p);fore=index[f"big_forearm_{side}"];twist=index[f"big_forearm_twist_{side}"]
 # Forearm twist is a sibling helper. Preserve the rigid cuff band by keeping it on forearm.
 tw=.55*smooth((ps[:,1]-.545)/.080)*(1-smooth((ps[:,1]-.638)/.020))
 amount=out[:,fore]*tw
 out[:,fore]-=amount;out[:,twist]+=amount
 cuff=(ps[:,1]>.666)&(ps[:,1]<.746)
 out[cuff]=0;out[cuff,fore]=1
 return out
def small_weights(p,side):
 out,dist,along=chain_weights(p,"small_"+side,.030)
 dweights=[];distances=[];params=[]
 for k in range(1,6):
  w,ds,t=chain_weights(p,f"smallfinger_{side}_{k:02d}",.015)
  dweights.append(w);distances.append(ds);params.append(t)
 distances=np.stack(distances,1);winner=distances.argmin(1)
 sw=chains["small_"+side]["points"];forward=sw[-1]-sw[-2];forward/=np.linalg.norm(forward)
 # Fingers may branch sideways from the palm. Use each individual base/tangent for the hand blend.
 for k in range(5):
  pick=winner==k
  if not pick.any():continue
  cp=chains[f"smallfinger_{side}_{k+1:02d}"]["points"]
  tangent=cp[1]-cp[0];tangent/=np.linalg.norm(tangent)
  proj=(p[pick]-cp[0])@tangent
  blend=smooth((proj+.002)/.025)
  # No finger weights back at the wrist/forearm.
  blend*=smooth(((p[pick]-sw[-2])@forward-.022)/.028)
  out[pick]=out[pick]*(1-blend[:,None])+dweights[k][pick]*blend[:,None]
 return out,np.minimum(dist,distances.min(1))
def body_weights(p,include_small=True):
 out=spine_weights(p);ps=src(p)
 for side,sgn in [("L",1),("R",-1)]:
  blend=smooth((ps[:,0]*sgn-.076)/.092)*smooth((ps[:,1]-.252)/.080)
  pick=blend>0
  out[pick]=out[pick]*(1-blend[pick,None])+arm_weights(p[pick],side)*blend[pick,None]
 if include_small:
  ww=[];dd=[]
  for side in ["L","R"]:
   sw,ds=small_weights(p,side);ww.append(sw);dd.append(ds)
  dd=np.stack(dd,1);owner=dd.argmin(1)
  for k in range(2):
   # Capture front-of-torso arm and finger remnants without weighting the abdomen behind them.
   blend=(1-smooth((dd[:,k]/S-.022)/.021))*smooth((ps[:,2]-.212)/.025)
   blend*=smooth((-ps[:,1]-.115)/.055)*(1-smooth((-ps[:,1]-.450)/.025))
   blend*=owner==k
   pick=blend>0
   out[pick]=out[pick]*(1-blend[pick,None])+ww[k][pick]*blend[pick,None]
 return out
weights={};stats=[];seam_reference={}
for part in meta["parts"]:
 pid=part["id"];p=a[f"p{pid}_positions"].astype(float);ids=a[f"p{pid}_source_ids"];fixed=a[f"p{pid}_fixed"]
 print("AUTHORING_SKIN",part["name"],len(p),flush=True)
 if pid==0:
  w=body_weights(p)
 elif 1<=pid<=6:
  stem="membrane_"+part["name"].replace("M09_Membrane_","")
  w,_,_=chain_weights(p,stem,.075)
  # Full pin at the anatomical strip; free inter-leaf edges retain their own flex weights.
  anchor=body_weights(p,include_small=False)
  w=w*(1-fixed[:,None])+anchor*fixed[:,None]
 elif pid==7:
  w=empty(len(p));ps=src(p)
  collar=1-smooth((-.475-ps[:,1])/.072)
  w[:,index["crown_neck"]]=collar;w[:,index["eye_crown"]]=1-collar
  root_blend=fixed*.70
  # Neck and spine roots use the identical root reference, preventing an independently moving cut rim.
  w=w*(1-root_blend[:,None])+spine_weights(p)*root_blend[:,None]
 elif pid in [8,9]:
  side="L" if pid==8 else "R"
  w,_=small_weights(p,side);anchor=body_weights(p)
  w=w*(1-fixed[:,None])+anchor*fixed[:,None]
 elif 10<=pid<=14:
  w=empty(len(p));w[:,index[f"eye_{pid-9:02d}"]]=1
 else:
  side="L" if pid<22 else "R";k=pid-16 if side=="L" else pid-21
  w,_,_=chain_weights(p,f"hook_{side}_{k:02d}",.013)
  w*=1-fixed[:,None];w[:,index[f"big_hand_{side}"]]+=fixed
 # New hidden closure vertices inherit the local owner field; no nearest-other-part shortcuts.
 # At unchanged cut rims, use the body source vertex's exact authored weights.
 if pid==0:
  for vi in np.flatnonzero(ids>=0):seam_reference[int(source_weld[ids[vi]])]=vi
  body_w=w
 elif pid in [1,2,3,4,5,6,7,8,9] or pid>=17:
  candidate=np.flatnonzero((ids>=0)&(fixed>.999))
  original=world(source_positions[ids[candidate]])
  candidate=candidate[np.linalg.norm(p[candidate]-original,axis=1)<.00003]
  for vi in candidate:
   ref=seam_reference.get(int(source_weld[ids[vi]]))
   if ref is not None:w[vi]=body_w[ref]
 # Top-four normalization is production input, not a test. 1024-unit quantization preserves exact sums.
 top=np.argpartition(w,-4,axis=1)[:,-4:]
 vals=np.take_along_axis(w,top,1);vals/=np.maximum(vals.sum(1,keepdims=True),1e-12)
 quant=np.rint(vals*1024).astype(np.int16);major=vals.argmax(1)
 quant[np.arange(len(p)),major]+=(1024-quant.sum(1)).astype(np.int16)
 weights[f"p{pid}_bones"]=top.astype(np.uint16);weights[f"p{pid}_weights"]=quant
 stats.append(dict(name=part["name"],vertices=len(p),weighted_vertices=len(p),
                   influence_limit=4,quantization=1024,method="anatomical part restricted, normalized"))
np.savez_compressed(OUT/"Authoring/skin_weights_v03.npz",**weights)
plan={"version":"M09_RigV03","source":meta["input"],"rig_name":"M09_Rig_V03",
 "bones":bones,"controls":controls,"parts":meta["parts"],"weight_receipt":stats,
 "chains":{name:{"points":c["points"].tolist(),"names":c["names"]} for name,c in chains.items()},
 "counts":{"bones_total":len(bones),"deform_and_export_bones":sum(b["deform"] for b in bones),
           "control_bones":sum(not b["deform"] for b in bones),"mesh_parts":len(meta["parts"]),
           "vertices":sum(p["vertices"] for p in meta["parts"])},
 "scope":"Authored skeleton and skinning only; no motion clips, UE import, pose tests, renders or acceptance.",
 "note":"V02 source topology retained, including partial small-finger remnants on the body. Those receive matching semantic digit weights. No decimation."}
(OUT/"Authoring/rig_recipe_v03.json").write_text(json.dumps(plan,indent=2),encoding="utf8")
print("RIG_RECIPE_SAVED",plan["counts"],flush=True)
