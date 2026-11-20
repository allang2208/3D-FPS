"""Import the repaired shed and persist render permutations on the quarry kit."""
from pathlib import Path
import os
import unreal as ue

project=Path(__file__).resolve().parents[3]
kit="/Game/WorldGeneration/TemperateHills/WhiteCliffs"
assets=ue.EditorAssetLibrary
name="SM_QuarryRuinedShed"
path=kit+"/Meshes/"+name
old=ue.load_asset(path)
bindings={str(s.material_slot_name):s.material_interface for s in old.static_materials}
# The masonry's foot dampness, cap lichen and individual mineral colours are
# authored into mesh vertices with the same channels as the parent quarry bed.
wall_mat=ue.load_asset(kit+"/Materials/Approach/M_QuarryBeddedLime")
if not wall_mat:
    raise RuntimeError("Missing weathered quarry wall material")
bindings["Stone"]=wall_mat
task=ue.AssetImportTask()
task.filename=str(project/"SourceAssets/HillsRiverLake20261117/Authored"/(name+".fbx"))
task.destination_path=kit+"/Meshes"
task.destination_name=name
task.automated=True
task.replace_existing=True
task.replace_existing_settings=True
options=ue.FbxImportUI()
options.import_materials=False
options.import_textures=False
options.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH
settings=options.static_mesh_import_data
settings.combine_meshes=True
settings.auto_generate_collision=False
settings.generate_lightmap_u_vs=False
settings.normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
settings.vertex_color_import_option=ue.VertexColorImportOption.REPLACE
task.options=options
ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=ue.load_asset(path)
if not task.imported_object_paths:
    raise RuntimeError(path)
for index,slot in enumerate(mesh.static_materials):
    mesh.set_material(index,bindings[str(slot.material_slot_name)])
nanite=mesh.get_editor_property("nanite_settings")
nanite.enabled=True
nanite.fallback_percent_triangles=1.
nanite.fallback_relative_error=0.
mesh.set_editor_property("nanite_settings",nanite)
mesh.get_editor_property("body_setup").set_editor_property("collision_trace_flag",ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not assets.save_loaded_asset(mesh,False):
    raise RuntimeError(path)

# Only these base materials back quarry Nanite instances. Instances inherit usage
# from their parent, so change the quarry-owned parents themselves.
render_materials=("M_CliffA","M_CliffB","M_LimestoneCut","M_LimestoneSpoil","M_OldWinch",
             "CutYard/M_QuarryWeatheredBed","CutYard/M_QuarryFreshBreak",
             "Quarry_M_OakDry","Quarry_M_BlastFurnace_WroughtIron","Quarry_M_Master_VertexBlend_Base_Triplanar")
for name in (() if os.environ.get("QUARRY_SHED_ONLY")=="1" else render_materials):
    mat=ue.load_asset(kit+"/Materials/"+name)
    if not isinstance(mat,ue.Material):
        raise RuntimeError("Cannot update quarry material "+name)
    changed=False
    for flag in ("used_with_nanite","used_with_instanced_static_meshes"):
        if not mat.get_editor_property(flag):
            mat.set_editor_property(flag,True)
            changed=True
    if changed:
        errors=ue.MaterialEditingLibrary.recompile_material(mat)
        if errors or not assets.save_loaded_asset(mat,False):
            raise RuntimeError(name+" "+str(errors))
ue.log("QUARRY_SHED_AND_RENDER_FLAGS_SAVED")
