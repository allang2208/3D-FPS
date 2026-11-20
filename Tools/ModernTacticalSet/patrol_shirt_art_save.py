"""Persist the existing armour item's shirt, retained carrier and UI image."""
import gc
import hashlib
import json
from pathlib import Path
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from patrol_shirt_art_render import KEY, ROOT, fingerprint
from ridge_boots_art_save import dynamic, supply_tangent_frames

DEST = "/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/PatrolShirtR2/Display"
E = ue.EditorAssetLibrary
SUB = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
TOOLS = ue.AssetToolsHelpers.get_asset_tools()


def static(geometry,source_hash,name,material_paths):
    path = DEST+"/"+name
    slots = geometry["material_slots"]
    materials = [ue.load_asset(material_paths[slot]) for slot in slots]
    if not all(materials):
        raise RuntimeError("Missing shirt or retained carrier material on "+name)
    asset = E.load_asset(path) if E.does_asset_exist(path) else None
    if asset and E.get_metadata_tag(asset,"EquipmentDefinition")!=KEY:
        raise RuntimeError("Another item is using "+path)
    if not asset or E.get_metadata_tag(asset,"PatrolShirtArtSource")!=source_hash:
        dm = dynamic(geometry)
        if dm.get_triangle_count()!=len(geometry["triangles"]):
            raise RuntimeError("Incomplete folded geometry for "+name)
        supply_tangent_frames(dm)
        if asset:
            options = ue.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,
                        new_material_slot_names=slots,enable_recompute_normals=False,enable_recompute_tangents=False)
            _, outcome = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,asset,options,ue.GeometryScriptMeshWriteLOD())
        else:
            options = ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                         enable_recompute_tangents=False,enable_collision=False)
            asset,outcome = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,options)
        if outcome!=ue.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError("Could not save "+name)
        asset.set_editor_property("static_materials",[ue.StaticMaterial(material_interface=m,material_slot_name=s)
                                                     for s,m in zip(slots,materials)])
        settings = ue.StaticMeshReductionOptions()
        settings.auto_compute_lod_screen_size = False
        settings.reduction_settings = [ue.StaticMeshReductionSettings(percent_triangles=frac,screen_size=size)
                                       for frac,size in ((1.,1.),(.22,.23),(.055,.075))]
        if SUB.set_lods(asset,settings)!=3:
            raise RuntimeError("Unable to construct shirt display distance levels")
        for lod in range(3):
            build = SUB.get_lod_build_settings(asset,lod)
            build.set_editor_property("use_full_precision_u_vs",True)
            build.set_editor_property("use_high_precision_tangent_basis",True)
            build.set_editor_property("recompute_tangents",False)
            SUB.set_lod_build_settings(asset,lod,build)
        E.set_metadata_tag(asset,"EquipmentDefinition",KEY)
        E.set_metadata_tag(asset,"PatrolShirtArtSource",source_hash)
        if not E.save_loaded_asset(asset,False):
            raise RuntimeError("Static asset was not saved: "+path)
    return dict(asset=asset.get_path_name(),source_sha256=source_hash,
                lod_vertices=[SUB.get_number_verts(asset,i) for i in range(SUB.get_lod_count(asset))])


def main():
    art = json.loads((ROOT/"artwork.json").read_bytes())
    digest = fingerprint()
    if art["fingerprint"]!=digest:
        raise RuntimeError("The reference or wearable source changed during the shirt export")
    mats = json.loads((ROOT/"Icons/materials.json").read_bytes())
    output = {}
    for kind in ("display","pickup"):
        raw = (ROOT/art[kind]).read_bytes()
        output[kind] = static(json.loads(raw),hashlib.sha256(raw).hexdigest(),"SM_TS01_PatrolShirt_"+kind.title(),mats)
        del raw
        gc.collect()
        ue.SystemLibrary.collect_garbage()
    image = ROOT/art["standard_icon"]
    task = ue.AssetImportTask()
    task.filename = str(image)
    task.destination_path = DEST
    task.destination_name = "T_TS01_PatrolShirt_Icon"
    task.automated = task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    texture = E.load_asset(DEST+"/"+task.destination_name)
    for key,value in dict(srgb=True,compression_settings=ue.TextureCompressionSettings.TC_EDITOR_ICON,
                          lod_group=ue.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=ue.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():
        texture.set_editor_property(key,value)
    if not E.save_loaded_asset(texture,False):
        raise RuntimeError("Could not persist the 3 x 3 catalogue icon")
    output["texture"] = dict(asset=texture.get_path_name(),source_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    output["fingerprint"] = digest
    (ROOT/"artwork-saved.json").write_text(json.dumps(output,indent=2),encoding="utf8")
    print("PATROL_SHIRT_INVENTORY_SAVED",digest,flush=True)


if __name__=="__main__":
    main()
