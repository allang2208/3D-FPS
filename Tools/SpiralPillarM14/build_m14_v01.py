"""M14 source-preserving semantic parts, dedicated rig and original animation authoring.
No renderer or game tests. Source GLB remains untouched.
"""
from pathlib import Path
import json, struct, math, bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004")
OUT=ROOT/"ProductionV01"
for folder in ["Authoring","Exports","Records"]: (OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/"Authoring/M14_Meshy_Source_v01.blend"))
source=next(o for o in bpy.context.scene.objects if o.type=="MESH")
material=source.data.materials[0]
n=len(source.data.vertices)
p=np.empty(n*3,np.float32);source.data.vertices.foreach_get("co",p);p=p.reshape(-1,3)
# glTF +Y up -> Blender +Z; mesh positions have already undergone this conversion.
raw=np.stack([p[:,0],p[:,2],-p[:,1]],axis=1).copy()
lo=raw.min(0);hi=raw.max(0);factor=3./float(hi[1]-lo[1])
p[:,0]*=factor;p[:,1]*=factor;p[:,2]=(p[:,2]-lo[1])*factor
nf=len(source.data.polygons);f=np.empty(nf*3,np.int32);source.data.loops.foreach_get("vertex_index",f);f=f.reshape(-1,3)
uv=np.empty(len(source.data.loops)*2,np.float32);source.data.uv_layers.active.data.foreach_get("uv",uv);uv=uv.reshape(-1,2)
norm=np.empty(len(source.data.corner_normals)*3,np.float32);source.data.corner_normals.foreach_get("vector",norm);norm=norm.reshape(-1,3)
x,h,d=raw.T
# Sample material identity in original UV space, not by cutting arbitrary connected islands.
image=next(i for i in bpy.data.images if i.name=="Image_1")
pix=np.empty(image.size[0]*image.size[1]*4,np.float32);image.pixels.foreach_get(pix);pix=pix.reshape(image.size[1],image.size[0],4)
uvv=np.zeros((n,2),np.float32);uvv[f.ravel()]=uv
ix=np.clip((uvv[:,0]*image.size[0]).astype(int),0,image.size[0]-1)
iy=np.clip((uvv[:,1]*image.size[1]).astype(int),0,image.size[1]-1)
metal=pix[iy,ix,2]>.46
# Visible source faces are partitioned; continuous seams use one global skin solution.
names=["Body_RootSkirt","Maw","Teeth","Membrane_L","Membrane_R","Sac_L","Sac_R","Restraint","Chains"]
c=raw[f].mean(1);cx,ch,cd=c.T
mouth_r=np.sqrt((cx/.17)**2+((ch+.455)/.19)**2)
labels=np.zeros(nf,np.int16)
mouth=(mouth_r<1)&(cd>.145)&(ch<-.23)
labels[mouth]=1
# Radial tooth faces lie on the inner lip band, with steep inward-facing surfaces.
cn=norm.reshape(-1,3,3).mean(1)
radial=np.stack([cx,np.zeros_like(cx),ch+.455],axis=1)
radial/=np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),1e-7)
inward=np.sum(cn*radial,axis=1)<-.18
labels[mouth&(mouth_r>.42)&(mouth_r<.88)&inward]=2
for side,sign in [("L",1),("R",-1)]:
    j=0 if side=="L" else 1
    side_region=(cx*sign>.24)&(ch>-.53)&(ch<.65)
    labels[side_region]=3+j
    sac=((cx-sign*.395)/.135)**2+((ch+.225)/.255)**2+((cd-.015)/.22)**2<1
    labels[side_region&sac]=5+j
face_metal=metal[f].sum(1)>=2
labels[face_metal]=8
labels[face_metal&(ch>.16)&(ch<.47)&(abs(cx)<.30)]=7
# Bone coordinates in Blender metres, +Z up, front -Y.
bones=[]
def add(name,head,tail,parent=None,group="Body"):
    bones.append(dict(name=name,head=list(head),tail=list(tail),parent=parent,group=group))
