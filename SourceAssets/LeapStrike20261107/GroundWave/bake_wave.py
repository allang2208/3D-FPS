"""Build the leap landing's raised annulus and translucent pressure-front material."""
import math
from pathlib import Path

import unreal as u


DEST = "/Game/Weapons/SteelWarhammer20261014/LeapStrikeV2"
MAT_NAME = "M_LeapGroundWave"
MESH_NAME = "SM_LeapGroundWave"
editing = u.MaterialEditingLibrary
library = u.EditorAssetLibrary


def existing(name):
    path = f"{DEST}/{name}"
    return u.load_asset(path) if library.does_asset_exist(path) else None


def save(asset):
    if not library.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"Could not save {asset.get_path_name()}")
    u.log(f"LEAP_GROUND_WAVE saved {asset.get_path_name()}")


def material():
    mat = existing(MAT_NAME) or u.AssetToolsHelpers.get_asset_tools().create_asset(
        MAT_NAME, DEST, u.Material, u.MaterialFactoryNew())
    editing.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("disable_depth_test", False)
    mat.set_editor_property("allow_front_layer_translucency", False)

    def node(cls):
        return editing.create_material_expression(mat, cls)

    def wire(source, target, pin):
        if not editing.connect_material_expressions(source, "", target, pin):
            raise RuntimeError(f"Could not connect {pin}")

    uv = node(u.MaterialExpressionTextureCoordinate)
    fade = node(u.MaterialExpressionScalarParameter)
    fade.set_editor_property("parameter_name", "Opacity")
    fade.set_editor_property("default_value", 1.0)
    profile = node(u.MaterialExpressionCustom)
    profile.set_editor_property("output_type", u.CustomMaterialOutputType.CMOT_FLOAT4)
    inputs = []
    for name in ("UV", "Fade"):
        pin = u.CustomInput()
        pin.set_editor_property("input_name", name)
        inputs.append(pin)
    profile.set_editor_property("inputs", inputs)
    profile.set_editor_property("code", Path(__file__).with_name("pressure_front.hlsl").read_text(encoding="utf-8"))
    wire(uv, profile, "UV")
    wire(fade, profile, "Fade")
    rgb = node(u.MaterialExpressionComponentMask)
    alpha = node(u.MaterialExpressionComponentMask)
    for mask, channels in ((rgb, "rgb"), (alpha, "a")):
        for channel in "rgba":
            mask.set_editor_property(channel, channel in channels)
        wire(profile, mask, "")
    transmittance = node(u.MaterialExpressionOneMinus)
    wire(alpha, transmittance, "")
    surface = node(u.MaterialExpressionSubstrateUnlitBSDF)
    wire(rgb, surface, "EmissiveColor")
    wire(transmittance, surface, "TransmittanceColor")
    if not editing.connect_material_property(surface, "", u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Could not connect the Substrate surface")
    editing.layout_material_expressions(mat)
    errors = editing.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat


def wave_mesh(mat):
    # XY scales with the native 50 cm unit radius. Heights stay in centimetres.
    section = [(0.62, 0.2), (0.75, 1.3), (0.86, 3.1), (0.93, 4.8), (0.967, 2.9), (1.0, 0.2)]
    sectors = 96
    vertices, uv, triangles = [], [], []
    for i in range(sectors + 1):
        angle = math.tau * i / sectors
        crest_height = 1.0 + 0.17 * math.sin(7*angle) + 0.10 * math.sin(13*angle)
        for radius, height in section:
            vertices.append(u.Vector(50*radius*math.cos(angle), 50*radius*math.sin(angle), height*crest_height))
            uv.append(u.Vector2D(i / sectors, radius))
    for i in range(sectors):
        for j in range(len(section)-1):
            a = i*len(section) + j
            b = a + len(section)
            triangles.extend([u.IntVector(a, b, a+1), u.IntVector(a+1, b, b+1)])
    mesh = u.DynamicMesh()
    buffers = u.GeometryScriptSimpleMeshBuffers(vertices=vertices, uv0=uv, triangles=triangles)
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh, buffers, 0, True)
    asset = existing(MESH_NAME)
    if asset:
        _, result = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
            mesh, asset, u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True, enable_recompute_tangents=True),
            u.GeometryScriptMeshWriteLOD(lod_index=0))
    else:
        asset, result = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
            mesh, f"{DEST}/{MESH_NAME}", u.GeometryScriptCreateNewStaticMeshAssetOptions(
                enable_recompute_normals=True, enable_recompute_tangents=True, enable_collision=False))
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Could not build the leap ground-wave mesh")
    asset.set_editor_property("static_materials", [u.StaticMaterial(material_interface=mat, material_slot_name="Wave")])
    save(asset)


if __name__ == "__main__":
    wave_mesh(material())
