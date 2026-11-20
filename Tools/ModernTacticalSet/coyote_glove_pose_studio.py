"""Photograph the saved equipped gloves in the captured M870 idle and reload poses."""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

if "--sheet" not in sys.argv:
    import bpy
    from mathutils import Matrix,Quaternion,Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_materials import ROOT,create

REVIEW=ROOT/"Review"
FLIP=np.array([.01,-.01,.01])


def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1.e-12)


def posed(d,names,pose):
    p=np.array(d["positions"])
    bones=d["bones"]
    if isinstance(bones,list):
        bones={b["name"]:b for b in bones}
    lookup={b["index"]:k for k,b in bones.items()}
    group={}
    side=np.zeros(len(p))
    for i,weights in enumerate(d["weights"]):
        pairs=weights.items() if isinstance(weights,dict) else [(lookup[idx],weight) for idx,weight in weights]
        for k,w in pairs:
            if w<=0:continue
            group.setdefault(k,[]).append((i,w))
            if k.endswith("_l"):side[i]+=w
    deformed=np.zeros_like(p);matrices=np.zeros((len(p),3,3))
    for k,items in group.items():
        idx,w=np.array(items).T;idx=idx.astype(int)
        m=pose[names.index(k)]
        b=bones[k]
        rot=m[:3,:3]@np.linalg.inv(np.asarray(b["axes"]).T)
        deformed[idx]+=(m[:3,3]+(p[idx]-b["position"])@rot.T)*w[:,None]
        matrices[idx]+=rot*w[:,None,None]
    f=np.array(d["triangles"])
    normal=np.array(d["normals"])
    normals=unit(np.einsum("fcj,fcji->fci",normal,np.linalg.inv(matrices)[f]))
    return deformed,normals,side>.5


def pose_matrices(data,clip,frame):
    local=data["clips"][clip]["local"][frame];names=data["names"]
    output=[]
    for t,parent in zip(local,data["parents"]):
        m=np.eye(4);m[:3,3]=t[:3]
        m[:3,:3]=np.array(Quaternion([t[6],*t[3:6]]).to_matrix())*t[7:]
        output.append(output[names.index(parent)]@m if parent in names else m)
    return np.asarray(output)


def thumb_patch_faces(d):
    from mathutils.kdtree import KDTree

    authored=json.loads((ROOT/"Authored/gloves_Super90.json").read_bytes())
    lo,hi=authored["parts"]["r_Thumb_lock_wrap"]
    patch=np.asarray(authored["positions"])[np.asarray(authored["triangles"])[lo:hi]]
    saved=np.asarray(d["positions"])[np.asarray(d["triangles"])]
    tree=KDTree(len(saved))
    for i,center in enumerate(saved.mean(1)):
        tree.insert(center,i)
    tree.balance()
    return np.unique([tree.find(center)[1] for center in patch.mean(1)])


def mesh(name,d,points,normals,include,materials):
    faces=np.array(d["triangles"])[include];me=bpy.data.meshes.new(name)
    vertices,indices=np.unique(faces,return_inverse=True)
    me.from_pydata((points[vertices]*FLIP).tolist(),[],indices.reshape(-1,3).tolist());me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob)
    for m in materials:me.materials.append(m)
    ids=np.array(d["triangle_materials"],np.int32)[include];me.polygons.foreach_set("material_index",ids)
    me.polygons.foreach_set("use_smooth",np.ones(len(faces),bool))
    direction=normals[include]*np.sign(FLIP)
    me.normals_split_custom_set(direction.reshape(-1,3).tolist())
    uv=np.asarray(d["uv"],np.float32)[include].copy();uv[:,:,1]=1-uv[:,:,1]
    me.uv_layers.new(name="SurfaceUV").data.foreach_set("uv",uv.reshape(-1))
    return ob


