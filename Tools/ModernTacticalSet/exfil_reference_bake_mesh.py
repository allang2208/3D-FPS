"""Read the delivery masters for baking, and write an independent one-material game asset."""
import json
import os
from pathlib import Path
import sys

import bpy
import numpy as np

PROJECT=Path(__file__).resolve().parents[2]
ROOT=PROJECT/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"
BAKES=ROOT/"Bakes"
CACHE=Path(os.environ["TEMP"])/"ts01_exfil_reference_bakes"
SLOTS=("Composite","Polymer","Rubber","Webbing","LoopPile","PadMesh","Metal","Label","Stitch","DarkPolymer")


def prop(group,name,n,dtype):
    arr=np.empty(len(group)*n,dtype=dtype)
    group.foreach_get(name,arr)
    return arr.reshape(-1,n) if n!=1 else arr


def norm(v):
    return v/np.maximum(1.e-12,np.linalg.norm(v,axis=-1,keepdims=True))


def extract(rig,stage):
    path=ROOT/"Models"/f"TS01_Helmet_{rig}_{stage}.blend"
    bpy.ops.wm.open_mainfile(filepath=str(path))
    manifest=json.loads((ROOT/"Authored"/f"parts-{rig}-{stage}.json").read_bytes())["parts"]
    result={k:[] for k in ("p","f","cn","uv","mat","tan","sign","group")}
    names=[];offset=0
    for name in manifest:
        ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles()
        transform=np.array(ob.matrix_world)
        pts=prop(me.vertices,"co",3,np.float32)@transform[:3,:3].T+transform[:3,3]
        ids=prop(me.loop_triangles,"vertices",3,np.int32)
        ci=prop(me.loop_triangles,"loops",3,np.int32)
        # Match the original game writer's degenerate-face filtering exactly.
        poly=prop(me.vertices,"co",3,np.float32).astype(np.float64)[ids]
        cross=np.cross(poly[:,1]-poly[:,0],poly[:,2]-poly[:,0])
        valid=(cross*cross).sum(1)>1.e-26
        ids=ids[valid];ci=ci[valid]
        ns=norm(prop(me.corner_normals,"vector",3,np.float32)@np.linalg.inv(transform[:3,:3]))
        if stage=="GAME":
            layer=me.uv_layers.active
            result["uv"].append(prop(layer.data,"uv",2,np.float32)[ci])
            lut=np.array([SLOTS.index(m.name.removeprefix("H1_").split(".")[0]) for m in me.materials],dtype=np.uint8)
            result["mat"].append(lut[prop(me.loop_triangles,"material_index",1,np.int32)[valid]])
        result["p"].append(pts.astype(np.float32)*100)
        result["f"].append(ids+offset);offset+=len(pts)
        result["cn"].append(ns[ci].astype(np.float32))
        result["group"].append(np.full(len(ids),len(names),dtype=np.int16));names.append(name)
    data={k:np.concatenate(v).astype(np.float32 if k in ("p","cn","tan","sign","uv") else v[0].dtype) for k,v in result.items() if v}
    data["names"]=np.array(names)
    CACHE.mkdir(parents=True,exist_ok=True)
    np.savez(CACHE/f"{rig}-{stage}.npz",**data)
    print("BAKE_INPUT",stage,rig,len(names),len(data["f"]),flush=True)


def build(rig,write_asset):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    inp=np.load(CACHE/f"{rig}-GAME.npz"); f=inp["f"];p=inp["p"]*.01
    uv=np.load(CACHE/f"{rig}-atlas.npy")
    me=bpy.data.meshes.new(f"EXFIL_{rig}_GameAtlas")
    me.from_pydata(p.tolist(),[],f.tolist());me.update()
    me.polygons.foreach_set("use_smooth",np.ones(len(f),bool))
    me.normals_split_custom_set(inp["cn"].reshape(-1,3).tolist())
    layer=me.uv_layers.new(name="EXFIL_Atlas"); layer.data.foreach_set("uv",uv.astype(np.float32).reshape(-1))
    obj=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if not write_asset:
        me.calc_tangents(uvmap=layer.name)
        atlas_t=prop(me.loops,"tangent",3,np.float32).reshape(-1,3,3)
        atlas_s=prop(me.loops,"bitangent_sign",1,np.float32).reshape(-1,3)
        layer.data.foreach_set("uv",inp["uv"].reshape(-1))
        me.calc_tangents(uvmap=layer.name)
        np.savez(CACHE/f"{rig}-basis.npz",t=atlas_t,s=atlas_s,
                 old_t=prop(me.loops,"tangent",3,np.float32).reshape(-1,3,3),
                 old_s=prop(me.loops,"bitangent_sign",1,np.float32).reshape(-1,3))
        return
    folder=BAKES/rig
    m=bpy.data.materials.new("EXFIL_Atlas_"+rig);m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    for kind in ("BaseColor","NormalGL","ORM"):
        file=folder/f"T_EXFIL_{rig}_{kind}.png"
        tx=m.node_tree.nodes.new("ShaderNodeTexImage");tx.image=bpy.data.images.load(str(file));tx.image.pack()
        if kind!="BaseColor":tx.image.colorspace_settings.name="Non-Color"
        if kind=="BaseColor":m.node_tree.links.new(tx.outputs["Color"],bs.inputs["Base Color"])
        elif kind=="NormalGL":
            normal=m.node_tree.nodes.new("ShaderNodeNormalMap")
            m.node_tree.links.new(tx.outputs["Color"],normal.inputs["Color"])
            m.node_tree.links.new(normal.outputs["Normal"],bs.inputs["Normal"])
        else:
            sep=m.node_tree.nodes.new("ShaderNodeSeparateColor");m.node_tree.links.new(tx.outputs["Color"],sep.inputs[0])
            m.node_tree.links.new(sep.outputs["Green"],bs.inputs["Roughness"]);m.node_tree.links.new(sep.outputs["Blue"],bs.inputs["Metallic"])
            group=bpy.data.node_groups.new("glTF Material Output","ShaderNodeTree")
            group.interface.new_socket(name="Occlusion",in_out="INPUT",socket_type="NodeSocketFloat")
            out=m.node_tree.nodes.new("ShaderNodeGroup");out.node_tree=group;m.node_tree.links.new(sep.outputs["Red"],out.inputs["Occlusion"])
    me.materials.append(m)
    # The preview/interchange pivot agrees with the head-bone-local game mesh.
    frame=json.loads((ROOT/"Authored"/f"helmet_{rig}_wear.json").read_bytes())["attachment_frame"]
    local=(inp["p"]*[1,-1,1]-frame["position"])@np.linalg.inv(frame["axes"])
    me.vertices.foreach_set("co",(local*[.01,-.01,.01]).astype(np.float32).reshape(-1))
    local_n=norm((inp["cn"]*[1,-1,1])@np.array(frame["axes"]).T)*[1,-1,1]
    me.normals_split_custom_set(local_n.reshape(-1,3).tolist());me.update()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/f"SM_EXFIL_{rig}_Atlas.blend"))
    bpy.ops.export_scene.gltf(filepath=str(folder/f"SM_EXFIL_{rig}_Atlas.glb"),use_selection=True,export_format="GLB",export_tangents=True)


if __name__=="__main__":
    action,rig,*extra=sys.argv[sys.argv.index("--")+1:]
    if action=="extract":extract(rig,extra[0])
    else:build(rig,action=="deliver")
