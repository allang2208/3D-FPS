"""Save the high village modules with their own Meshy textures and compound collision."""
import gc
import hashlib
import json
import os
import runpy
from pathlib import Path
from struct import iter_unpack
from zipfile import ZipFile
import unreal as u

PROJECT=Path(os.environ["HIGH_VILLAGE_PROJECT"])
SOURCE=PROJECT/"SourceAssets/HillsVillageHighWall20261120/Design01/Authored"
PACK="/Game/WorldGeneration/TemperateHills/HighVillageDefense"
OWNER="HillsVillageHighWall20261120"
RECEIPT=SOURCE/"imported.json"
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
L=u.MaterialEditingLibrary


def save(obj):
    E.set_metadata_tag(obj,"VillageHighWallOwner",OWNER)
    if not E.save_loaded_asset(obj,False):
        raise RuntimeError("Could not save "+obj.get_path_name())


def existing(addr):
    if not E.does_asset_exist(addr):return None
    asset=E.load_asset(addr)
    if not asset or str(E.get_metadata_tag(asset,"VillageHighWallOwner"))!=OWNER:
        raise RuntimeError("Existing package belongs to different production: "+addr)
    return asset


def require(addr):
    obj=u.load_asset(addr)
    if not obj:raise RuntimeError("Required village material missing "+addr)
    return obj


def texture(slot,channel):
    folder="Bakes" if (slot,channel)==("HighWallStone","normal") else "Textures"
    fname=SOURCE/folder/f"{slot}_{channel}.png"
    name="T_"+slot+"_"+channel
    dest=PACK+"/Textures";path=dest+"/"+name
    old=existing(path)
    digest=hashlib.sha256(fname.read_bytes()).hexdigest()
    if old and str(E.get_metadata_tag(old,"VillageSourceSHA"))==digest:return old
    t=u.AssetImportTask()
    t.filename=str(fname);t.destination_name=name;t.destination_path=dest
    t.automated=True;t.save=False;t.replace_existing=bool(old)
    A.import_asset_tasks([t]);tex=require(path)
    tex.set_editor_property("srgb",channel=="base_color")
    if channel=="normal":
        tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("flip_green_channel",True)
    elif channel!="base_color":
        tex.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property("max_texture_size",2048)
    E.set_metadata_tag(tex,"VillageSourceSHA",digest)
    save(tex)
    return tex


