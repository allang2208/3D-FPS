"""Author the innkeeper surface and character in an isolated UE 5.8 project."""
import json
import os
from pathlib import Path

import unreal as ue


PROJECT = Path(__file__).resolve().parents[3]
BODY = PROJECT / "SourceAssets/VillageTavernKeeper/FullBody"
OUT = BODY / "UEAuthoringR1"
DEST = "/Game/Characters/VillageTavernKeeper"
MATERIAL_PATH = DEST + "/Materials/M_TavernKeeper"
LIB = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
MEL = ue.MaterialEditingLibrary
saved = []


def store(asset):
    if not asset or not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + str(asset))
    saved.append(asset.get_path_name().split(".")[0])


def import_asset(source, folder, name, factory, options=None):
    task = ue.AssetImportTask()
    task.filename = str(source)
    task.destination_name = name
    task.destination_path = folder
    task.factory = factory
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    path = folder + "/" + name
    if not LIB.does_asset_exist(path):
        raise RuntimeError("Import did not produce " + path + " from " + str(source))
    return ue.load_asset(path)


def surface():
    tex_dir = BODY / "MeshyR1/Textures"
    source_maps = [
        ("Color", tex_dir / "M0_base_color.png", ue.TextureCompressionSettings.TC_DEFAULT, ue.MaterialSamplerType.SAMPLERTYPE_COLOR),
        ("Normal", tex_dir / "M0_normal.png", ue.TextureCompressionSettings.TC_NORMALMAP, ue.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        ("ORM", OUT / "T_TavernKeeper_ORM.png", ue.TextureCompressionSettings.TC_MASKS, ue.MaterialSamplerType.SAMPLERTYPE_MASKS),
    ]
    if LIB.does_asset_exist(MATERIAL_PATH):
        mat = ue.load_asset(MATERIAL_PATH)
        MEL.delete_all_material_expressions(mat)
    else:
        mat = TOOLS.create_asset("M_TavernKeeper", DEST + "/Materials", ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_property("two_sided", True)
    MEL.set_material_usage(mat, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab = MEL.create_material_expression(mat, ue.MaterialExpressionSubstrateShadingModels, -250, 0)
    for row, (role, path, compression, sampler) in enumerate(source_maps):
        tex = import_asset(path, DEST + "/Textures", "T_TavernKeeper_" + role, ue.TextureFactory())
        tex.set_editor_property("compression_settings", compression)
        tex.set_editor_property("srgb", role == "Color")
        tex.set_editor_property("lod_group", ue.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if role == "Normal" else ue.TextureGroup.TEXTUREGROUP_CHARACTER)
        if role == "Normal":
            # Meshy glTF normals use +Y tangent space. Unreal samples DirectX tangent space.
            tex.set_editor_property("flip_green_channel", True)
        store(tex)
        node = MEL.create_material_expression(mat, ue.MaterialExpressionTextureSample, -650, 280 * row - 280)
        node.texture = tex
        node.sampler_type = sampler
        pins = {"Color": [("RGB", "BaseColor")], "Normal": [("RGB", "Normal")],
                "ORM": [("G", "Roughness"), ("B", "Metallic")]}
        for channel, pin in pins[role]:
            if not MEL.connect_material_expressions(node, channel, slab, pin):
                raise RuntimeError("Could not bind " + role + " to " + pin)
    if not MEL.connect_material_property(slab, "", ue.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Could not bind the surface")
    MEL.recompile_material(mat)
    store(mat)


def character():
    mat = ue.load_asset(MATERIAL_PATH)
    if not mat:
        raise RuntimeError("Create the innkeeper material before importing her rig.")
    ue.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    ui = ue.FbxImportUI()
    ui.automated_import_should_detect_type = False
    ui.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_as_skeletal = True
    ui.import_mesh = True
    ui.import_materials = False
    ui.import_textures = False
    ui.import_animations = False
    ui.create_physics_asset = False
    data = ui.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = False
    data.set_editor_property("bUseT0AsRefPose", False)
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh = import_asset(OUT / "SK_TavernKeeper.fbx", DEST, "SK_TavernKeeper", ue.FbxFactory(), ui)
    slots = list(mesh.materials)
    for slot in slots:
        slot.material_interface = mat
    mesh.set_editor_property("materials", slots)
    store(mesh.skeleton)
    store(mesh)


stage = os.environ["TAVERN_KEEPER_IMPORT_STAGE"]
if stage == "surface":
    surface()
elif stage == "character":
    character()
else:
    raise ValueError("Unknown stage: " + stage)
(OUT / (stage + "_saved.json")).write_text(json.dumps(saved, indent=2), encoding="utf-8")
print("TAVERN_KEEPER_SAVED " + stage, flush=True)
