"""Save the TS01 glove's camera-aligned display, loose pickup, and inventory texture."""
import hashlib
import json
import runpy
import sys
from pathlib import Path

import unreal as ue
sys.path.insert(0,str(Path(__file__).parent))
import lower_seam_uv

P=Path(__file__).resolve().parents[2]
R=P/"SourceAssets/ModernTacticalSet20261113/CoyoteGlovesR2"
DEST="/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CoyoteGlovesR2"
assets=ue.EditorAssetLibrary
utils=ue.GeometryScript_AssetUtils
mat_utils=ue.GeometryScript_Materials
dynamic=runpy.run_path(str(P/"Tools/FieldHat/save_icon.py"))["dynamic"]
sub=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def save_mesh(file,name):
    data=json.loads(file.read_bytes())
    geometry_sha=sha(file)
    path=f"{DEST}/Display/{name}"
    obj=assets.load_asset(path) if assets.does_asset_exist(path) else None
    tag="CoyoteGloveGeometry"
    if obj and not assets.get_metadata_tag(obj,tag):
        raise RuntimeError(f"Existing unowned mesh {path}")
    if not obj or assets.get_metadata_tag(obj,tag)!=geometry_sha or assets.get_metadata_tag(obj,"SeamUV")!=lower_seam_uv.REVISION:
        lower_seam_uv.unfold_sidewalls(data,"CG_",4.)
        dm=dynamic(data)
        if dm.get_triangle_count()!=len(data["triangles"]):
            raise RuntimeError(f"Rejected source faces on {name}")
        slots=data["material_slots"]
        materials=[assets.load_asset(DEST+"/Materials/M_"+s) for s in slots]
        if not all(materials):raise RuntimeError("Missing CoyoteGlovesR2 material")
        if obj:
            options=ue.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                replace_materials=True,new_materials=materials,new_material_slot_names=slots)
            _,status=utils.copy_mesh_to_static_mesh(dm,obj,options,ue.GeometryScriptMeshWriteLOD())
        else:
            options=ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False)
            obj,status=ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,options)
            if obj:
                obj.set_editor_property("static_materials",[ue.StaticMaterial(material_interface=m,material_slot_name=s) for m,s in zip(materials,slots)])
        if status!=ue.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(f"Could not save {name}")
        lods=ue.StaticMeshReductionOptions();lods.auto_compute_lod_screen_size=False
        lods.reduction_settings=[ue.StaticMeshReductionSettings(percent_triangles=r,screen_size=s)
                                for r,s in ((1.,1.),(.50,.18),(.24,.07))]
        if sub.set_lods(obj,lods)!=3:raise RuntimeError("Missing glove display LOD")
        assets.set_metadata_tag(obj,tag,geometry_sha)
        assets.set_metadata_tag(obj,"SeamUV",lower_seam_uv.REVISION)
        if not assets.save_loaded_asset(obj,False):raise RuntimeError(f"Failed to persist {path}")
    triangles=[]
    for i in range(3):
        rd,status=utils.copy_mesh_from_static_mesh(obj,ue.DynamicMesh(),ue.GeometryScriptCopyMeshFromAssetOptions(),
                                 ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.RENDER_DATA,lod_index=i))
        if status!=ue.GeometryScriptOutcomePins.SUCCESS or not rd.get_triangle_count():
            raise RuntimeError(f"Empty render data {path} LOD{i}")
        triangles.append(rd.get_triangle_count())
    return dict(asset=obj.get_path_name(),source_sha256=geometry_sha,render_lods=triangles,seam_uv=lower_seam_uv.REVISION)


def main():
    art=json.loads((R/"artwork.json").read_bytes())
    if art["source_sha256"]!=sha(R/art["source"]):
        raise RuntimeError("Game glove changed after making artwork")
    saved={}
    for role in ("pickup","display"):
        saved[role]=save_mesh(R/art[role],"SM_TS01_CoyoteGloves_"+role.title())
    png=R/art["standard_icon"]
    task=ue.AssetImportTask();task.filename=str(png);task.destination_path=DEST+"/Display"
    task.destination_name="T_TS01_CoyoteGloves_Icon";task.automated=True;task.replace_existing=True;task.save=False
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=assets.load_asset(task.destination_path+"/"+task.destination_name)
    for k,v in dict(srgb=True,compression_settings=ue.TextureCompressionSettings.TC_EDITOR_ICON,
        lod_group=ue.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=ue.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():
        texture.set_editor_property(k,v)
    if not assets.save_loaded_asset(texture,False):raise RuntimeError("Failed to save glove icon texture")
    saved["texture"]=dict(asset=texture.get_path_name(),source_sha256=sha(png))
    (R/"artwork-saved.json").write_text(json.dumps(saved,indent=2),encoding="utf8")
    print("COYOTE_GLOVE_ART_SAVED",saved,flush=True)


if __name__=="__main__":main()
