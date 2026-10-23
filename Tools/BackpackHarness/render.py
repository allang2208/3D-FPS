"""Requested multi-view source render with current exported clothes and UVs."""
import json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

P=Path("D:/FPS3D/FPSGAME")
R=P/"SourceAssets/BackpackHarnessRebuild20261020"
profile=sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "knit_sweater"
posed="--posed" in sys.argv
manifest=json.loads((R/"manifest.json").read_text())
row=next(r for r in manifest["variants"] if r["profile"]==profile)
pack=json.loads((R/"PoseViews"/profile/"pack.json" if posed else Path(row["source"])).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True
    # Match the actual opaque single-sided UE materials, including the bag.
    m.use_backface_culling=True
    b=m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*color,1)
    b.inputs["Roughness"].default_value=.72
    return m


bag_mat=material("Original bag",(.25,.23,.15))
fabric=material("Woven harness",(.235,.225,.145))
hardware=material("Metal hardware",(.13,.15,.17))
hardware.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value=.9
hardware.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value=.3
for mat,path in [(bag_mat,P/"SourceAssets/BackpackMount20261002/T_SovietBackpack_BaseColor.png"),
                  (fabric,R/"Textures/T_HarnessFabric_BaseColor.png")]:
    tex=mat.node_tree.nodes.new("ShaderNodeTexImage");tex.image=bpy.data.images.load(str(path))
    mat.node_tree.links.new(tex.outputs["Color"],mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
normal=fabric.node_tree.nodes.new("ShaderNodeTexImage")
normal.image=bpy.data.images.load(str(R/"Textures/T_HarnessFabric_Normal_GL.png"))
normal.image.colorspace_settings.name="Non-Color"
normal_map=fabric.node_tree.nodes.new("ShaderNodeNormalMap")
fabric.node_tree.links.new(normal.outputs["Color"],normal_map.inputs["Color"])
fabric.node_tree.links.new(normal_map.outputs["Normal"],fabric.node_tree.nodes.get("Principled BSDF").inputs["Normal"])
body_mat=material("Body",(.37,.24,.17))
shirt_mat=material("Current garment",(.12,.16,.12) if profile!="mage_robe" else (.04,.12,.35))


def add(name,data,mats,filter_slots=False):
    v=np.asarray(data["positions"])*.01
    t=np.asarray(data["triangles"],int);ids=np.arange(len(t))
    if filter_slots:
        slots=[m["slot"].lower() for m in data["materials"]]
        keep=np.array([not any(x in s for x in ("exposed","inner","lining","proxy","neckseam")) for s in slots])
        ids=ids[keep[np.asarray(data["triangle_materials"])]]
    me=bpy.data.meshes.new(name);me.from_pydata(v.tolist(),[],t[ids].tolist());me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for mat in mats:me.materials.append(mat)
    for face,fi in zip(me.polygons,ids):
        face.material_index=int(data["triangle_materials"][fi]) if len(mats)>1 else 0
        face.use_smooth=True
    if "uv" in data:
        uv=me.uv_layers.new(name="UVMap")
        for face,fi in zip(me.polygons,ids):
            for loop,coord in zip(face.loop_indices,data["uv"][fi]):
                uv.data[loop].uv=(coord[0],1-coord[1])
    if "normals" in data:
        me.normals_split_custom_set([tuple(n) for fi in ids for n in data["normals"][fi]])
    return ob


add("Harness and bag",pack,[bag_mat,hardware,fabric])
add("Current body",json.loads((R/"PoseViews"/profile/"body.json" if posed else R/"Inputs/body.json").read_text()),[body_mat],True)
if row["shirt"]:
    add("Current clothing",json.loads((R/"PoseViews"/profile/"cloth.json" if posed else R/"Inputs"/(row["shirt"]+".json")).read_text()),[shirt_mat],True)
scene=bpy.context.scene;scene.render.engine="BLENDER_EEVEE"
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new("World");scene.world.use_nodes=True
scene.world.node_tree.nodes.get("Background").inputs[0].default_value=(.12,.12,.12,1)
scene.world.node_tree.nodes.get("Background").inputs[1].default_value=.65
for name,location,power,size in [("Key",(-2,2,3),450,3),("Rear",(1,-2,3),400,2),("Side",(2,1,1.5),250,2)]:
    light=bpy.data.lights.new(name,"AREA");light.energy=power;light.shape="DISK";light.size=size
    ob=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(ob);ob.location=location
    ob.rotation_euler=(Vector((0,0,1.25))-ob.location).to_track_quat("-Z","Y").to_euler()
camera=bpy.data.cameras.new("Camera");ob=bpy.data.objects.new("Camera",camera);bpy.context.collection.objects.link(ob)
scene.camera=ob;camera.type="ORTHO";camera.ortho_scale=.85
out=R/"Preview";out.mkdir(exist_ok=True)
for tag,location in [("back",(.65,-1.4,1.7)),("side",(1.6,.2,1.52)),("front",(.55,1.6,1.58))]:
    ob.location=location;ob.rotation_euler=(Vector((0,-.03,1.28))-ob.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(out/(profile+("_idle" if posed else "")+"_"+tag+".png"));bpy.ops.render.render(write_still=True)
    print("HARNESS_PREVIEW",scene.render.filepath,flush=True)
