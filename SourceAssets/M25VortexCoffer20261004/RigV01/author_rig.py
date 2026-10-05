"""Author M25 skin and original peristaltic motion; preserve source mesh and maps.
No render, pose test, UE session, or runtime work is performed by this script.
Coordinates throughout this file are glTF metres: +Z forward, +Y up, +X across.
"""
from pathlib import Path
import copy, json, math, shutil, struct
import numpy as np
from scipy.spatial.transform import Rotation

OUT=Path(__file__).resolve().parent
INPUT=OUT.parent/"Inputs"/"Meshy_AI_Arcane_Maw_1004062246_texture.glb"
INPUT.parent.mkdir(exist_ok=True)
original=Path(r"C:/Users/allan/Downloads/Meshy_AI_Arcane_Maw_1004062246_texture.glb")
if not INPUT.exists(): shutil.copy2(original,INPUT)
with INPUT.open("rb") as f:
    f.seek(12)
    size,kind=struct.unpack("<II",f.read(8)); doc=json.loads(f.read(size))
    size,kind=struct.unpack("<II",f.read(8)); binary=bytearray(f.read(size))
positions=np.load(OUT/"fitted_positions.npy")
META=json.loads((OUT/"fitting_inputs.json").read_text())
N=len(positions)
SECTIONS=np.linspace(-1.60,1.56,7)
FPS=30
PERIOD=2.8
SPEED=.16
DUTY=.70

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0.,1.)
    return t*t*(3.-2.*t)

def orient(direction):
    v=np.asarray(direction,dtype=float)
    v/=np.linalg.norm(v)
    axis=np.cross([0.,1.,0.],v)
    dot=float(v[1])
    if dot < -.999999: return Rotation.from_rotvec([math.pi,0,0]).as_matrix()
    q=np.r_[axis,1.+dot]; q/=np.linalg.norm(q)
    return Rotation.from_quat(q).as_matrix()

spec=[]
lookup={}
def bone(name,head,tail,parent=None,region="body",deform=True,**extra):
    head=np.array(head,dtype=float);tail=np.array(tail,dtype=float)
    entry=dict(name=name,head=head.tolist(),tail=tail.tolist(),
        parent=parent,region=region,deform=deform,**extra)
    entry["rotation"]=orient(tail-head).tolist()
    lookup[name]=len(spec);spec.append(entry)
    return len(spec)-1

bone("root",[0,0,0],[0,.14,0],deform=False,region="root")
belly_id=bone("belly_support",[0,.065,0],[0,.065,.18],"root","belly_support")
centers=[];lobes=[]
for i,z in enumerate(SECTIONS):
    h=.36+.17*math.sin(math.pi*i/6)
    center=bone(f"body_{i:02d}",[0,h,z],[0,h,z+.20],"root","body",section=i)
    centers.append(center);row=[]
    width=.74*math.sqrt(max(.30,1.-(z/2.2)**2))
    for sign,side in [(-1,"L"),(1,"R")]:
        row.append(bone(f"sac_{i:02d}.{side}",[sign*width,h*.94,z],
            [sign*(width+.14),h*.94,z],spec[center]["name"],"sac",section=i,side=sign))
    lobes.append(row)

# Ground-contact guides follow the actual low surface perimeter, with one chain
# per sector. Thin connected veil regions are driven smoothly between sectors.
low=positions[positions[:,1]<.17]
rho=np.sqrt((low[:,0]/1.6726)**2+(low[:,2]/2.05)**2)
theta=np.arctan2(low[:,0]/1.6726,low[:,2]/2.05)
feet=[]
for i in range(32):
    angle=2*math.pi*i/32
    diff=np.arctan2(np.sin(theta-angle),np.cos(theta-angle))
    ids=np.where(np.abs(diff)<math.pi/32*.85)[0]
    if len(ids):
        selected=ids[np.argsort(rho[ids])[int(len(ids)*.85):]]
        tip=np.median(low[selected],axis=0)
    else:
        tip=np.array([1.6726*math.sin(angle),.035,2.05*math.cos(angle)])
    tip[1]=max(.028,float(tip[1]))
    base=tip*np.array([.53,0,.53])+[0,.26,0]
    mid=tip*np.array([.79,0,.79])+[0,.085,0]
    tail=tip+(tip-mid)*.18
    tail[1]=tip[1]
    root_id=bone(f"tendril_{i:02d}_base",base,mid,"root","tendril_base",sector=i,angle=angle)
    mid_id=bone(f"tendril_{i:02d}_mid",mid,tip,spec[root_id]["name"],"tendril_mid",sector=i,angle=angle)
    tip_id=bone(f"tendril_{i:02d}_tip",tip,tail,spec[mid_id]["name"],"tendril_tip",sector=i,angle=angle)
    feet.append(dict(angle=angle,base=root_id,mid=mid_id,tip=tip_id))