add("root",(0,0,0),(0,0,.18),None,"Root")
add("base",(0,0,.20),(0,0,.55),"root")
zs=[.55,1.05,1.55,2.05,2.55,3.]
for k in range(5): add(f"spine_{k+1:02d}",(0,0,zs[k]),(0,0,zs[k+1]),"base" if k==0 else f"spine_{k:02d}")
def world(v): return np.array([v[0]*factor,-v[2]*factor,(v[1]-lo[1])*factor])
mouth_center=world([0,-.455,.235])
add("maw",mouth_center,mouth_center+[0,-.22,0],"spine_01","Mouth")
add("mouth_socket",mouth_center+[0,-.09,0],mouth_center+[0,-.15,0],"maw","Mouth")
for k in range(8):
    a=2*math.pi*k/8
    q=mouth_center+np.array([math.cos(a)*.19,-.015,math.sin(a)*.22])
    add(f"jaw_{k:02d}",q,q+[0,-.06,0],"maw","Mouth")
for k in range(8):
    a=2*math.pi*k/8
    q=np.array([math.cos(a),math.sin(a),0.])
    add(f"rootfan_{k:02d}",q*.20+[0,0,.27],q*.62+[0,0,.12],"base","Roots")
    add(f"roottoe_{k:02d}",q*.62+[0,0,.12],q*1.08+[0,0,.035],f"rootfan_{k:02d}","Roots")
for side,sign in [("L",1),("R",-1)]:
    chain=[world([sign*.15,.66,.0]),world([sign*.29,.30,.005]),world([sign*.40,-.01,.015]),world([sign*.41,-.36,.02])]
    for k in range(3):
        add(f"mem_{side}_{k}",chain[k],chain[k+1],"spine_04" if k==0 else f"mem_{side}_{k-1}","Membranes")
    sac=world([sign*.405,-.255,.015])
    add(f"sac_{side}",sac+[0,0,.18],sac+[0,0,-.22],f"mem_{side}_1","Sacs")
    for k in range(3):
        add(f"chain_{side}_{k}",chain[k]+[sign*.028,0,0],chain[k+1]+[sign*.028,0,0],
            "spine_04" if k==0 else f"chain_{side}_{k-1}","Metal")
add("restraint",(0,0,2.03),(0,0,2.17),"spine_04","Metal")
index={b["name"]:i for i,b in enumerate(bones)}
def smooth(v):
    t=np.clip(v,0,1);return t*t*(3-2*t)
# Shared vertex weights are computed once before cutting the mesh.
W=np.zeros((n,len(bones)),np.float32)
body_z=np.array([.20,.75,1.3,1.8,2.3,2.8])
body_names=["base"]+[f"spine_{k:02d}" for k in range(1,6)]
z=p[:,2]
for k,name in enumerate(body_names):
    left=body_z[k-1] if k else body_z[k]-.65
    right=body_z[k+1] if k+1<len(body_z) else 3.3
    W[:,index[name]]=np.where(z<body_z[k],smooth((z-left)/(body_z[k]-left)),1-smooth((z-body_z[k])/(right-body_z[k])))
W/=np.maximum(W.sum(1,keepdims=True),1e-8)
def mix(targets,amount):
    W[:]*=(1-amount[:,None])
    for name,weights in targets.items(): W[:,index[name]]+=weights*amount
# Root fan, anchored distally to the ground; adjacent fans blend continuously.
angle=np.mod(np.arctan2(p[:,1],p[:,0]),2*math.pi)*8/(2*math.pi)
a0=np.floor(angle).astype(int)%8;frac=angle-np.floor(angle)
radius=np.linalg.norm(p[:,:2],axis=1)
root_amount=(1-smooth((z-.06)/.45))*smooth(radius/.32)
root_targets={}
toe=smooth((radius-.36)/.46)
for k in range(8):
    angular=np.where(a0==k,1-frac,np.where((a0+1)%8==k,frac,0))
    root_targets[f"rootfan_{k:02d}"]=angular*(1-toe)
    root_targets[f"roottoe_{k:02d}"]=angular*toe
