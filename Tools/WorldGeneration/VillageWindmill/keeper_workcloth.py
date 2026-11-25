"""Authoring and UE bindings for the keeper's two individually cut cloth panels."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3]/"SourceAssets/HillsVillageWindmill/MillKeeper/CharacterR1/WorkwearR4"
DEST = "/Game/WorldGeneration/TemperateHills/AbandonedVillage/MillKeeper/WorkwearR4"
PANEL_NAMES = ("Apron","SkirtPanels")
CHANNELS = ("Color","Normal","Roughness")


def texture_name(panel,channel):
    return "T_Keeper_"+panel+"_"+channel


def panel_paths():
    return {panel: DEST+"/MI_Keeper_"+panel for panel in PANEL_NAMES}


def pocket_uv(u,v):
    # Lower corners are cut on the bias. The opening pitches towards the hand.
    clip=.036*max(0.,(v-.80)/.20)
    return .512+clip+(.35-2.*clip)*u, .245-.026*u+(.228+.026*u)*v


def bind_blender(mat,shader,panel):
    import bpy
    tree=mat.node_tree
    for channel in CHANNELS:
        name=texture_name(panel,channel)
        tex=tree.nodes.new("ShaderNodeTexImage")
        tex.image=bpy.data.images.load(str(SOURCE/(name+".png")),check_existing=True)
        target={"Color":"Base Color","Normal":"Normal","Roughness":"Roughness"}[channel]
        if channel!="Color":
            tex.image.colorspace_settings.name="Non-Color"
        socket=tex.outputs["Color"]
        if channel=="Normal":
            normal=tree.nodes.new("ShaderNodeNormalMap")
            tree.links.new(socket,normal.inputs["Color"])
            socket=normal.outputs["Normal"]
        tree.links.new(socket,shader.inputs[target])
    shader.inputs["Specular IOR Level"].default_value=.17


def save_panels():
    import unreal as u
    lib=u.EditorAssetLibrary
    edit=u.MaterialEditingLibrary
    tools=u.AssetToolsHelpers.get_asset_tools()

    def save(obj):
        if not obj or not lib.save_loaded_asset(obj,False):
            raise RuntimeError("Failed to save keeper cloth asset "+str(obj))

    textures={}
    for panel in PANEL_NAMES:
        textures[panel]={}
        for channel in CHANNELS:
            name=texture_name(panel,channel)
            task=u.AssetImportTask()
            task.filename=str(SOURCE/(name+".png"))
            task.destination_path=DEST+"/Textures"
            task.replace_existing=True
            task.automated=True
            task.factory=u.TextureFactory()
            tools.import_asset_tasks([task])
            tex=lib.load_asset(DEST+"/Textures/"+name)
            tex.srgb=channel=="Color"
            if channel=="Normal":
                tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
                tex.flip_green_channel=True  # The author PNG uses OpenGL tangent Y.
            elif channel=="Roughness":
                tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
            save(tex)
            textures[panel][channel]=tex
    name="M_Keeper_Workcloth"
    master=lib.load_asset(DEST+"/"+name) if lib.does_asset_exist(DEST+"/"+name) else tools.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    edit.delete_all_material_expressions(master)
    edit.set_material_usage(master,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    master.set_editor_property("two_sided",True)
    slab=edit.create_material_expression(master,u.MaterialExpressionSubstrateShadingModels)
    for channel,sampler,pin in [
            ("Color",u.MaterialSamplerType.SAMPLERTYPE_COLOR,"BaseColor"),
            ("Normal",u.MaterialSamplerType.SAMPLERTYPE_NORMAL,"Normal"),
            ("Roughness",u.MaterialSamplerType.SAMPLERTYPE_MASKS,"Roughness")]:
        node=edit.create_material_expression(master,u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property("parameter_name",channel)
        node.set_editor_property("texture",textures["Apron"][channel])
        node.set_editor_property("sampler_type",sampler)
        if not edit.connect_material_expressions(node,"R" if channel=="Roughness" else "RGB",slab,pin):
            raise ValueError("Could not bind "+pin)
    spec=edit.create_material_expression(master,u.MaterialExpressionConstant)
    spec.set_editor_property("r",.17)
    edit.connect_material_expressions(spec,"",slab,"Specular")
    edit.connect_material_property(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL)
    edit.recompile_material(master)
    save(master)
    result={}
    for panel,path in panel_paths().items():
        mi=lib.load_asset(path) if lib.does_asset_exist(path) else tools.create_asset(path.rsplit("/",1)[1],DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        edit.set_material_instance_parent(mi,master)
        for channel,tex in textures[panel].items():
            edit.set_material_instance_texture_parameter_value(mi,channel,tex)
        edit.update_material_instance(mi)
        save(mi)
        result[panel]=mi
    return result
