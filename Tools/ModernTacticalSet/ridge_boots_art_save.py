"""Persist the reciprocal display/pickup poses and the transparent catalogue image."""
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from ridge_boots_art_render import ROOT, fingerprint

DEST = "/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/RidgeBootsR2"
KEY = "ue_modern_tactical_boots"
ASSETS = ue.EditorAssetLibrary
SUB = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
dynamic = runpy.run_path(str(HERE.parent/"FieldHat/save_icon.py"))["dynamic"]


TANGENT_REVISION = "UnitBasis01"


def supply_tangent_frames(mesh):
    library = ue.GeometryScript_Normals
    lists = ue.GeometryScript_List
    library.compute_tangents(mesh,ue.GeometryScriptTangentsOptions())
    _, normals, valid, _ = library.get_mesh_per_vertex_normals(mesh,False)
    _, tangents, bitangents, has_tangents, _ = library.get_mesh_per_vertex_tangents(mesh,False)
    if not valid or not has_tangents:
        raise RuntimeError("The boot geometry has no shading frame")
    xs, ys = [], []
    for normal,tx,ty in zip(*(lists.convert_vector_list_to_array(v) for v in (normals,tangents,bitangents))):
        a,b,c = normal.x,normal.y,normal.z
        norm = math.sqrt(a*a+b*b+c*c)
        if not math.isfinite(norm) or norm < 1.e-8:
            a,b,c = 0.,0.,1.
        else:
            a,b,c = a/norm,b/norm,c/norm
        dot = a*tx.x+b*tx.y+c*tx.z
        x,y,z = tx.x-dot*a,tx.y-dot*b,tx.z-dot*c
        length = math.sqrt(x*x+y*y+z*z)
        if not math.isfinite(length) or length < 1.e-6:
            x,y,z = (0.,c,-b) if abs(a)<.8 else (-c,0.,a)
            length = math.sqrt(x*x+y*y+z*z)
        x,y,z = x/length,y/length,z/length
        i,j,k = b*z-c*y,c*x-a*z,a*y-b*x
        handed = -1 if i*ty.x+j*ty.y+k*ty.z<0 else 1
        xs.append(ue.Vector(x,y,z))
        ys.append(ue.Vector(handed*i,handed*j,handed*k))
    library.set_mesh_per_vertex_tangents(mesh,lists.convert_array_to_vector_list(xs),
                                          lists.convert_array_to_vector_list(ys))


def static_mesh(geometry,sha,name):
    path = DEST+"/Display/"+name
    slots = geometry["material_slots"]
    mats = [ue.load_asset(DEST+"/Materials/M_"+s) for s in slots]
    if not all(mats):
        raise RuntimeError("Boot material packages must exist before saving "+path)
    asset = ASSETS.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if asset and ASSETS.get_metadata_tag(asset,"EquipmentDefinition")!=KEY:
        raise RuntimeError("Another item occupies "+path)
    if not asset or ASSETS.get_metadata_tag(asset,"BootArtSource")!=sha or ASSETS.get_metadata_tag(asset,"BootTangents")!=TANGENT_REVISION:
        dm = dynamic(geometry)
        supply_tangent_frames(dm)
        if dm.get_triangle_count()!=len(geometry["triangles"]):
            raise RuntimeError("Incomplete footwear topology for "+path)
        if asset:
            opts = ue.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,
                new_material_slot_names=slots,enable_recompute_normals=False,enable_recompute_tangents=False)
            _,outcome = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
                dm,asset,opts,ue.GeometryScriptMeshWriteLOD())
        else:
            opts = ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=False,enable_collision=False)
            asset,outcome = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
        if outcome!=ue.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError("Could not write "+path)
        asset.set_editor_property("static_materials",[
            ue.StaticMaterial(material_interface=m,material_slot_name=s) for m,s in zip(mats,slots)])
        settings = ue.StaticMeshReductionOptions()
        settings.auto_compute_lod_screen_size = False
        settings.reduction_settings = [ue.StaticMeshReductionSettings(percent_triangles=p,screen_size=s)
                                       for p,s in ((1.,1.),(.18,.23),(.035,.075))]
        if SUB.set_lods(asset,settings)!=3:
            raise RuntimeError("Could not build footwear detail levels for "+path)
        for lod in range(3):
            build = SUB.get_lod_build_settings(asset,lod)
            build.set_editor_property("use_full_precision_u_vs",True)
            build.set_editor_property("use_high_precision_tangent_basis",True)
            build.set_editor_property("recompute_tangents",False)
            SUB.set_lod_build_settings(asset,lod,build)
        ASSETS.set_metadata_tag(asset,"EquipmentDefinition",KEY)
        ASSETS.set_metadata_tag(asset,"BootArtSource",sha)
        ASSETS.set_metadata_tag(asset,"BootTangents",TANGENT_REVISION)
        if not ASSETS.save_loaded_asset(asset,False):
            raise RuntimeError("Cannot save "+path)
    return dict(asset=asset.get_path_name(),source_sha256=sha,
                lod_vertices=[SUB.get_number_verts(asset,i) for i in range(SUB.get_lod_count(asset))])


def main():
    manifest = ROOT/"artwork.json"
    if not manifest.exists() or json.loads(manifest.read_bytes()).get("fingerprint")!=fingerprint():
        env = {k:v for k,v in os.environ.items() if k not in ("PYTHONHOME","PYTHONPATH")}
        subprocess.run([shutil.which("python"),"-X","utf8",str(HERE/"ridge_boots_art_render.py")],
                       env=env,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    art = json.loads(manifest.read_bytes())
    if art["fingerprint"]!=fingerprint():
        raise RuntimeError("Boot source changed during background export")
    output = {}
    for kind in ("display","pickup"):
        raw = (ROOT/art[kind]).read_bytes()
        output[kind] = static_mesh(json.loads(raw),hashlib.sha256(raw).hexdigest(),
                                   "SM_TS01_RidgeBoots_"+kind.title())
        del raw
        gc.collect()
        ue.SystemLibrary.collect_garbage()
    image = ROOT/art["standard_icon"]
    task = ue.AssetImportTask()
    task.filename = str(image)
    task.destination_path = DEST+"/Display"
    task.destination_name = "T_TS01_RidgeBoots_Icon"
    task.automated = True
    task.replace_existing = True
    task.save = False
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = ASSETS.load_asset(task.destination_path+"/"+task.destination_name)
    texture.set_editor_property("srgb",True)
    texture.set_editor_property("compression_settings",ue.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property("lod_group",ue.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property("mip_gen_settings",ue.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not ASSETS.save_loaded_asset(texture,False):
        raise RuntimeError("Could not save boot UI texture")
    output["texture"] = dict(asset=texture.get_path_name(),source_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    output["fingerprint"] = art["fingerprint"]
    (ROOT/"artwork-saved.json").write_text(json.dumps(output,indent=2),encoding="utf8")
    print("RIDGE_BOOT_ITEM_SAVED", output, flush=True)


if __name__=="__main__":
    main()
