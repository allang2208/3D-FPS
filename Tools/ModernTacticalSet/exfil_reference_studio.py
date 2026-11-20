"""Photograph the actual game mesh and derive its physical inventory and pickup meshes."""
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix,Vector

P=Path(__file__).resolve().parents[2]
ROOT=P/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"
REVIEW=ROOT/"Review"
ICON=ROOT/"Icons"
KEY="ue_modern_tactical_helmet"
FLIP=np.array([1.,-1.,1.])


def write_json(path,data):
    path.write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def camera_in_scene(scene):
    cam=bpy.data.cameras.new("Reference camera");cam.type="ORTHO"
    eye=bpy.data.objects.new(cam.name,cam);scene.collection.objects.link(eye);scene.camera=eye
    return eye


def aim(camera,center,right,up,toward,span):
    rotation=Matrix(np.column_stack((right,up,toward)).tolist()).to_4x4()
    camera.matrix_world=Matrix.Translation(Vector(center+toward*.88))@rotation
    camera.data.ortho_scale=span


def illuminate(scene,center,right,up,toward,inside=False):
    for obj in list(scene.objects):
        if obj.type=="LIGHT":
            bpy.data.objects.remove(obj,do_unlink=True)
    def box(name,direction,power,radius,warm=(1,1,1)):
        bulb=bpy.data.lights.new(name,"AREA");bulb.energy=power;bulb.shape="DISK";bulb.size=radius;bulb.color=warm
        obj=bpy.data.objects.new(name,bulb);scene.collection.objects.link(obj)
        obj.location=Vector(center+direction)
        obj.rotation_euler=(Vector(center)-obj.location).to_track_quat("-Z","Y").to_euler()
    key=-toward*.13-right*.19+up*.50
    box("Crown key",key,10.2,.19,(1,.90,.70))
    box("Fill card",toward*.47+right*.36+up*.05,1.24,.54,(.82,.90,1))
    box("Rear strip",-toward*.27+right*.18+up*.39,7.7,.27,(1,.91,.72))
    box("Side return",toward*.25-right*.43+up*.04,1.92,.53,(.87,.92,1))
    if inside:
        box("Liner bounce",toward*.44,5.5,.39)


def still(scene,path,w,h,samples):
    scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
    scene.cycles.samples=samples;scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


def inventory(scene,eye,world_mesh,source):
    ICON.mkdir(exist_ok=True)
    eye.data.ortho_scale*=1.085
    still(scene,ICON/(KEY+".png"),320,320,48)
    bpy.ops.object.select_all(action="DESELECT")
    meshes=[o for o in scene.objects if o.type=="MESH" and not o.hide_render]
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join()
    mesh=bpy.context.view_layer.objects.active;bpy.context.view_layer.update()
    show=runpy.run_path(str(P/"Tools/FieldHat/render_icon.py"))
    exporter=show["export_display"];exporter.__globals__["OUT"]=ICON
    display=exporter(KEY,mesh,eye)
    data=json.loads(display.read_bytes())
    data["material_slots"]=[m.name.split(".")[0] for m in mesh.data.materials]
    points=np.array(data["positions"]);data["positions"]=(points-(points.min(0)+points.max(0))*.5).tolist()
    write_json(display,data)
    pickup=ROOT/"Authored/helmet_pickup.json"
    data=json.loads(world_mesh.read_bytes());points=np.array(data["positions"])
    data["positions"]=(points-(points.max(0)+points.min(0))*.5).tolist();write_json(pickup,data)
    if any(digest(ROOT/k)!=v for k,v in source.items()):
        raise RuntimeError("Game master changed during photography")
    write_json(ROOT/"artwork.json",dict(pickup=str(pickup),icon=dict(display=str(display),png=str(ICON/(KEY+".png")),resolution=[320,320]),source_sha256=source))


def render(mode):
    view=json.loads((REVIEW/"product-camera.json").read_bytes())
    master=ROOT/"Models/TS01_Helmet_Jason_GAME.blend"
    world_mesh=ROOT/"Authored/helmet_Jason_world.json"
    source={str(p.relative_to(ROOT)):digest(p) for p in (master,world_mesh)}
    if mode=="previous":master=Path(os.environ["TEMP"])/"EXFIL_before_crest.blend"
    bpy.ops.wm.open_mainfile(filepath=str(master))
    for ob in list(bpy.context.scene.objects):
        if ob.type in ("CAMERA","LIGHT") or ob.name.startswith("REFERENCE_ONLY_"):
            bpy.data.objects.remove(ob,do_unlink=True)
    for bitmap in bpy.data.images:
        tex=ROOT/"Textures"/Path(bitmap.filepath).name
        if tex.is_file():bitmap.filepath=str(tex);bitmap.reload()
    scene=bpy.context.scene;eye=camera_in_scene(scene)
    center=np.array(view["center"])*FLIP*.01
    right=np.array(view["right"])*FLIP;up=np.array(view["up"])*FLIP;toward=np.array(view["eye"])*FLIP
    span=view["vertical_cm"]*.01
    world=bpy.data.worlds.new("Low studio ambient");world.use_nodes=True
    bg=next(n for n in world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs["Color"].default_value=(.31,.32,.34,1);bg.inputs["Strength"].default_value=.16;scene.world=world
    scene.render.engine="CYCLES";scene.cycles.use_denoising=True
    scene.render.film_transparent=True;scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
    scene.view_settings.view_transform="AgX";scene.view_settings.look="AgX - Medium High Contrast";scene.view_settings.exposure=-.24
    aim(eye,center,right,up,toward,span);illuminate(scene,center,right,up,toward)
    w,h=view["pixel_size"]
    if mode in ("calibration","previous"):
        dest=REVIEW/"previous-crown.png" if mode=="previous" else Path(os.environ['TEMP'])/"exfil-light-calibration.png"
        mult=2 if mode=="previous" else 1
        still(scene,dest,w*mult,h*mult,32 if mode=="previous" else 18);return
    if mode=="hero":
        still(scene,REVIEW/"product-render.png",w*3,h*3,72)
        inventory(scene,eye,world_mesh,source);return
    points=np.array(json.loads(world_mesh.read_bytes())["positions"])*FLIP*.01
    origin=(points.min(0)+points.max(0))*.5
    for name,yaw,elevation in (("front",0,4),("side",-90,0),("rear",135,5),("liner",155,-66)):
        a,b=np.radians([yaw,elevation]);toward=np.array([np.sin(a)*np.cos(b),-np.cos(a)*np.cos(b),np.sin(b)])
        right=np.array([np.cos(a),np.sin(a),0]);up=np.cross(toward,right)
        horizontal=(points-origin)@right;vertical=(points-origin)@up
        center=origin+(horizontal.max()+horizontal.min())*.5*right+(vertical.max()+vertical.min())*.5*up
        span=max(np.ptp(horizontal),np.ptp(vertical))*1.12
        aim(eye,center,right,up,toward,span);illuminate(scene,center,right,up,toward,inside=name=="liner")
        still(scene,REVIEW/f"view-{name}.png",660,660,48)


if __name__=="__main__":
    render(sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'hero')
