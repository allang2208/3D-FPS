"""Build the native editable rig, the photographic pair, high relief and interchange models."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_art_geometry import neutral_hand,unit
from lower_seam_uv import unfold_sidewalls

P=HERE.parents[1]
ROOT=P/"SourceAssets/ModernTacticalSet20261113/CoyoteGlovesR2"
MODEL=ROOT/"Models"
EXPORT=ROOT/"Exports"


def begin():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.preferences.view.use_translate_new_dataname=False
    from coyote_glove_materials import create
    result=create()
    for im in bpy.data.images:
        if im.source=="FILE" and im.filepath and not im.packed_file:
            im.pack()
    return result


def skeleton(joints,name):
    data=bpy.data.armatures.new(name)
    obj=bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    children={}
    for k,(pivot,axes,parent) in joints.items():
        if parent:children.setdefault(parent,[]).append(k)
    for k,(pivot,axes,parent) in joints.items():
        bone=data.edit_bones.new(k)
        bone.head=Vector(pivot*.01)
        offspring=children.get(k,[])
        if len(offspring)==1 and np.linalg.norm(joints[offspring[0]][0]-pivot)>.1:
            tip=joints[offspring[0]][0]
        elif parent and k.startswith(("thumb_","index_","middle_","ring_","pinky_")):
            old=joints[parent][0];tip=pivot+unit(pivot-old)*1.7
        else:
            tip=pivot+axes[0]*2.
        bone.tail=Vector(tip*.01)
        if (bone.tail-bone.head).length<.0002:
            bone.tail=bone.head+Vector((0,.003,0))
        bone.align_roll(Vector(axes[2]))
    for k,(_,_,parent) in joints.items():
        if parent in joints:data.edit_bones[k].parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False);obj.display_type="WIRE";obj.show_in_front=False
    return obj


def mesh(name,p,f,n,uv,mat,slots,materials):
    me=bpy.data.meshes.new(name)
    me.from_pydata((p*.01).tolist(),[],f.tolist())
    me.update()
    ob=bpy.data.objects.new(name,me)
    bpy.context.scene.collection.objects.link(ob)
    for k in slots:
        me.materials.append(materials[k])
    me.polygons.foreach_set("use_smooth",np.ones(len(f),dtype=bool))
    me.polygons.foreach_set("material_index",np.asarray(mat,np.int32))
    layer=me.uv_layers.new(name="Surface UV")
    layer.data.foreach_set("uv",uv.astype(np.float32).reshape(-1))
    me.normals_split_custom_set(n.reshape(-1,3).tolist())
    return ob


def bind(ob,arm,rows):
    for name,entries in rows.items():
        group=ob.vertex_groups.new(name=name)
        for vi,w in entries:group.add([int(vi)],float(w),"REPLACE")
    mod=ob.modifiers.new("Native finger and wrist weights","ARMATURE")
    mod.object=arm;ob.parent=arm


def select(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:ob.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]


def native_master(d):
    mats=begin()
    scale=np.array([1.,-1.,1.])
    p=np.asarray(d['positions'])*scale;f=np.asarray(d['triangles']);n=np.asarray(d['normals'])*scale
    uv=np.asarray(d['uv']);uv[:,:,1]=1.-uv[:,:,1]
    ids={b['index']:b['name'] for b in d['bones']}
    joints={b['name']:(np.asarray(b['position'])*scale,unit(np.asarray(b['axes'])*scale),ids.get(b['parent'])) for b in d['bones']}
    arm=skeleton(joints,"CG_Body_NativeRig")
    slots=[x.rsplit("/",1)[-1].split(".")[0].removeprefix("M_") for x in d['material_slots']]
    ob=mesh("CG_Native_Body_Gloves",p,f,n,uv,d['triangle_materials'],slots,mats)
    groups={}
    for vi,row in enumerate(d["weights"]):
        for bi,weight in row:groups.setdefault(ids[bi],[]).append((vi,weight))
    bind(ob,arm,groups)
    select([ob,arm])
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/"SK_TS01_CoyoteGloves_Body.blend"),compress=True)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/"SK_TS01_CoyoteGloves_Body.fbx"),use_selection=True,
        object_types={"MESH","ARMATURE"},apply_unit_scale=True,bake_anim=False,add_leaf_bones=False,
        mesh_smooth_type="FACE",axis_forward="-Y",axis_up="Z",path_mode="COPY",embed_textures=True)


def height_image(name):
    size=512
    y,x=np.indices((size,size),dtype=np.float32)/size
    tau=np.pi*2
    if name=="Knit":
        w=x*54+.20*np.sin(tau*y*32)
        course=y*32+.24*np.cos(tau*w)
        h=.48+.25*np.cos(tau*w)+.22*np.cos(tau*course)*np.cos(tau*w*.5)
    elif name=="Webbing":
        u=tau*x*80;v=tau*y*52
        h=.5+.26*np.cos(u)*(.55+.45*np.sin(v/2))+.23*np.cos(v)*(.55-.45*np.sin(u/2))
    else:
        rng=np.random.default_rng(403)
        grains=rng.normal(0,.09,(size,size))
        h=.5+grains+.14*np.sin(tau*(x*25+y*32)+2*np.sin(tau*y*5))+.15*np.sin(tau*(x*45-y*30))
    image=bpy.data.images.new("Sculpt relief · "+name,width=size,height=size,alpha=False)
    image.colorspace_settings.name="Non-Color"
    h=np.clip(h,0.,1.);rgba=np.stack((h,h,h,np.ones_like(h)),-1).astype(np.float32)
    image.pixels.foreach_set(rgba.ravel());image.pack()
    tx=bpy.data.textures.new("Physical relief · "+name,"IMAGE")
    tx.image=image;tx.extension="REPEAT"
    return tx


def high_relief(ob,tx):
    sub=ob.modifiers.new("Fabric sculpt resolution","SUBSURF")
    sub.subdivision_type="SIMPLE"
    sub.levels=2 if len(ob.data.polygons)>12000 else 3
    sub.render_levels=sub.levels
    sub.uv_smooth="NONE";sub.show_only_control_edges=False
    for name,strength in (("Knit",.00031),("Webbing",.00028),("Suede",.00014)):
        mi=next((i for i,m in enumerate(ob.data.materials) if m.name.split(".")[0]=="CG_"+name),None)
        if mi is None:continue
        used=set();bound=set();edges={}
        for face in ob.data.polygons:
            if face.material_index!=mi:continue
            used.update(face.vertices)
            for edge in face.edge_keys:edges[edge]=edges.get(edge,0)+1
        for edge,count in edges.items():
            if count==1:bound.update(edge)
        if not used-bound:continue
        mask=ob.vertex_groups.new(name="Sculpt "+name);mask.add(sorted(used-bound),1.,"REPLACE")
        mod=ob.modifiers.new(name+" surface relief","DISPLACE")
        mod.texture=tx[name];mod.texture_coords="UV";mod.uv_layer=ob.data.uv_layers.active.name
        mod.vertex_group=mask.name;mod.strength=strength;mod.mid_level=.5


def studio_master(d):
    mats=begin();hands={}
    for side in ("l","r"):
        hands[side]=neutral_hand(d,side,cupped=side=="r",empty_cuff=True)
    objects=[]
    for side,g in hands.items():
        name="CG_Studio_"+side
        x=-8. if side=="l" else 8.
        off=np.array([x,-6.5,0.])
        joints={k:(pivot+off,axes,parent) for k,(pivot,axes,parent) in g["joints"].items()}
        arm=skeleton(joints,name+"_Rig")
        ob=mesh(name,g["p"]+off,g["f"],g["n"],g["uv"],g["m"],g["slots"],mats)
        bind(ob,arm,g["groups"])
        ob["studio_side"]=side;ob["studio_offset_cm"]=off
        triangles=g["p"][g["f"]];centers=triangles.mean(1)
        fabric=(g["m"]==g["slots"].index("CG_Knit"))&(abs(centers[:,0])<3.5)&(centers[:,1]>2)&(centers[:,1]<9)
        area=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
        mean_z=np.sum(g["n"][fabric,:,2].mean(1)*area[fabric])
        ob["dorsal_facing_z"]=1 if mean_z>=0 else -1
        objects.extend([ob,arm])
    select(objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/"SK_TS01_CoyoteGloves_GAME.blend"),compress=True)
    bpy.ops.export_scene.gltf(filepath=str(EXPORT/"SK_TS01_CoyoteGloves.glb"),export_format="GLB",use_selection=True,
        export_tangents=True,export_animations=False,export_all_influences=True)
    # High and game have identical rest dimensions. Keep the relief and
    # subdivision layers editable in the high-resolution source.
    tx={k:height_image(k) for k in ("Knit","Suede","Webbing")}
    for ob in objects:
        if ob.type=="MESH":high_relief(ob,tx)
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/"SK_TS01_CoyoteGloves_HIGH.blend"),compress=True)
    deps=bpy.context.evaluated_depsgraph_get()
    high={}
    for ob in objects:
        if ob.type!="MESH":continue
        ev=ob.evaluated_get(deps);geo=ev.to_mesh();geo.calc_loop_triangles()
        high[ob.name]=len(geo.loop_triangles);ev.to_mesh_clear()
    return high


def main():
    for dst in (EXPORT,MODEL):dst.mkdir(exist_ok=True,parents=True)
    src=ROOT/"Authored/gloves_Body.json";studio_source=ROOT/"Authored/gloves_M4.json"
    body_bytes=src.read_bytes();studio_bytes=studio_source.read_bytes()
    d=json.loads(body_bytes)
    studio=json.loads(studio_bytes)
    unfold_sidewalls(d,"CG_",4.)
    unfold_sidewalls(studio,"CG_",4.)
    native_master(d);high=studio_master(studio)
    print("COYOTE_EDITABLE_MASTERS",len(d["triangles"]),high,flush=True)
    (MODEL/"models.json").write_text(json.dumps(dict(source=str(src.relative_to(ROOT)),
        source_sha256=hashlib.sha256(body_bytes).hexdigest(),native_triangles=len(d["triangles"]),
        photographic_source=studio_source.relative_to(ROOT).as_posix(),photographic_source_sha256=hashlib.sha256(studio_bytes).hexdigest(),
        photographic_high_triangles=high,game_glb="Exports/SK_TS01_CoyoteGloves.glb",
        native_fbx="Exports/SK_TS01_CoyoteGloves_Body.fbx"),indent=2))


if __name__=="__main__":
    main()