def scan_material(slot,parent):
    name="MI_"+slot
    dest=PACK+"/Materials"
    mat=existing(dest+"/"+name) or A.create_asset(name,dest,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    if not mat:raise RuntimeError("Cannot create "+name)
    L.set_material_instance_parent(mat,parent)
    for channel in ("base_color","normal","roughness","metallic"):
        # UE 5.8 updates the override but returns false unconditionally.
        L.set_material_instance_texture_parameter_value(mat,channel,texture(slot,channel))
    save(mat)
    return mat


def create_role(role,materials,receipt):
    path=PACK+"/"+role;file=SOURCE/(role+".meshzip")
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    obj=existing(path)
    if obj and str(E.get_metadata_tag(obj,"VillageSourceSHA"))==digest and role in receipt["saved"]:
        return
    dynamic=u.DynamicMesh()
    with ZipFile(file) as archive:
        spec=json.loads(archive.read("mesh.json"))
        for i,slot in enumerate(spec["materials"]):
            if slot not in materials:raise RuntimeError("Unbound material "+slot)
            def entries(name,fmt):
                return iter_unpack("<"+fmt,archive.read(f"{i}/{name}"))
            buf=u.GeometryScriptSimpleMeshBuffers()
            buf.vertices=[u.Vector(*p) for p in entries("vertices","3f")]
            buf.uv1=[u.Vector2D(max(p[2],0.)/170.,0.) for p in entries("vertices","3f")]
            buf.uv0=[u.Vector2D(*p) for p in entries("uv","2f")]
            buf.normals=[u.Vector(*p) for p in entries("normals","3f")]
            buf.triangles=[u.IntVector(*p) for p in entries("indices","3i")]
            u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic,buf,material_id=i)
            del buf
    # NewAsset creates an initial mesh; CopyMesh below installs the named material
    # bindings, normals, Nanite fallback and the authored channels in one pass.
    if not obj:
        obj,result=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,path,
            u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True,enable_collision=True,enable_nanite=False))
        if not obj or result!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError("Cannot create "+path)
    ns=obj.get_editor_property("nanite_settings");ns.enabled=True
    ns.fallback_percent_triangles=1.;ns.fallback_relative_error=.35
    slots=spec["materials"]
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,
        enable_recompute_tangents=True,replace_materials=True,new_materials=[materials[s] for s in slots],
        new_material_slot_names=slots,apply_nanite_settings=True,new_nanite_settings=ns)
    _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,obj,options,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Mesh build failed: "+role)
    body=obj.get_editor_property("body_setup")
    aggregate=body.get_editor_property("agg_geom");boxes=[]
    for data in spec["boxes"]:
        box=u.KBoxElem();box.set_editor_property("center",u.Vector(*data["center"]))
        for field,length in zip(("x","y","z"),data["size"]):
            box.set_editor_property(field,length)
        if "pitch" in data:box.set_editor_property("rotation",u.Rotator(pitch=data["pitch"]))
        boxes.append(box)
    for key in ("convex_elems","sphere_elems","sphyl_elems"):aggregate.set_editor_property(key,[])
    aggregate.set_editor_property("box_elems",boxes)
    body.set_editor_property("agg_geom",aggregate)
    body.set_editor_property("collision_trace_flag",u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    E.set_metadata_tag(obj,"VillageSourceSHA",digest)
    save(obj)
    receipt["saved"][role]={"path":obj.get_path_name(),"materials":slots,"triangles":spec["faces"],
        "collision_boxes":len(boxes),"source_sha256":digest}
    RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf8")
    u.log("HIGH_VILLAGE_SAVED "+obj.get_path_name())
    del dynamic
    gc.collect()


def main():
    for dest in (PACK,PACK+"/Materials",PACK+"/Textures"):E.make_directory(dest)
    portals_only=os.environ.get("HIGH_VILLAGE_PORTALS_ONLY")=="1"
    if portals_only:
        roles=("SM_HighPortalGalleryWest","SM_HighPortalGalleryEast")
    elif os.environ.get("HIGH_VILLAGE_WALL_ONLY")=="1":
        roles=("SM_HighWall",)
    else:
        roles=("SM_HighWall","SM_HighPortalGalleryWest","SM_HighPortalGalleryEast","SM_IronGrilleWest","SM_IronGrilleEast")
    needed = set()
    for role in roles:
        with ZipFile(SOURCE/(role+".meshzip")) as archive:
            needed.update(json.loads(archive.read("mesh.json"))["materials"])
    perim={}
    for catalog in ("VillageDefenses20261117","HillsVillagePerimeter20261117"):
        source=PROJECT/"SourceAssets"/catalog/"asset-production.json"
        for obj in json.loads(source.read_text(encoding="utf-8-sig"))["saved"]:
            perim.update(obj["materials"])
    materials={slot:require(perim[slot]) for slot in needed if slot in perim}
    scan_slots=needed-materials.keys()
    if portals_only:
        for slot in scan_slots:
            materials[slot]=require(PACK+"/Materials/MI_"+slot)
    elif scan_slots:
        parent=require("/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelArtifact")
        for slot in sorted(scan_slots):
            materials[slot]=scan_material(slot,parent)
    receipt=json.loads(RECEIPT.read_text(encoding="utf8")) if RECEIPT.exists() else {"saved":{}}
    for role in roles:
        bindings=materials
        if role.startswith("SM_HighPortalGallery"):
            # These are the two actual bindings in the abandoned house wall.
            donor=require("/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A")
            slots={s.material_interface.get_name():s.material_interface for s in donor.static_materials}
            bindings=dict(materials,Mortar=slots["MI_Main_Mortar_00A"])
            for slot in ("YardField","YardSlate","YardCap"):
                bindings[slot]=slots["MI_Main_StoneWall_00A"]
        create_role(role,bindings,receipt)
    if not portals_only:
        runpy.run_path(str(SOURCE.parent/"author_wall_fracture.py"),run_name="__main__")
    u.log("HIGH_VILLAGE_IMPORT_COMPLETE")


main()
