"""Import both inventory representations of the new field trousers into UE."""
import gc
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import unreal as ue
sys.path.insert(0,str(Path(__file__).parent))
import lower_seam_uv

P=Path(__file__).resolve().parents[2]
R=P/"SourceAssets/ModernTacticalSet20261113/FieldTrousersR2"
DEST="/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/FieldTrousersR2"
assets=ue.EditorAssetLibrary
utils=ue.GeometryScript_AssetUtils
dynamic=runpy.run_path(str(P/"Tools/FieldHat/save_icon.py"))["dynamic"]
sub=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
DISTANCE_PATTERN="SewnPanels01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def store(geometry,source_sha,name):
    path=DEST+"/Display/"+name
    slots=geometry["material_slots"]
    mats=[ue.load_asset(DEST+"/Materials/M_"+slot) for slot in slots]
    if not all(mats):raise RuntimeError("Incomplete trouser materials for "+name)
    mesh=assets.load_asset(path) if assets.does_asset_exist(path) else None
    if mesh and assets.get_metadata_tag(mesh,"EquipmentDefinition")!="ue_modern_tactical_pants":
        raise RuntimeError("Existing asset occupies the requested trousers path "+path)
    if (not mesh or assets.get_metadata_tag(mesh,"FieldTrousersArtSource")!=source_sha
        or assets.get_metadata_tag(mesh,"SeamUV")!=lower_seam_uv.REVISION
        or assets.get_metadata_tag(mesh,"DistancePattern")!=DISTANCE_PATTERN):
        lower_seam_uv.unfold_sidewalls(geometry,"FT_",8.)
        dm=dynamic(geometry)
        if dm.get_triangle_count()!=len(geometry["triangles"]):
            raise RuntimeError("Source faces lost on "+name)
        if mesh:
            opts=ue.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,
                new_material_slot_names=slots,enable_recompute_normals=False,enable_recompute_tangents=True)
            _,status=utils.copy_mesh_to_static_mesh(dm,mesh,opts,ue.GeometryScriptMeshWriteLOD())
        else:
            opts=ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True,enable_collision=False)
            mesh,status=ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
        if status!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Failed to create "+path)
        mesh.set_editor_property("static_materials",[ue.StaticMaterial(material_interface=m,material_slot_name=s) for m,s in zip(mats,slots)])
        opts=ue.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False
        opts.reduction_settings=[ue.StaticMeshReductionSettings(percent_triangles=1.,screen_size=s)
            for s in (1.,.18,.07)]
        if sub.set_lods(mesh,opts)!=3:raise RuntimeError("Cannot build three detail levels for "+path)
        # The far reducer moved pocket flaps and the waist overlay into the
        # trouser surface. Keep their fitted positions at distance and remove
        # complete sub-pixel stitch and zipper elements instead.
        for level,removed in [(1,{"FT_Thread"}),(2,{"FT_Thread","FT_Hardware"})]:
            keep=[i for i,slot in enumerate(geometry["triangle_materials"]) if slots[slot] not in removed]
            layer=dict(geometry)
            for field in ("triangles","triangle_materials","normals","uv"):
                layer[field]=[geometry[field][i] for i in keep]
            lod_mesh=dynamic(layer)
            write_lod=ue.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,
                new_material_slot_names=slots,enable_recompute_normals=False,enable_recompute_tangents=True)
            _,status=utils.copy_mesh_to_static_mesh(lod_mesh,mesh,write_lod,ue.GeometryScriptMeshWriteLOD(lod_index=level))
            if status!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(f"Cannot save sewn LOD {level} for {path}")
        assets.set_metadata_tag(mesh,"DistancePattern",DISTANCE_PATTERN)
        assets.set_metadata_tag(mesh,"FieldTrousersArtSource",source_sha)
        assets.set_metadata_tag(mesh,"SeamUV",lower_seam_uv.REVISION)
        assets.set_metadata_tag(mesh,"EquipmentDefinition","ue_modern_tactical_pants")
        if not assets.save_loaded_asset(mesh,False):raise RuntimeError("Could not save "+path)
    levels=[sub.get_number_verts(mesh,level) for level in range(sub.get_lod_count(mesh))]
    return dict(asset=mesh.get_path_name(),source_sha256=source_sha,lod_vertices=levels,seam_uv=lower_seam_uv.REVISION,
                distance_pattern=DISTANCE_PATTERN)


def main():
    art=json.loads((R/"artwork.json").read_bytes())
    if art["source_sha256"]!=sha(R/art["source"]):
        # The artist can finish a newer cut while UE is queued behind the
        # shared import mutex. Photograph and export that actual cut before
        # persisting an obsolete icon or pickup.
        env={k:v for k,v in os.environ.items() if k not in ("PYTHONHOME","PYTHONPATH")}
        subprocess.run([shutil.which("python"),"-X","utf8",str(Path(__file__).with_name("field_pants_art_render.py"))],
            env=env,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
        art=json.loads((R/"artwork.json").read_bytes())
        if art["source_sha256"]!=sha(R/art["source"]):
            raise RuntimeError("New sewing pattern arrived while exporting the game models")
    receipt=R/"artwork-saved.json"
    if receipt.is_file():
        saved=json.loads(receipt.read_bytes())
        inputs=(("display","display"),("pickup","pickup"),("texture","standard_icon"))
        if all(saved[k]["source_sha256"]==sha(R/art[file]) and assets.does_asset_exist(saved[k]["asset"]) and
               (k=="texture" or (saved[k].get("seam_uv")==lower_seam_uv.REVISION and saved[k].get("distance_pattern")==DISTANCE_PATTERN))
               for k,file in inputs):
            return
    output={}
    for kind in ("display","pickup"):
        file=R/art[kind]
        data=file.read_bytes()
        output[kind]=store(json.loads(data),hashlib.sha256(data).hexdigest(),"SM_TS01_FieldTrousers_"+kind.title())
        del data;gc.collect();ue.SystemLibrary.collect_garbage()
    image=R/art["standard_icon"]
    task=ue.AssetImportTask();task.filename=str(image);task.destination_path=DEST+"/Display"
    task.destination_name="T_TS01_FieldTrousers_Icon";task.automated=True;task.replace_existing=True;task.save=False
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=assets.load_asset(task.destination_path+"/"+task.destination_name)
    texture.set_editor_property("srgb",True)
    texture.set_editor_property("compression_settings",ue.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property("lod_group",ue.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property("mip_gen_settings",ue.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not assets.save_loaded_asset(texture,False):raise RuntimeError("Failed to save field trouser inventory texture")
    output["texture"]=dict(asset=texture.get_path_name(),source_sha256=sha(image))
    receipt.write_text(json.dumps(output,indent=2),encoding="utf8")
    print("FIELD_TROUSER_ART_SAVED",output,flush=True)


if __name__=="__main__":main()
