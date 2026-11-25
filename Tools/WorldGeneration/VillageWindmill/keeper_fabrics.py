"""Shared cloth settings for the keeper's editable and game-ready wardrobe."""
from keeper_workcloth import panel_paths, save_panels
DEST = "/Game/WorldGeneration/TemperateHills/AbandonedVillage/MillKeeper/WardrobeR3"
MASTER = "/Game/Monsters/WitchRebuilt/Materials/M_WitchRebuilt_Fabric09"


def fabric(rgb, repeats, normal, roughness, variation, color_detail, specular):
    return dict(ClothColor=rgb, WeaveTiling=repeats, RepairWeaveTiling=repeats,
                NormalStrength=normal, Roughness=roughness, RoughnessDetail=variation,
                ColorDetail=color_detail, Specular=specular)


FABRICS = {
    "WorkLinen": fabric((.064, .088, .143), 5.55, .26, .86, .12, .14, .18),
    "NeckLinen": fabric((.084, .109, .156), 1., .23, .88, .11, .13, .16),
    "Skirt": fabric((.113, .076, .055), 23.46, .38, .91, .15, .23, .14),
    "Apron": fabric((.405, .324, .227), 1., .30, .89, .12, .18, .15),
}


def material_paths():
    return {**{name: DEST + "/MI_Keeper_" + name for name in FABRICS}, **panel_paths()}


def save_fabrics():
    import unreal as u
    library = u.MaterialEditingLibrary
    master = u.load_asset(MASTER)
    if not master:
        raise RuntimeError("Missing shared WitchRebuilt fabric")
    result = {}
    for name in FABRICS.keys()-panel_paths().keys():
        path=material_paths()[name]
        instance = u.EditorAssetLibrary.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
        if not instance:
            instance = u.AssetToolsHelpers.get_asset_tools().create_asset(
                path.rsplit("/",1)[1], DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        library.set_material_instance_parent(instance, master)
        for param, value in FABRICS[name].items():
            if param == "ClothColor":
                library.set_material_instance_vector_parameter_value(instance, param, u.LinearColor(*value, 1.))
            else:
                library.set_material_instance_scalar_parameter_value(instance, param, value)
        library.update_material_instance(instance)
        if not u.EditorAssetLibrary.save_loaded_asset(instance, False):
            raise RuntimeError("Could not save " + path)
        result[name] = instance
    result.update(save_panels())
    return result


def author_shader(mat, shader, name, textures):
    import bpy
    settings = FABRICS[name]
    nodes, link = mat.node_tree.nodes, mat.node_tree.links.new

    def math_node(op, left, right):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        for socket, v in zip(n.inputs, (left, right)):
            if isinstance(v, (float, int)):
                socket.default_value = v
            else:
                link(v, socket)
        return n.outputs[0]

    coord = nodes.new("ShaderNodeTexCoord")
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    link(coord.outputs["UV"], scale.inputs[0])
    scale.inputs["Scale"].default_value = settings["WeaveTiling"]
    maps = {}
    for channel in ("N", "R"):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(textures / f"T_Witch_FabricDetail_{channel}.png"), check_existing=True)
        tex.image.colorspace_settings.name = "Non-Color"
        link(scale.outputs[0], tex.inputs["Vector"])
        maps[channel] = tex.outputs["Color"]
    split, join = nodes.new("ShaderNodeSeparateColor"), nodes.new("ShaderNodeCombineColor")
    link(maps["N"], split.inputs[0])
    link(split.outputs["Red"], join.inputs["Red"])
    link(math_node("SUBTRACT", 1., split.outputs["Green"]), join.inputs["Green"])
    link(split.outputs["Blue"], join.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = settings["NormalStrength"]
    link(join.outputs[0], normal.inputs["Color"])
    link(normal.outputs[0], shader.inputs["Normal"])
    deviation = math_node("SUBTRACT", maps["R"], .75)
    rough = math_node("ADD", settings["Roughness"], math_node("MULTIPLY", deviation, settings["RoughnessDetail"]))
    link(rough, shader.inputs["Roughness"])
    tint = nodes.new("ShaderNodeVectorMath")
    tint.operation = "SCALE"
    tint.inputs[0].default_value = settings["ClothColor"]
    link(math_node("ADD", 1., math_node("MULTIPLY", deviation, settings["ColorDetail"])), tint.inputs["Scale"])
    link(tint.outputs[0], shader.inputs["Base Color"])
    shader.inputs["Specular IOR Level"].default_value = settings["Specular"]