def shoot(clip,frame,sides,tag):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats=create()
    d=json.loads((REVIEW/"Read/Super90.json").read_bytes())
    with gzip.open(ROOT.parent/"NativeGloveR1/Read/M870_poses.json.gz","rt") as file:pose_data=json.load(file)
    pose=pose_matrices(pose_data,clip,frame);names=pose_data["names"]
    points,normals,left=posed(d,names,pose);faces=np.array(d["triangles"]);slots=d["material_slots"]
    scene=bpy.context.scene;scene.render.engine="CYCLES";scene.cycles.samples=40;scene.cycles.use_denoising=True
    scene.render.film_transparent=True
    scene.render.resolution_x=720;scene.render.resolution_y=580;scene.render.resolution_percentage=100
    scene.view_settings.view_transform="AgX";scene.view_settings.look="AgX - Medium High Contrast"
    scene.view_settings.exposure=-1.50
    scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
    world=bpy.data.worlds.new("Studio");world.use_nodes=True;scene.world=world
    bg=next(n for n in world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs[0].default_value=(.48,.48,.48,1);bg.inputs[1].default_value=.32
    closeups={}
    for side in sides:
        selected=left if side=="l" else ~left
        valid=selected[faces].all(1)
        bones=lambda b: pose[names.index(b+"_"+side),:3,3]*FLIP
        v=points[np.unique(faces[valid])]*FLIP
        longitudinal=unit(bones("middle_01")-bones("hand"));across=unit(bones("index_01")-bones("pinky_01"))
        dorsal=unit(np.cross(longitudinal,across))
        # Use the closure and knitted back to disambiguate mirrored axes.
        lbl=valid & (np.array(d["triangle_materials"])==slots.index("CG_Label"))
        front=unit(np.mean(normals[lbl],axis=(0,1))*np.sign(FLIP))
        if np.dot(dorsal,front)<0:dorsal=-dorsal
        outward=unit(dorsal+.70*across-.22*longitudinal)
        if tag=="reload":
            panel=thumb_patch_faces(d)
            posed_faces=points[faces[panel]]
            area=np.linalg.norm(np.cross(posed_faces[:,1]-posed_faces[:,0],posed_faces[:,2]-posed_faces[:,0]),axis=1)
            facing=unit(np.average(normals[panel].mean(1),axis=0,weights=area)*np.sign(FLIP))
            outward=unit(facing+.18*across)
            longitudinal=unit(bones("thumb_03")-bones("thumb_01"))
            thumb=np.array([sum(w for k,w in row.items() if k.startswith("thumb_") and k.endswith("_"+side)) for row in d["weights"]])
            v=points[thumb>.4]*FLIP
        up=unit(longitudinal-outward*np.dot(longitudinal,outward))
        right=unit(np.cross(up,outward));axes=np.column_stack((right,up,outward))
        proj=v@axes;center=(proj.min(0)+proj.max(0))*.5@axes.T
        span=max(np.ptp(proj[:,0]),np.ptp(proj[:,1])*720/580)*(1.32 if tag=="reload" else 1.12)
        closeups[side]=(mesh("Saved_Glove_"+side,d,points,normals,valid,[mats[k] for k in slots]),center,axes,span)
    camdata=bpy.data.cameras.new("Glove product camera");camdata.type="ORTHO";cam=bpy.data.objects.new(camdata.name,camdata)
    scene.collection.objects.link(cam);scene.camera=cam
    for side,(obj,center,axes,span) in closeups.items():
        for key,(other,*_) in closeups.items():other.hide_render=key!=side
        cam.matrix_world=Matrix.Translation(Vector(center+axes[:,2]*.75))@Matrix(axes.tolist()).to_4x4();camdata.ortho_scale=span
        for ob in list(scene.objects):
            if ob.type=="LIGHT":bpy.data.objects.remove(ob,do_unlink=True)
        for label,off,energy,size in (("Key",[-.20,.18,.32],7,.28),("Fill",[.27,-.1,.30],4,.37),("Rim",[.22,.26,-.12],5,.24)):
            data=bpy.data.lights.new(label,"AREA");data.energy=energy;data.shape="DISK";data.size=size
            light=bpy.data.objects.new(label,data);scene.collection.objects.link(light)
            light.location=Vector(center+axes@off);light.rotation_euler=(Vector(center)-light.location).to_track_quat("-Z","Y").to_euler()
        scene.render.filepath=str(REVIEW/f"M870-{tag}-{side}.png");bpy.ops.render.render(write_still=True)


def comparison():
    from PIL import Image, ImageDraw, ImageFont

    board=Image.new("RGB",(1536,482),(242,241,237))
    text=ImageDraw.Draw(board)
    title=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",25)
    for i,(view,label) in enumerate((("idle-l","待机 · 左手"),("idle-r","待机 · 右手"),("reload-r","换弹 · 右手拇指"))):
        glove=Image.open(REVIEW/f"M870-{view}.png").convert("RGBA")
        glove.thumbnail((512,424),Image.Resampling.LANCZOS)
        board.paste(glove,(i*512+(512-glove.width)//2,56),glove)
        text.text((22+i*512,16),label,font=title,fill=(57,52,43))
    board.save(REVIEW/"M870-hand-poses.jpg",quality=93,optimize=True)


if __name__=="__main__":
    if "--sheet" in sys.argv:
        comparison()
    else:
        if "--thumb-only" not in sys.argv:
            shoot("A_M870_idle",0,("l","r"),"idle")
        shoot("A_M870_reload_full",71,("r",),"reload")
