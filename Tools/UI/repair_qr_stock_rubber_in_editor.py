"""Recover the QR performance stock rubber roughness link inside the running editor.

The headless repair could not save this asset because the interactive editor holds the
package open, so the same authored connection is applied through the editor that owns it:

    SourceAssets/MeshyPerformanceStock20260913/import_assets.py
        sample(T_Stock_Roughness).R -> Clamp(0.75..1) -> MP_ROUGHNESS

Only MaterialEditingLibrary entry points that already ran safely in this session are used,
and the asset is saved only after the material compiles without errors.
"""
import unreal

PATH = "/Game/Weapons/QRPerformanceStock/Meshy20260913/M_Stock_Rubber"
TOKEN = "T_Stock_Roughness"
CHANNEL = "R"

LIB = unreal.MaterialEditingLibrary

material = unreal.load_asset(PATH)
if not material:
    raise RuntimeError("missing asset: " + PATH)

before = list(LIB.recompile_material(material) or [])
unreal.log("QR_RUBBER_EDITOR before=" + "; ".join(before))
if not before:
    unreal.log("QR_RUBBER_EDITOR skip: material already compiles")
else:
    clamp = None
    sample = None
    for node in LIB.get_material_expressions(material):
        name = node.get_class().get_name()
        if name == "MaterialExpressionClamp" and clamp is None:
            clamp = node
        if name == "MaterialExpressionTextureSample":
            texture = node.get_editor_property("texture")
            if texture and TOKEN in texture.get_name():
                sample = node
    if clamp is None or sample is None:
        raise RuntimeError("expected clamp/texture sample not found (clamp=%s sample=%s)"
                           % (clamp is not None, sample is not None))
    linked = LIB.connect_material_expressions(sample, CHANNEL, clamp, "Input")
    if not linked:
        linked = LIB.connect_material_expressions(sample, CHANNEL, clamp, "")
    if not linked:
        raise RuntimeError("connect_material_expressions was refused")
    after = list(LIB.recompile_material(material) or [])
    unreal.log("QR_RUBBER_EDITOR after=" + ("; ".join(after) if after else "<clean>"))
    if after:
        raise RuntimeError("material still reports: " + "; ".join(after))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError("save_loaded_asset failed")
    unreal.log("QR_RUBBER_EDITOR saved " + material.get_path_name())

unreal.log("QR_RUBBER_EDITOR COMPLETE")
