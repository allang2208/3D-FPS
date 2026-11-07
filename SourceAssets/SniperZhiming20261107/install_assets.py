"""Import and save the single shared mesh, surface and gunsmith icon."""
import json
import runpy
import shutil
from pathlib import Path

import unreal as u

source = Path(__file__).resolve().parent / "Exports"
folder = "/Game/Weapons/SniperZhiming"
icons = "/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms"
tools = u.AssetToolsHelpers.get_asset_tools()
library = u.EditorAssetLibrary
editing = u.MaterialEditingLibrary


def save(asset):
    if not library.save_loaded_asset(asset, False):
        raise RuntimeError(f"Could not save {asset.get_path_name()}")


def import_file(name, suffix, where, options=None):
    task = u.AssetImportTask()
    task.filename = str(source / (name + suffix))
    task.destination_name = name
    task.destination_path = where
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    if options:
        task.factory = u.FbxFactory()
        task.options = options
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError(f"Import failed for {name}")
    return u.load_asset(where + "/" + name)


def require_clean(owned):
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty & owned:
        raise RuntimeError("Unsaved edits on the requested appearance: "+str(dirty & owned))
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError("PIE is using the live project; deferred Zhiming appearance import.")


def install_icon():
    key = "muzzle_sniper_zhiming"
    require_clean({icons+"/"+key})
    tex = import_file(key,".png",icons)
    tex.srgb = True
    tex.lod_group = u.TextureGroup.TEXTUREGROUP_UI
    tex.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.never_stream = True
    tex.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(tex)
    staged = Path(u.Paths.project_content_dir()).resolve() / icons.removeprefix("/Game/")
    shutil.copy2(source / (key+".png"), staged / (key+".png"))
    u.log("ZHIMING_ICON_SAVED "+tex.get_path_name())
    return tex


def artwork_packages():
    return {folder+"/"+name for name in ("T_Zhiming_RoundArtwork","T_Zhiming_RoundFinish","M_Zhiming_RoundArtwork")}


def finish_texture(name, srgb):
    texture=import_file(name,".png",folder)
    texture.srgb=srgb
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    texture.compression_settings=u.TextureCompressionSettings.TC_BC7
    texture.set_editor_property("compression_no_alpha",False)
    save(texture)
    return texture


def install_artwork():
    ink=finish_texture("T_Zhiming_RoundArtwork",True)
    finish=finish_texture("T_Zhiming_RoundFinish",False)
    name="M_Zhiming_RoundArtwork"
    layer=(u.load_asset(folder+"/"+name) if library.does_asset_exist(folder+"/"+name)
           else tools.create_asset(name,folder,u.Material,u.MaterialFactoryNew()))
    layer.set_editor_property("blend_mode",u.BlendMode.BLEND_MASKED)
    layer.set_editor_property("opacity_mask_clip_value",.35)
    editing.delete_all_material_expressions(layer)
    sample=editing.create_material_expression(layer,u.MaterialExpressionTextureSample,-700,-220)
    sample.set_editor_property("texture",ink)
    editing.connect_material_property(sample,"RGB",u.MaterialProperty.MP_BASE_COLOR)
    editing.connect_material_property(sample,"A",u.MaterialProperty.MP_OPACITY_MASK)
    packed=editing.create_material_expression(layer,u.MaterialExpressionTextureSample,-700,120)
    packed.set_editor_property("texture",finish)
    packed.set_editor_property("sampler_type",u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    editing.connect_material_property(packed,"A",u.MaterialProperty.MP_ROUGHNESS)
    metal=editing.create_material_expression(layer,u.MaterialExpressionConstant,-220,-200)
    metal.set_editor_property("r",.72)
    editing.connect_material_property(metal,"",u.MaterialProperty.MP_METALLIC)

    # Decode signed tangent normals; Unreal and the Blender source use opposite green signs.
    scale=editing.create_material_expression(layer,u.MaterialExpressionConstant3Vector,-700,420)
    scale.set_editor_property("constant",u.LinearColor(2,-2,2,1))
    multiply=editing.create_material_expression(layer,u.MaterialExpressionMultiply,-430,190)
    editing.connect_material_expressions(packed,"RGB",multiply,"A")
    editing.connect_material_expressions(scale,"",multiply,"B")
    bias=editing.create_material_expression(layer,u.MaterialExpressionConstant3Vector,-430,420)
    bias.set_editor_property("constant",u.LinearColor(-1,1,-1,1))
    normal=editing.create_material_expression(layer,u.MaterialExpressionAdd,-200,190)
    editing.connect_material_expressions(multiply,"",normal,"A")
    editing.connect_material_expressions(bias,"",normal,"B")
    editing.connect_material_property(normal,"",u.MaterialProperty.MP_NORMAL)
    editing.recompile_material(layer)
    save(layer)
    return layer


def install():
    require_clean(artwork_packages()|{folder+"/SM_SniperZhiming",icons+"/muzzle_sniper_zhiming"})
    factory=u.load_asset("/Game/Weapons/M24/Surface20261027/SM_M24_m24_factory_suppressor")
    recess=u.load_asset("/Game/Weapons/SniperSuppressor20261019/M_SniperSuppressor_Recess")
    if not factory or not factory.get_material(0) or not recess:
        raise RuntimeError("Missing the original sniper muzzle material")
    layer=install_artwork()
    flag = "Interchange.FeatureFlags.Import.FBX"
    old = u.SystemLibrary.get_console_variable_int_value(flag)
    try:
        u.SystemLibrary.execute_console_command(None, flag + " 0")
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_as_skeletal = False
        options.import_mesh = True
        options.import_materials = options.import_textures = options.import_animations = False
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.convert_scene_unit = False
        data.import_uniform_scale = 1.
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        mesh = import_file("SM_SniperZhiming", ".fbx", folder, options)
    finally:
        u.SystemLibrary.execute_console_command(None, f"{flag} {old}")
    slots = list(mesh.static_materials)
    materials={"ZhimingGraphite":factory.get_material(0),"Zhiming_Recess":recess,"Zhiming_Inlay":layer}
    for slot in slots:
        key=str(slot.get_editor_property("imported_material_slot_name"))
        if key not in materials:
            key=str(slot.material_slot_name)
        slot.material_interface=materials[key]
    mesh.set_editor_property("static_materials", slots)
    tip = json.loads((source / "mesh.json").read_text())["tip_cm"]
    for label,x in (("MountFace",0.),("Muzzle",tip),("AimGuide",tip+10.)):
        socket = mesh.find_socket(label)
        if not socket:
            socket = u.new_object(u.StaticMeshSocket, outer=mesh)
            socket.set_editor_property("socket_name", label)
            mesh.add_socket(socket)
        socket.set_editor_property("relative_location", u.Vector(x,0,0))
    save(mesh)
    tex=install_icon()
    u.log("ZHIMING_ROUND_ASSETS_SAVED " + mesh.get_path_name() + " " + tex.get_path_name()
          + " factory_finish=" + factory.get_material(0).get_path_name())


if globals().get("ZHIMING_ICON_ONLY"):
    install_icon()
elif globals().get("ZHIMING_ARTWORK_ONLY"):
    require_clean(artwork_packages()|{icons+"/muzzle_sniper_zhiming"})
    layer=install_artwork()
    icon=install_icon()
    u.log("ZHIMING_LIVERY_SAVED "+layer.get_path_name()+" "+icon.get_path_name())
else:
    install()
    if not library.does_asset_exist(folder+"/M_Zhiming_Critical"):
        runpy.run_path(str(source.parent / "install_critical_fx.py"))