mix(root_targets,root_amount)
# Mouth mask blends through the surrounding tissue; no cut lip and body seam.
mr=np.sqrt((x/.22)**2+((h+.455)/.23)**2)
amount=(1-smooth((mr-.65)/.6))*smooth((d-.10)/.08)
ma=np.mod(np.arctan2(h+.455,x),2*math.pi)*8/(2*math.pi)
m0=np.floor(ma).astype(int)%8;mf=ma-np.floor(ma)
ring=smooth((mr-.23)/.25)*.90
target={"maw":1-ring}
for k in range(8):target[f"jaw_{k:02d}"]=ring*np.where(m0==k,1-mf,np.where((m0+1)%8==k,mf,0))
mix(target,amount)
# Broad lateral organs derive from the same bounded envelopes as their source faces.
for side,sign in [("L",1),("R",-1)]:
    outside=smooth((x*sign-.18)/.14)*smooth((h+.60)/.15)*(1-smooth((h-.48)/.20))
    hs=np.array([.51,.17,-.18])
    dif=(h[:,None]-hs[None,:])/.27
    weights=np.exp(-dif*dif*2);weights/=weights.sum(1,keepdims=True)
    mix({f"mem_{side}_{k}":weights[:,k] for k in range(3)},outside)
    sr=((x-sign*.395)/.135)**2+((h+.225)/.255)**2+((d-.015)/.22)**2
    sac_amount=(1-smooth((sr-.30)/.85))*outside
    mix({f"sac_{side}":np.ones(n,np.float32)},sac_amount)
# Hold the restraint as a rigid island; chains use the adjacent limited motion field.
band=metal&(h>.16)&(h<.47)&(abs(x)<.30)
mix({"restraint":np.ones(n,np.float32)},band.astype(np.float32))
for side,sign in [("L",1),("R",-1)]:
    amt=(metal&(x*sign>0)&~band).astype(np.float32)
    t=np.clip((.65-h)/1.25*3,0,2)
    ids=np.floor(t).astype(int);fpart=t-ids
    target={}
    for k in range(3):target[f"chain_{side}_{k}"]=np.where(ids==k,1-fpart,np.where(np.minimum(ids+1,2)==k,fpart,0))
    mix(target,amt)
# UV-split duplicates share weights, preventing seam jumps after export.
quant=np.round(p*1000000).astype(np.int64)
_,first,inverse=np.unique(quant,axis=0,return_index=True,return_inverse=True)
W=W[first][inverse]
bi=np.argsort(W,axis=1)[:,-4:][:,::-1].astype(np.int16)
wi=np.take_along_axis(W,bi,axis=1);wi/=np.maximum(wi.sum(1,keepdims=True),1e-8)
qw=np.round(wi*1024).astype(np.int32);qw[:,0]+=1024-qw.sum(1)
del W,pix,quant
bpy.data.objects.remove(source,do_unlink=True)
ad=bpy.data.armatures.new("M14_Skeleton");rig=bpy.data.objects.new("M14_Rig",ad);bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for entry in bones:
    eb=ad.edit_bones.new(entry["name"]);eb.head=entry["head"];eb.tail=entry["tail"]
    if entry["parent"]:eb.parent=ad.edit_bones[entry["parent"]]
    axis=(eb.tail-eb.head).normalized();eb.align_roll(Vector((0,-1,0)) if abs(axis.y)<.95 else Vector((0,0,1)))
bpy.ops.object.mode_set(mode="OBJECT")
groups={}
for b in bones:
    groups.setdefault(b["group"],ad.collections.get(b["group"]) or ad.collections.new(b["group"])).assign(ad.bones[b["name"]])
    ad.bones[b["name"]].inherit_scale="NONE"
    rig.pose.bones[b["name"]].rotation_mode="QUATERNION"
objects=[];parts=[]
materials={}
for family in ['Body','Mouth','Membrane','Metal']:
    materials[family]=material.copy();materials[family].name='M14_'+family