mouth_id=bone("maw",[0,.50,1.43],[0,.50,1.65],"body_06","mouth")
rings=[]
for i in range(8):
    a=2*math.pi*i/8
    head=np.array([.39*math.cos(a),.50+.34*math.sin(a),1.51])
    rings.append(bone(f"maw_rim_{i:02d}",head,head+[0,0,.12],"maw","maw_rim",angle=a))
bone("socket_maw",[0,.50,1.72],[0,.50,1.87],"maw","socket",False)
# Source-fitted insulator tips. Ridge folds/straps from the height map are not
# treated as electrical terminals.
pole_tips=[
    [-.02,1.291417,.58],[-.42,1.21240,0.],[.38,1.21330,.02],
    [-.66,1.07349,.46],[.62,1.07668,.48],
    [-.42,1.08152,-.44],[.42,1.06984,-.40],
    [-.36,.88761,-.78],[.38,.88299,-.74]]
poles=[]
for i,tip in enumerate(pole_tips):
    tip=np.array(tip);height=.26 if i==0 else (.23 if i<7 else .19)
    base=tip.copy();base[1]-=height;base[0]*=.91
    section=int(np.argmin(np.abs(SECTIONS-base[2])))
    poles.append(bone(f"electrode_{i:02d}",base,tip,f"body_{section:02d}",
        "electrode",section=section,radius=.108))
    bone(f"socket_electric_{i:02d}",tip,tip+[0,.07,0],f"electrode_{i:02d}","socket",False)
B=len(spec)
rest=np.tile(np.eye(4),(B,1,1))
for i,s in enumerate(spec):
    rest[i,:3,:3]=s["rotation"];rest[i,:3,3]=s["head"]
parent=np.array([lookup[s["parent"]] if s["parent"] else -1 for s in spec])
rest_inverse=np.linalg.inv(rest)
(OUT/"skeleton_spec.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")
print(f"AUTHOR fitted {B} bones, 32 perimeter chains, 9 rigid electrodes",flush=True)

