"""Photograph the game meshes. Derive both inventory representations from the same arrangement."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix,Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_art import ROOT, MODEL, unit

REVIEW=ROOT/"Review"
ICON=ROOT/"Icons"
KEY="ue_modern_tactical_gloves"


def prepare():
    bpy.ops.wm.open_mainfile(filepath=str(MODEL/"SK_TS01_CoyoteGloves_GAME.blend"))
    hands={}
    for ob in list(bpy.context.scene.objects):
        if ob.type!="MESH":continue
        if not ob.get("studio_side"):continue
        side=ob["studio_side"];hands[side]=ob
        ob.parent=None
        for mod in list(ob.modifiers):ob.modifiers.remove(mod)
        ob.matrix_world=Matrix.Identity(4)
        offset=Vector(ob["studio_offset_cm"])*.01
        ob.data.transform(Matrix.Translation(-offset))
    scene=bpy.context.scene
    cam=bpy.data.cameras.new("Product camera");cam.type="ORTHO";cam.clip_start=.001
    view=bpy.data.objects.new(cam.name,cam);scene.collection.objects.link(view);scene.camera=view
    scene.render.engine="CYCLES";scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.view_settings.view_transform="AgX";scene.view_settings.look="AgX - Medium High Contrast"
    scene.view_settings.exposure=-1.82;scene.render.film_transparent=True
    scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
    world=bpy.data.worlds.new("Soft studio surroundings");world.use_nodes=True
    bg=next(n for n in world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs[0].default_value=(.55,.60,.65,1);bg.inputs[1].default_value=.43;scene.world=world
    return hands,view,scene


def pose(ob,at,rz,ry,rx):
    affine=Matrix.Translation(Vector(at)*.01)
    for axis,angle in [('Z',rz),('Y',ry),('X',rx)]:affine=affine@Matrix.Rotation(math.radians(angle),4,axis)
    ob.matrix_world=affine


def points(ob):
    local=np.empty(len(ob.data.vertices)*3,np.float32)
    ob.data.vertices.foreach_get("co",local)
    m=np.array(ob.matrix_world)
    return local.reshape(-1,3)@m[:3,:3].T+m[:3,3]


def lighting(scene,center):
    for ob in list(scene.objects):
        if ob.type=="LIGHT":bpy.data.objects.remove(ob,do_unlink=True)
    def area(name,p,d,size,color):
        bulb=bpy.data.lights.new(name,"AREA");bulb.energy=p;bulb.shape="DISK";bulb.size=size;bulb.color=color
        ob=bpy.data.objects.new(name,bulb);scene.collection.objects.link(ob);ob.location=Vector(center)+Vector(d)
        ob.rotation_euler=(Vector(center)-ob.location).to_track_quat("-Z","Y").to_euler()
    area("Broad fabric key",9.5,(-.29,.33,.42),.28,(1.,.97,.92))
    area("Palm fill",4.7,(.28,-.17,.34),.4,(.92,.96,1.))
    area("Edge strip",5.8,(.35,.24,.16),.24,(1.,.98,.93))


def photo(hands,view,scene,file,width,height,pad=1.10,toward=(0,0,1)):
    span=np.concatenate([points(ob) for ob in hands if not ob.hide_render])
    toward=unit(np.array(toward,dtype=float))
    right=unit(np.cross([0,1,0],toward))
    up=np.cross(toward,right)
    axis=np.array([right,up,toward]);local=span@axis.T
    center=(local.min(0)+local.max(0))*.5@axis
    view.matrix_world=Matrix.Translation(Vector(center+toward*.7))@Matrix(axis.T.tolist()).to_4x4()
    size=local.max(0)-local.min(0)
    view.data.ortho_scale=max(size[0]/min(1.,width/height),size[1]/min(1.,height/width))*pad
    lighting(scene,center)
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100
    scene.render.filepath=str(file);bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    return axis


def export(objs,axis,file):
    slots=[];p=[];faces=[];normals=[];uv=[];ids=[];count=0
    for ob in objs:
        me=ob.data;me.calc_loop_triangles()
        local_slots=[]
        for mat in me.materials:
            name=mat.name.split(".")[0]
            if name not in slots:slots.append(name)
            local_slots.append(slots.index(name))
        world=points(ob)
        p.extend((world@axis.T*100).tolist())
        convert=axis@np.linalg.inv(np.array(ob.matrix_world)[:3,:3]).T
        for tri in me.loop_triangles:
            faces.append([count+v for v in tri.vertices])
            ids.append(local_slots[tri.material_index])
            normals.append([unit(convert@np.array(me.corner_normals[i].vector)).tolist() for i in tri.loops])
            tex=[me.uv_layers.active.data[i].uv for i in tri.loops]
            uv.append([[x,1.-y] for x,y in tex])
        count+=len(world)
    geom=np.array(p);p=(geom-(geom.min(0)+geom.max(0))*.5).tolist()
    file.write_text(json.dumps(dict(positions=p,triangles=faces,normals=normals,uv=uv,
                                    triangle_materials=ids,material_slots=slots),separators=(",",":")))


def shoot(mode):
    for dest in (ICON,REVIEW):dest.mkdir(parents=True,exist_ok=True)
    hands,view,scene=prepare();left=hands["l"];right=hands["r"]
    if mode in ("back","palm"):
        primary=right if mode=="back" else left
        mate=right if primary==left else left;mate.hide_render=True
        flip=180 if primary["dorsal_facing_z"]<0 else 0
        if mode=="back":
            pose(primary,(0,0,0),161,8+flip,21)
        else:
            pose(primary,(0,0,0),-9,174+flip,3)
        photo([primary],view,scene,REVIEW/(mode+".png"),780,900,1.10)
        return
    left.hide_render=True
    flip=180 if right["dorsal_facing_z"]<0 else 0
    pose(right,(0,0,0),-12,flip-12,8)
    axis=photo([right],view,scene,ICON/(KEY+".png"),320,320,1./.91,toward=(.06,-.15,1.))
    pickup=ICON/"gloves_pickup.json";display=ICON/"gloves_display.json"
    export([right],np.diag([1.,-1.,1.]),pickup)
    export([right],np.stack((-axis[2],axis[0],axis[1])),display)
    model=json.loads((MODEL/"models.json").read_bytes())
    src=ROOT/model["photographic_source"]
    source_sha=model["photographic_source_sha256"]
    if hashlib.sha256(src.read_bytes()).hexdigest()!=source_sha:
        raise RuntimeError("Source changed during the studio export")
    receipt=dict(source=src.relative_to(ROOT).as_posix(),source_sha256=source_sha,
              standard_icon=(ICON/(KEY+".png")).relative_to(ROOT).as_posix(),
              display=display.relative_to(ROOT).as_posix(),pickup=pickup.relative_to(ROOT).as_posix(),
              single_empty_right_glove=True,fill_target=.91)
    (ROOT/"artwork.json").write_text(json.dumps(receipt,indent=2))


if __name__=="__main__":
    shoot(sys.argv[sys.argv.index("--")+1])
