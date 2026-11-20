"""Editable, skinned TS01 field trousers and a physically scaled cloth relief master."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_art import bind,mesh,select,skeleton,unit
from field_pants_materials import create

ROOT=HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113/FieldTrousersR2"
MODELS=ROOT/"Models"
EXPORTS=ROOT/"Exports"
NAME="SK_TS01_FieldTrousers"
FLIP=np.array([1.,-1.,1.])


def garment(d,mats):
    slots=d["material_slots"]
    used=[i for i,name in enumerate(slots) if name in mats]
    unknown=[name for i,name in enumerate(slots) if i not in used and not name.startswith("NATIVE:")]
    if unknown:
        raise RuntimeError(f"Missing trouser material {unknown}")
    material=np.asarray(d["triangle_materials"])
    cloth=np.isin(material,used)
    source_faces=np.asarray(d["triangles"])
    garment_faces=np.flatnonzero(cloth)
    # The triangle at the closure of a sewn loop sometimes belongs to both
    # adjoining pattern boundaries. Keep one copy with the same material.
    duplicate_key=np.column_stack((np.sort(source_faces[cloth],axis=1),material[cloth]))
    _,first=np.unique(duplicate_key,axis=0,return_index=True)
    cloth[:]=False;cloth[garment_faces[first]]=True
    faces=source_faces[cloth]
    vertices,compact=np.unique(faces.ravel(),return_inverse=True)
    coords=np.asarray(d["positions"])[vertices]*FLIP
    normals=np.asarray(d["normals"])[cloth]*FLIP
    uv=np.asarray(d["uv"])[cloth]
    uv[:,:,1]=1.-uv[:,:,1]
    mat_index=np.searchsorted(used,material[cloth])
    ob=mesh(NAME,coords,compact.reshape(-1,3),normals,uv,mat_index,[slots[i] for i in used],mats)
    ids={b["index"]:b["name"] for b in d["bones"]}
    joints={b["name"]:(np.array(b["position"])*FLIP,unit(np.asarray(b["axes"])*FLIP),ids.get(b["parent"])) for b in d["bones"]}
    arm=skeleton(joints,"TS01_Jason_Rig")
    groups={}
    for i,v in enumerate(vertices):
        for bi,w in d["weights"][v]:
            groups.setdefault(ids[bi],[]).append((i,w))
    bind(ob,arm,groups)
    ob.modifiers[0].name="Native pelvis, thigh and calf weights"
    # Retain the pattern cutter's face sets in the editable game mesh.
    if isinstance(d.get("parts"),dict):
        source_ids=np.flatnonzero(cloth)
        pattern=np.zeros(len(source_ids),dtype=np.int32)
        names=["Garment"]
        for name,bounds in d["parts"].items():
            if not isinstance(bounds,list) or len(bounds)!=2:continue
            a,b=bounds
            if not isinstance(a,int) or not isinstance(b,int):continue
            names.append(name)
            pattern[(source_ids>=a)&(source_ids<b)]=len(names)-1
        if len(names)>1:
            attr=ob.data.attributes.new("Sewing pattern piece","INT","FACE")
            attr.data.foreach_set("value",pattern)
            ob["pattern_names"]=json.dumps(names)
    return ob,arm


def relief_texture(kind,res=512):
    # Reconstruct a relative fabric height field from the material's own
    # tiled OpenGL tangent-space normal. Integrating gradients keeps warp,
    # weft, and the raised ripstop lines registered to the finished textile.
    image=bpy.data.images.get(kind+"_NormalGL.png")
    if image is None:
        raise RuntimeError("No matching normal map for "+kind)
    width,height=image.size
    rgba=np.empty(width*height*4,np.float32)
    image.pixels.foreach_get(rgba)
    normals=rgba.reshape(height,width,4)[::max(1,height//res),::max(1,width//res),:3]*2-1
    h,w=normals.shape[:2]
    dx=-normals[:,:,0]/np.maximum(.18,normals[:,:,2])
    dy=-normals[:,:,1]/np.maximum(.18,normals[:,:,2])
    kx=np.fft.rfftfreq(w)[None,:]*2*np.pi
    ky=np.fft.fftfreq(h)[:,None]*2*np.pi
    denom=kx*kx+ky*ky
    denom[0,0]=1.
    field=np.fft.irfft2((-1j*kx*np.fft.rfft2(dx)-1j*ky*np.fft.rfft2(dy))/denom,s=(h,w)).real
    a,b=np.percentile(field,[1.,99.])
    level=np.clip((field-a)/max(1.e-7,b-a),0.,1.).astype(np.float32)
    relief=bpy.data.images.new(kind+" textile relief",width=w,height=h,alpha=False)
    relief.colorspace_settings.name="Non-Color"
    relief.pixels.foreach_set(np.stack([level,level,level,np.ones_like(level)],axis=2).ravel())
    relief.pack()
    tx=bpy.data.textures.new(kind+" woven displacement","IMAGE")
    tx.image=relief
    return tx


def high_master(ob):
    sub=ob.modifiers.new("Garment subdivision for woven relief","SUBSURF")
    sub.subdivision_type="SIMPLE";sub.levels=2;sub.render_levels=2;sub.uv_smooth="NONE"
    for name,strength in (("FT_Ripstop",.00029),("FT_Reinforcement",.00033),("FT_Stretch",.00022),("FT_Webbing",.00041)):
        slot=ob.data.materials.find(name)
        if slot<0:continue
        vertices=set();boundary={}
        for face in ob.data.polygons:
            if face.material_index!=slot:continue
            vertices.update(face.vertices)
            for edge in face.edge_keys:boundary[edge]=boundary.get(edge,0)+1
        for edge,n in boundary.items():
            if n==1:vertices.difference_update(edge)
        if not vertices:continue
        mask=ob.vertex_groups.new(name=name+" relief field")
        mask.add(sorted(vertices),1.,"REPLACE")
        mod=ob.modifiers.new(name+" warp and weft","DISPLACE")
        mod.texture=relief_texture(name);mod.texture_coords="UV";mod.uv_layer=ob.data.uv_layers.active.name
        mod.vertex_group=mask.name;mod.strength=strength;mod.mid_level=.5
    bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/(NAME+"_HIGH.blend")),compress=True)
    ctx=bpy.context.evaluated_depsgraph_get()
    ev=ob.evaluated_get(ctx);model=ev.to_mesh();model.calc_loop_triangles()
    tri=len(model.loop_triangles);ev.to_mesh_clear()
    return tri


def main():
    for path in (MODELS,EXPORTS):path.mkdir(parents=True,exist_ok=True)
    source=ROOT/"Authored/pants_Jason.json";raw=source.read_bytes()
    src=json.loads(raw)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    mats=create()
    for im in bpy.data.images:
        if im.source=="FILE" and im.filepath and not im.packed_file:im.pack()
    ob,arm=garment(src,mats);select([ob,arm])
    triangles=len(ob.data.polygons)
    bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/(NAME+"_GAME.blend")),compress=True)
    bpy.ops.export_scene.gltf(filepath=str(EXPORTS/(NAME+".glb")),export_format="GLB",use_selection=True,
        export_animations=False,export_tangents=True,export_all_influences=True)
    bpy.ops.export_scene.fbx(filepath=str(EXPORTS/(NAME+".fbx")),use_selection=True,
        object_types={"MESH","ARMATURE"},bake_anim=False,add_leaf_bones=False,mesh_smooth_type="FACE",
        apply_unit_scale=True,axis_forward="-Y",axis_up="Z",path_mode="COPY",embed_textures=True)
    high=high_master(ob)
    record=dict(source=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(raw).hexdigest(),
        native_clothed_body="Jason",triangles=triangles,high_triangles=high,
        game_blend="Models/"+NAME+"_GAME.blend",high_blend="Models/"+NAME+"_HIGH.blend",
        game_glb="Exports/"+NAME+".glb",native_fbx="Exports/"+NAME+".fbx")
    (MODELS/"models.json").write_text(json.dumps(record,indent=2))
    print("FIELD_TROUSER_MASTERS",triangles,high,flush=True)


if __name__=="__main__":main()