joints=np.zeros((N,4),dtype=np.uint16)
weights=np.zeros((N,4),dtype=np.float32)
body_ids=np.array([[lobes[i][0],centers[i],lobes[i][1]] for i in range(7)])
for start in range(0,N,40000):
    p=positions[start:start+40000];n=len(p);x,y,z=p.T
    score=np.zeros((n,B),np.float32)
    t=np.clip((z-SECTIONS[0])/(SECTIONS[-1]-SECTIONS[0])*6,0,6)
    first=np.minimum(t.astype(int),5);blend=smooth(0,1,t-first)
    lateral=smooth(0,.78,np.abs(x))
    side=np.where(x<0,0,2)
    rows=np.arange(n)
    for section,amount in [(first,1-blend),(first+1,blend)]:
        score[rows,body_ids[section,1]]+=amount*(1-lateral)
        score[rows,body_ids[section,side]]+=amount*lateral

    # Perimeter chains are a semantic low-surface field. Each source-position
    # duplicate receives the same field, including copies on separate UV seams.
    r=np.sqrt((x/1.6726)**2+(z/2.05)**2)
    a=np.arctan2(x/1.6726,z/2.05)
    gate=(1-smooth(.08,.39,y))*smooth(.36,.69,r)
    foot_score=np.zeros_like(score)
    for foot in feet:
        da=np.arctan2(np.sin(a-foot["angle"]),np.cos(a-foot["angle"]))
        angular=np.exp(-.5*(da/.155)**2)
        actual_tip=np.array(spec[foot["tip"]]["head"])
        rt=math.sqrt((actual_tip[0]/1.6726)**2+(actual_tip[2]/2.05)**2)
        local_r=r/max(rt,.5)
        for key,mean,sigma in [("base",.54,.18),("mid",.78,.135),("tip",1.,.125)]:
            foot_score[:,foot[key]]=angular*np.exp(-.5*((local_r-mean)/sigma)**2)
    plant=(1-smooth(.018,.075,y))*smooth(.60,.83,r)
    for foot in feet:
        foot_score[:,foot["base"]]*=1-plant
        foot_score[:,foot["mid"]]*=1-plant
    foot_score/=np.maximum(foot_score.sum(1,keepdims=True),1e-15)
    score=score*(1-gate[:,None])+foot_score*gate[:,None]
    # A neutral underside support protects low central flesh from breathing
    # and body pitch; outer planted tissue follows translation-only toe pads.
    belly_gate=(1-smooth(.015,.075,y))*(1-smooth(.45,.67,r))
    score*=1-belly_gate[:,None];score[:,belly_id]+=belly_gate

    # A protected central throat and eight rim controls; do not drag ground
    # tendrils into the mouth through a broad nearest-bone falloff.
    mx=x/.45;my=(y-.50)/.39
    mr=np.sqrt(mx*mx+my*my)
    mouth_gate=smooth(1.13,1.46,z)*(1-smooth(1.03,1.30,mr))*smooth(.075,.18,y)
    mouth_score=np.zeros_like(score)
    core=1-smooth(.32,.80,mr)
    mouth_score[:,mouth_id]=core
    ma=np.arctan2(my,mx)
    ring_field=[]
    for i in rings:
        da=np.arctan2(np.sin(ma-spec[i]["angle"]),np.cos(ma-spec[i]["angle"]))
        ring_field.append(np.exp(-.5*(da/.55)**2))
    ring_field=np.asarray(ring_field).T
    ring_field/=np.maximum(ring_field.sum(1,keepdims=True),1e-15)
    mouth_score[:,rings]=ring_field*(1-core[:,None])
    score=score*(1-mouth_gate[:,None])+mouth_score*mouth_gate[:,None]

    # The ceramic stack is rigid. Only its short collar transition blends into
    # the supporting sac; the actual disk stack has one joint, no soft scaling.
    for i in poles:
        a=np.array(spec[i]["head"]);b=np.array(spec[i]["tail"])
        u=np.clip((y-a[1])/(b[1]-a[1]),0,1)
        axis=a[None,:]+u[:,None]*(b-a)
        radial=np.sqrt((x-axis[:,0])**2+(z-axis[:,2])**2)
        g=(1-smooth(.108,.15,radial))*smooth(a[1]-.045,a[1]+.025,y)
        score*=1-g[:,None];score[:,i]+=g
    idx=np.argpartition(score,-4,axis=1)[:,-4:]
    val=score[rows[:,None],idx]
    order=np.argsort(-val,axis=1)
    idx=np.take_along_axis(idx,order,1);val=np.take_along_axis(val,order,1)
    val/=np.maximum(val.sum(1,keepdims=True),1e-15)
    joints[start:start+n]=idx;weights[start:start+n]=val
    if start%400000==0:print(f"AUTHOR skinning {start}/{N}",flush=True)
np.savez_compressed(OUT/"skin_weights.npz",joints=joints,weights=weights,
    bone_names=np.array([s["name"] for s in spec]))
print("AUTHOR normalized four-influence skin saved",flush=True)

# Write transformed positions into the original accessor. Every original
# triangle, UV, normal, image and material is retained.
prim=doc["meshes"][0]["primitives"][0]
pa=doc["accessors"][prim["attributes"]["POSITION"]]
view=doc["bufferViews"][pa["bufferView"]]
offset=view.get("byteOffset",0)+pa.get("byteOffset",0)
np.ndarray((N,3),np.float32,buffer=binary,offset=offset,
    strides=(view.get("byteStride",12),4))[:]=positions
pa["min"]=positions.min(0).tolist();pa["max"]=positions.max(0).tolist()
def append_array(array,kind,component):
    array=np.ascontiguousarray(array)
    while len(binary)%4:binary.append(0)
    offset=len(binary);binary.extend(array.tobytes())
    view=len(doc["bufferViews"])
    doc["bufferViews"].append({"buffer":0,"byteOffset":offset,"byteLength":array.nbytes})
    accessor=len(doc["accessors"])
    desc={"bufferView":view,"componentType":component,"count":len(array),"type":kind}
    if kind=="SCALAR":
        desc.update(min=[float(array.min())],max=[float(array.max())])
    doc["accessors"].append(desc)
    return accessor
