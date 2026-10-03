"""M09 source extraction and anatomical selection input production. No rendering or acceptance tests."""
import json, struct, shutil, hashlib
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
SRC=Path("C:/Users/allan/Downloads/Meshy_AI_Bound_Oculamoth_1003131003_texture.glb")
for sub in ["Source","Authoring","Textures","Exports","Records"]: (ROOT/sub).mkdir(parents=True,exist_ok=True)
copy=ROOT/"Source"/SRC.name
if not copy.exists():shutil.copy2(SRC,copy)
b=copy.read_bytes();off=12
while off<len(b):
 size,kind=struct.unpack_from("<II",b,off);chunk=b[off+8:off+8+size];off+=8+size
 if kind==0x4e4f534a:g=json.loads(chunk)
 elif kind==0x004e4942:binary=chunk
def acc(i):
 a=g["accessors"][i];v=g["bufferViews"][a["bufferView"]];dt={5126:"<f4",5125:"<u4",5123:"<u2",5121:"u1"}[a["componentType"]];n={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[a["type"]]
 return np.ndarray((a["count"],n),dtype=dt,buffer=binary,offset=v.get("byteOffset",0)+a.get("byteOffset",0),strides=(v.get("byteStride",np.dtype(dt).itemsize*n),np.dtype(dt).itemsize)).copy()
p=g["meshes"][0]["primitives"][0];v=acc(p["attributes"]["POSITION"]);f=acc(p["indices"]).reshape(-1,3);uv=acc(p["attributes"]["TEXCOORD_0"]);norm=acc(p["attributes"]["NORMAL"])
_,first,inv=np.unique(np.rint(v.astype(float)/1e-6).astype(np.int64),axis=0,return_index=True,return_inverse=True)
wp=v[first];wf=inv[f];e=np.concatenate([wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]]]);e.sort(1);e=np.unique(e,axis=0)
np.savez_compressed(ROOT/"Authoring"/"source_arrays.npz",positions=v,faces=f,uv=uv,normals=norm,weld_ids=inv,first=first,edges=e)
for i,name in enumerate(["M09_BaseColor.jpg","M09_MetallicRoughness.jpg","M09_Normal.jpg"]):
 im=g["images"][i];bv=g["bufferViews"][im["bufferView"]];(ROOT/"Textures"/name).write_bytes(binary[bv.get("byteOffset",0):bv.get("byteOffset",0)+bv["byteLength"]])
meta={"source_file":str(SRC),"archived_source":str(copy),"sha256":hashlib.sha256(b).hexdigest(),"source_triangles":len(f),"source_vertices":len(v),"source_axes":["X","Y_up","Z_front"],"scale_to_280cm":2.8/float(np.ptp(v[:,1])),"source_min_y":float(v[:,1].min()),"original_preserved":True,"testing_requested":False}
(ROOT/"Records"/"source_manifest.json").write_text(json.dumps(meta,indent=2),encoding="utf8")
# Build the actual connected outer surfaces beyond the integrated root band.
x,y,z=wp.T
candidate=(np.abs(x)>.18)&(y<.26)&(y>-.85)
# Protect the anterior small arms from sheet selection using their observed tube paths.
def segdist(points,a,b):
 a=np.array(a);d=np.array(b)-a;t=np.clip((points-a)@d/(d@d),0,1);return np.linalg.norm(points-a-t[:,None]*d,axis=1)
for sign in [-1,1]:
 for a,b,r in [([sign*.13,-.115,.15],[-sign*.07,-.34,.225],.045),([-sign*.07,-.34,.225],[-sign*.15,-.44,.205],.045)]:
  candidate&=segdist(wp,a,b)>r
ce=e[candidate[e[:,0]]&candidate[e[:,1]]]
gr=coo_matrix((np.ones(len(ce),np.int8),(ce[:,0],ce[:,1])),shape=(len(wp),len(wp))).tocsr()
n,lab=connected_components(gr,directed=False);hist=np.bincount(lab[candidate],minlength=n)
recs=[]
for cid in np.argsort(hist)[-20:][::-1]:
 ids=np.flatnonzero((lab==cid)&candidate)
 if len(ids)<30:continue
 q=wp[ids];recs.append({"id":int(cid),"vertices":len(ids),"min":q.min(0).tolist(),"max":q.max(0).tolist(),"centroid":q.mean(0).tolist()})
np.savez_compressed(ROOT/"Authoring"/"outer_surface_components.npz",candidate=candidate,labels=lab)
(ROOT/"Records"/"outer_surface_components.json").write_text(json.dumps(recs,indent=2),encoding="utf8")
samples=[]
for sx,sy in [(0,.15),(.12,.12),(.18,.15),(.25,.1),(.35,.05),(.4,-.12),(.45,-.30),(.32,-.58),(.25,-.70),(.13,-.12),(.05,-.25),(-.08,-.34),(.11,-.39),(0,-.5),(0,-.65),(.27,.68),(.25,.86)]:
 q=wp[(abs(x-sx)<.008)&(abs(y-sy)<.008)]
 if len(q):samples.append({"xy":[sx,sy],"zmin":float(q[:,2].min()),"zmax":float(q[:,2].max()),"zquartiles":np.quantile(q[:,2],[.1,.25,.5,.75,.9]).tolist()})
(ROOT/"Records"/"surface_landmark_samples.json").write_text(json.dumps(samples,indent=2),encoding="utf8")
print(json.dumps({"outer_components":recs,"surface_samples":samples},indent=2),flush=True)
