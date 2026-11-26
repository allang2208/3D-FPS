"""Offline same-camera rear-quarter, side, and back views with the fitted collar."""
import ast
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).parent))
from helmet_nape_review import PROJECT, REVIEW, REVISIONS, SET as S, torso


def area(scene, target, name, offset, power, size):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power
    data.shape="DISK"
    data.size=size
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=target+Vector(offset)
    obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()


def render(rig,rev):
    bpy.ops.wm.open_mainfile(filepath=str(S/REVISIONS[rev]/"Models"/f"TS01_Helmet_{rig}_GAME.blend"))
    bpy.context.preferences.view.use_translate_new_dataname=False
    REVIEW.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    head=bpy.data.objects["REFERENCE_ONLY_"+rig]
    head.hide_render=False
    head.hide_set(False)
    clay=bpy.data.materials.new("Nape review reference skin")
    clay.use_nodes=True
    bs=next(n for n in clay.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value=(.32,.27,.23,1)
    bs.inputs["Roughness"].default_value=.81
    head.data.materials.clear()
    head.data.materials.append(clay)
    for face in head.data.polygons:
        face.use_smooth=True
    garment=torso(rig)
    top=max(v.co.z for v in head.data.vertices)
    # The image only reaches the upper chest; limit mesh creation to the visible area.
    f=np.asarray(garment["triangles"])
    p=garment["positions"]
    keep=p[f,2].max(1)>(top*100-48)
    garment.pop("normals",None)
    obj=mesh(garment,"Equipped fitted collar and carrier",keep)
    for i,name in enumerate(garment["material_slots"]):
        if name.startswith("NATIVE:"):
            obj.data.materials[i]=clay

    target=Vector((0,-.003,top-.143))
    cam=bpy.data.cameras.new("Rear coverage comparison camera")
    cam.type="ORTHO"
    cam.ortho_scale=.462
    cam.clip_start=.005
    eye=bpy.data.objects.new("Rear coverage comparison camera",cam)
    scene.collection.objects.link(eye)
    scene.camera=eye
    area(scene,target,"Large rear key",(-.48,.60,.65),28,.48)
    area(scene,target,"Side fill",(.42,.18,.24),15,.51)
    area(scene,target,"Front edge",(.15,-.47,.30),13,.33)
    world=bpy.data.worlds.new("Rear coverage studio")
    world.use_nodes=True
    bg=next(n for n in world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs[0].default_value=(.18,.20,.23,1)
    bg.inputs[1].default_value=.60
    scene.world=world
    scene.render.engine="CYCLES"
    scene.cycles.samples=16
    scene.cycles.use_denoising=True
    scene.render.resolution_x=496
    scene.render.resolution_y=492
    scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.view_settings.view_transform="AgX"
    scene.view_settings.exposure=0
    for angle,name in ((90,"side"),(137,"oblique"),(180,"rear")):
        a=math.radians(angle)
        eye.location=target+Vector((math.sin(a)*.75,-math.cos(a)*.75,.032))
        eye.rotation_euler=(target-eye.location).to_track_quat("-Z","Y").to_euler()
        scene.render.filepath=str(REVIEW/f"{rig}-{rev}-{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    source=PROJECT/"Tools/ModernTacticalSet/set_review_render.py"
    funcs=[n for n in ast.parse(source.read_text(encoding="utf-8")).body
           if isinstance(n,ast.FunctionDef) and n.name in {"material","mesh"}]
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(source),"exec"))
    render(*sys.argv[-2:])