prim["attributes"]["JOINTS_0"]=append_array(joints,"VEC4",5123)
prim["attributes"]["WEIGHTS_0"]=append_array(weights,"VEC4",5126)
del joints,weights
doc["nodes"]=[{"name":"SK_M25_VortexCoffer_V01","mesh":0,"skin":0}]
doc["meshes"][0]["name"]="SK_M25_VortexCoffer_V01"
for i,s in enumerate(spec):
    local=rest_inverse[parent[i]]@rest[i] if parent[i]>=0 else rest[i]
    node={"name":s["name"],"translation":local[:3,3].tolist(),
          "rotation":Rotation.from_matrix(local[:3,:3]).as_quat().tolist(),
          "extras":{"region":s["region"],"deform":s["deform"]}}
    children=[j+1 for j,p in enumerate(parent) if p==i]
    if children:node["children"]=children
    doc["nodes"].append(node)
doc["skins"]=[{"name":"SKEL_M25_VortexCoffer_V01","joints":list(range(1,B+1)),
    "skeleton":1,"inverseBindMatrices":append_array(
        rest_inverse.transpose(0,2,1).astype(np.float32).reshape(B,16),"MAT4",5126)}]
doc["scenes"]=[{"name":"M25_RigV01","nodes":[0,1]}];doc["scene"]=0

def core_shift(point,t,mode):
    x,y,z=point
    if mode=="Idle":
        phase=2*math.pi*t/4-z*.75
        return np.array([.003*x*math.sin(phase),.007*math.sin(phase),.003*math.cos(phase)])
    phase=2*math.pi*(t/PERIOD-z/3.6)
    return np.array([.032*x*math.cos(phase),.029*(1+math.cos(phase)),.060*math.sin(phase)])

def transformed_head(i,pose):
    p=parent[i]
    return (pose[p]@rest_inverse[p]@np.r_[spec[i]["head"],1.])[:3]

def poses(time,seconds,mode,root_motion):
    # Exact endpoint repetition is authored explicitly; root travel remains.
    t=0. if abs(time-seconds)<1e-7 else time
    pose=rest.copy()
    for i in centers:
        h=np.array(spec[i]["head"]);tail=np.array(spec[i]["tail"])
        pose[i,:3,3]=h+core_shift(h,t,mode)
        pose[i,:3,:3]=orient(tail+core_shift(tail,t,mode)-pose[i,:3,3])
    for row in lobes:
        for i in row:
            pose[i,:3,3]=np.array(spec[i]["head"])+core_shift(spec[i]["head"],t,mode)
            p=parent[i]
            pose[i,:3,:3]=pose[p,:3,:3]@rest[p,:3,:3].T@rest[i,:3,:3]

    for foot in feet:
        bi,mi,ti=foot["base"],foot["mid"],foot["tip"]
        base=np.array(spec[bi]["head"]);mid=np.array(spec[mi]["head"]);tip=np.array(spec[ti]["head"])
        ds=core_shift(base,t,mode)
        if mode=="Idle":
            # Tip support stays fixed; breathing dissipates through the web.
            bh=base+ds*.4;mh=mid+ds*.12;th=tip.copy();lift=0.
        else:
            p=(t/PERIOD-tip[2]/3.6+(.50 if tip[0]<0 else 0.))%1.
            stride=SPEED*PERIOD*DUTY
            if p<DUTY:
                shift=stride*(p/DUTY-.5);lift=0.
            else:
                q=(p-DUTY)/(1-DUTY)
                shift=stride*.5-stride*q+(SPEED*PERIOD/(2*math.pi))*math.sin(2*math.pi*q)
                lift=.072*math.sin(math.pi*q)**2
            # +Z is forward, so local support travels backwards during stance.
            th=tip+np.array([0.,lift,-shift])
            mh=mid+ds*.20+np.array([0.,lift*.60,-shift*.62])
            bh=base+ds*.65
        for idx,head,tail in [(bi,bh,mh),(mi,mh,th)]:
            pose[idx,:3,3]=head;pose[idx,:3,:3]=orient(tail-head)
        pose[ti,:3,3]=th
        tail=np.array(spec[ti]["tail"])-np.array(spec[ti]["head"])
        tail[1]+=lift*.28
        pose[ti,:3,:3]=orient(tail)

    for i in [mouth_id]+rings:
        pose[i,:3,3]=transformed_head(i,pose)
        p=parent[i]
        pose[i,:3,:3]=pose[p,:3,:3]@rest[p,:3,:3].T@rest[i,:3,:3]
        if i in rings:
            a=spec[i]["angle"];breath=.003*math.sin(2*math.pi*t/(4 if mode=="Idle" else PERIOD))
            pose[i,:3,3]+=np.array([math.cos(a)*breath,math.sin(a)*breath,0.])
    for i in poles:
        p=parent[i]
        pose[i,:3,3]=transformed_head(i,pose)
        pose[i,:3,:3]=pose[p,:3,:3]@rest[p,:3,:3].T@rest[i,:3,:3]
    for i,s in enumerate(spec):
        if s["region"]=="socket":
            p=parent[i];pose[i]=pose[p]@rest_inverse[p]@rest[i]
    if root_motion:pose[:,:3,3]+=np.array([0.,0.,SPEED*time])
    return pose