for label,name in enumerate(names):
    face_ids=np.flatnonzero(labels==label)
    if not len(face_ids):continue
    faces=f[face_ids];verts,remap=np.unique(faces.ravel(),return_inverse=True)
    mesh=bpy.data.meshes.new("M14_"+name);mesh.vertices.add(len(verts));mesh.vertices.foreach_set("co",p[verts].ravel())
    mesh.loops.add(len(remap));mesh.loops.foreach_set("vertex_index",remap)
    mesh.polygons.add(len(face_ids));mesh.polygons.foreach_set("loop_start",np.arange(len(face_ids),dtype=np.int32)*3)
    mesh.polygons.foreach_set("loop_total",np.full(len(face_ids),3,np.int32))
    mesh.polygons.foreach_set("use_smooth",np.ones(len(face_ids),bool))
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv",uv.reshape(-1,3,2)[face_ids].ravel())
    mesh.update();mesh.normals_split_custom_set(norm.reshape(-1,3,3)[face_ids].reshape(-1,3))
    family='Metal' if label in (7,8) else 'Membrane' if label in (3,4) else 'Mouth' if label in (1,2) else 'Body'
    mesh.materials.append(materials[family])
    ob=bpy.data.objects.new("M14_"+name,mesh);bpy.context.scene.collection.objects.link(ob)
    boneids=bi[verts].ravel();q=qw[verts].ravel();vid=np.repeat(np.arange(len(verts),dtype=np.int32),4)
    keep=q>0;key=boneids[keep].astype(np.int32)*2048+q[keep];vid=vid[keep]
    order=np.argsort(key);key=key[order];vid=vid[order];values,starts=np.unique(key,return_index=True);ends=np.r_[starts[1:],len(key)]
    vgs={}
    for val,start,end in zip(values,starts,ends):
        bn=int(val//2048);vg=vgs.setdefault(bn,ob.vertex_groups.get(bones[bn]["name"]) or ob.vertex_groups.new(name=bones[bn]["name"]))
        vg.add(vid[start:end].tolist(),float(val%2048)/1024,"REPLACE")
    ob.parent=rig;mod=ob.modifiers.new("M14_Skin","ARMATURE");mod.object=rig
    ob["source_face_preserved"]=True;ob["split_note"]="Shared seam weights; visual production partition, not detachable organs."
    objects.append(ob);parts.append(dict(name=ob.name,source_triangles=len(face_ids),vertices=len(verts)))
    print("M14_PART_SAVED",name,len(face_ids),flush=True)
scene=bpy.context.scene;scene.render.fps=30;scene.unit_settings.system="METRIC";scene.unit_settings.scale_length=1
rig["source_height_m"]=float(hi[1]-lo[1]);rig["height_m"]=3.;rig["source_scale"]=factor
def reset():
    for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
def turn(name,axis,radians):
    pb=rig.pose.bones[name];local=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    pb.rotation_quaternion=Quaternion(local,radians) @ pb.rotation_quaternion
def shift(name,delta):
    pb=rig.pose.bones[name];pb.location=pb.bone.matrix_local.to_3x3().inverted()@Vector(delta)
def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def pulse(t,a,b,c):
    return ease((t-a)/(b-a)) if t<b else 1-ease((t-b)/(c-b))
durations={"Idle":4.0,"Move":2.4,"TurnLeft":2.4,"TurnRight":2.4,"Bite":1.9,"Hit":.7,"Death":3.0}
clips={}
# Export neutral bind before actions.
bpy.ops.object.select_all(action="DESELECT");rig.select_set(True)
for ob in objects:ob.select_set(True)
fbx_settings=dict(use_selection=True,apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",axis_forward="-Z",axis_up="Y",add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype="NULL",path_mode="STRIP",use_mesh_modifiers=False)
bpy.ops.export_scene.fbx(filepath=str(OUT/"Exports/M14_Skeletal_v01.fbx"),object_types={"ARMATURE","MESH"},bake_anim=False,mesh_smooth_type="FACE",**fbx_settings)
for role,duration in durations.items():
    rig.animation_data_create();action=bpy.data.actions.new("A_M14_"+role);action.use_fake_user=True;rig.animation_data.action=action
    frames=round(duration*30);scene.frame_start=0;scene.frame_end=frames
    for frame in range(frames+1):
        t=frame/30.;reset()
        cycle=2*math.pi*t/duration
        # Soft hanging components: low amplitudes, fixed roots and delayed tips.
        for side,sign in [("L",1),("R",-1)]:
            for k in range(3):
                turn(f"mem_{side}_{k}",(0,1,0),sign*.025*math.sin(cycle-k*.6))
                turn(f"chain_{side}_{k}",(0,1,0),sign*.010*math.sin(cycle-k*.4))
            turn(f"sac_{side}",(1,0,0),.035*math.sin(cycle-.6+sign*.2))
        if role=="Idle":
            for k in range(1,6):
                turn(f"spine_{k:02d}",(0,1,0),.010*math.sin(cycle-k*.5))
            for side in ["L","R"]:rig.pose.bones[f"sac_{side}"].scale=(1+.018*math.sin(cycle),1,1+.012*math.sin(cycle))
        elif role in ("Move","TurnLeft","TurnRight"):
            shift("base",(.015*math.sin(cycle),0,.007*(1-math.cos(2*cycle))))
            for k in range(1,6):
                turn(f"spine_{k:02d}",(0,0,1),.018*math.sin(cycle-k*.5))
            for k in range(8):
                ph=(t/duration+(k%2)*.5)%1.;duty=.65;stroke=.28*duration*duty
                if ph<duty:forward=stroke*(.5-ph/duty);lift=0.
                else:
                    q=(ph-duty)/(1-duty);forward=stroke*(-.5+ease(q));lift=.065*math.sin(math.pi*q)**2
                delta=np.array([0,-forward,lift])
                if role!="Move":
                    sign=1 if role=="TurnLeft" else -1
                    a=2*math.pi*k/8;delta=np.array([-math.sin(a),math.cos(a),0])*forward*sign+np.array([0,0,lift])
                shift(f"roottoe_{k:02d}",delta);shift(f"rootfan_{k:02d}",delta*.25)
        elif role=="Bite":
            wind=pulse(t,0,.55,1.9);strike=pulse(t,.55,.86,1.35)
            for k in range(1,6):
                turn(f"spine_{k:02d}",(0,0,1),.06*wind*((-1)**k))
                turn(f"spine_{k:02d}",(1,0,0),-.022*wind if k>2 else .030*strike)
            shift("maw",(0,.045*wind-.34*strike,.025*strike))
            gape=pulse(t,.08,.58,1.1)
            for k in range(8):
                a=2*math.pi*k/8;shift(f"jaw_{k:02d}",(math.cos(a)*.032*gape,-.01*gape,math.sin(a)*.040*gape))
            for side in ["L","R"]:rig.pose.bones[f"sac_{side}"].scale=(1-.035*wind,1,1+.025*wind)
        elif role=="Hit":
            hit=pulse(t,0,.12,.7)
            for k in range(1,6):turn(f"spine_{k:02d}",(1,0,0),-.05*hit)
            shift("maw",(0,.04*hit,0))
        elif role=="Death":
            collapse=ease((t-.15)/1.85)
            turn("base",(1,0,0),-1.25*collapse)
            shift("base",(0,.32*collapse,-.10*collapse))
            for k in range(1,6):turn(f"spine_{k:02d}",(1,0,0),-.09*collapse)
            for side,sign in [("L",1),("R",-1)]:
                turn(f"sac_{side}",(0,1,0),sign*.18*collapse)
                for k in range(3):turn(f"mem_{side}_{k}",(0,1,0),sign*.10*collapse)
            for k in range(8):shift(f"roottoe_{k:02d}",(0,0,.015*collapse))
        for pb in rig.pose.bones:
            pb.keyframe_insert("location",frame=frame,group=pb.name)
            pb.keyframe_insert("rotation_quaternion",frame=frame,group=pb.name)
            pb.keyframe_insert("scale",frame=frame,group=pb.name)
    # Linear sampled channels keep the authored clock, without spline overshoot.
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag=strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation="LINEAR"
    bpy.ops.object.select_all(action="DESELECT");rig.select_set(True)
    filename=OUT/f"Exports/A_M14_{role}.fbx"
    bpy.ops.export_scene.fbx(filepath=str(filename),object_types={"ARMATURE"},bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.,**fbx_settings)
    clips[role]=dict(file=str(filename),duration_seconds=duration,loop=role in ("Idle","Move","TurnLeft","TurnRight"))
    print("M14_ANIMATION",role,flush=True)
rig.animation_data.action=None;reset();scene.frame_set(0)
bpy.ops.object.select_all(action="DESELECT");rig.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Authoring/M14_Rigged_Animated_v01.blend"),compress=True)
recipe=dict(source=str(ROOT/"Authoring/M14_Meshy_Source_v01.blend"),height_m=3.,source_triangles=nf,parts=parts,bones=bones,clips=clips,
    animation_walk_speed_cm_s=28.,bite_contact_seconds=.86,bite_seconds=1.9,death_seconds=3.,
    policy="Original visible faces, UV and corner normals retained. Global four-influence weights shared at duplicated positions. No automatic decimation.",
    separation="Surface partition; seams remain attached. No independently detachable organ claims.",
    tested=False,rendered=False)
(OUT/"Records/production_recipe.json").write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("M14_AUTHORING_COMPLETE",len(bones),nf,flush=True)