contracts=[
    dict(name="M25_Idle",seconds=4.,mode="Idle",root_motion=False,
         loop=True,intent="Small asynchronous sac breathing; resting tendril tips remain supported"),
    dict(name="M25_Crawl_InPlace",seconds=PERIOD,mode="Crawl",root_motion=False,
         loop=True,speed_m_s=SPEED,duty_factor=DUTY,
         intent="Posterior-to-anterior contraction wave, alternating perimeter traction and lifted recovery"),
    dict(name="M25_Crawl_RootMotion",seconds=PERIOD,mode="Crawl",root_motion=True,
         loop=True,speed_m_s=SPEED,root_distance_m=SPEED*PERIOD,duty_factor=DUTY,
         intent="Same crawl with +Z root travel; stance-tip translation cancels root travel"),
]
doc["animations"]=[]
for contract in contracts:
    count=round(contract["seconds"]*FPS)+1
    times=np.linspace(0,contract["seconds"],count,dtype=np.float32)
    translations=np.zeros((B,count,3),np.float32)
    rotations=np.zeros((B,count,4),np.float32)
    for f,t in enumerate(times):
        pose=poses(float(t),contract["seconds"],contract["mode"],contract["root_motion"])
        inv=np.linalg.inv(pose)
        for i in range(B):
            local=inv[parent[i]]@pose[i] if parent[i]>=0 else pose[i]
            translations[i,f]=local[:3,3]
            q=Rotation.from_matrix(local[:3,:3]).as_quat()
            if f and np.dot(q,rotations[i,f-1])<0:q=-q
            rotations[i,f]=q
    time_accessor=append_array(times,"SCALAR",5126)
    animation={"name":contract["name"],"samplers":[],"channels":[],"extras":contract}
    for i in range(B):
        for path,array,kind in [("translation",translations[i],"VEC3"),("rotation",rotations[i],"VEC4")]:
            sampler=len(animation["samplers"])
            animation["samplers"].append({"input":time_accessor,
                "output":append_array(array,kind,5126),"interpolation":"LINEAR"})
            animation["channels"].append({"sampler":sampler,"target":{"node":i+1,"path":path}})
    doc["animations"].append(animation)
    print("AUTHOR animation baked "+contract["name"],flush=True)
doc["buffers"]=[{"byteLength":len(binary)}]
doc["asset"]["generator"]="M25 original mesh preserved; fitted semantic skeleton and original peristaltic animation"
doc["extras"]={"source_file":str(INPUT),"forward_axis":"+Z","up_axis":"+Y",
    "length_m":4.1,"vertices":N,"triangles":6524740,"weights_per_vertex":4,
    "original_geometry_uv_normals_maps_retained":True,"tests_run":False,
    "ue_imported":False,"rig_version":"V01"}
data=json.dumps(doc,separators=(",",":")).encode("utf-8")
data+=b" "*((-len(data))%4)
binary+=b"\0"*((-len(binary))%4)
path=OUT/"M25_VortexCoffer_RigV01.glb"
with path.open("wb") as f:
    f.write(struct.pack("<4sII",b"glTF",2,12+8+len(data)+8+len(binary)))
    f.write(struct.pack("<II",len(data),0x4E4F534A));f.write(data)
    f.write(struct.pack("<II",len(binary),0x004E4942));f.write(binary)
(OUT/"animation_contract.json").write_text(json.dumps(contracts,indent=2),encoding="utf-8")
receipt={"rigged_glb":str(path),"source_archived":str(INPUT),"bones":B,
    "deform_bones":sum(s["deform"] for s in spec),"vertices":N,"triangles":6524740,
    "perimeter_chains":32,"rigid_electrodes":9,"weight_influences":4,
    "animations":contracts,"preserved":["source topology","UV","normals","PBR images","material"],
    "scale":META["scale_to_4_1m"],"dimensions_m":META["dimensions_m"],
    "tests_run":False,"renders_run":False,"ue_imported":False}
(OUT/"author_receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print("M25_RIG_AUTHORING_SAVED "+str(path),flush=True)
