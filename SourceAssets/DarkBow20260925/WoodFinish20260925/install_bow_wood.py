"""Replace the dark-bow riser/arrow flat Phong with shared Normandy wood scans.

The original Fab bow uses three near-black FBX Phong instances. Slot 2 has
collapsed UVs (uv area 0), so any UV0 wood wrap would sample one texel.
First-person grain must lock to the bow: LocalPosition triplanar, not WorldPosition
(voxel wood swims when the weapon moves). Textures are the existing
T_WoodSurface_00A_* objects — no new texture data.

    powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 `
        -PythonScript SourceAssets/DarkBow20260925/WoodFinish20260925/install_bow_wood.py `
        -QueueWaitSeconds 180
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
DEST = "/Game/Weapons/DarkBow20260925/ArmsV2/Materials"
RISER = "/Game/Weapons/DarkBow20260925/ArmsV2/SM_DarkBow_Riser"
ARROW = "/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow"
NORM = "/Game/UnrealNormandy/Textures"
MASTER_NAME = "M_BowWood_LocalScan"
EAL = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL.make_directory(DEST)


def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError("missing " + path)
    return asset


def save_asset(asset):
    asset.modify()
    pkg = asset.get_package()
    if not u.EditorLoadingAndSavingUtils.save_packages([pkg], False):
        if not EAL.save_loaded_asset(asset, False):
            raise RuntimeError("save failed " + asset.get_path_name())
    return asset.get_path_name()


def node(mat, cls, **props):
    result = L.create_material_expression(mat, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin, output=""):
    names = [str(n) for n in (L.get_material_expression_input_names(target) or [])]
    if pin not in names:
        if pin in ("Input", "", "none") and names:
            pin = names[0]
        elif names:
            raise RuntimeError("pin %s not in %s" % (pin, names))
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError(
            "connect failed %s -> %s.%s"
            % (source.get_class().get_name(), target.get_class().get_name(), pin)
        )


def prop(source, name, output=""):
    if not L.connect_material_property(source, output, getattr(u.MaterialProperty, "MP_" + name)):
        raise RuntimeError("output failed " + name)


def scalar(mat, name, value):
    return node(
        mat,
        u.MaterialExpressionScalarParameter,
        parameter_name=name,
        default_value=float(value),
    )


def vector(mat, name, rgb):
    return node(
        mat,
        u.MaterialExpressionVectorParameter,
        parameter_name=name,
        default_value=u.LinearColor(rgb[0], rgb[1], rgb[2], 1.0),
    )


def custom(mat, code, inputs, size):
    result = node(mat, u.MaterialExpressionCustom)
    result.set_editor_property("code", code)
    result.set_editor_property(
        "output_type", getattr(u.CustomMaterialOutputType, "CMOT_FLOAT" + str(size))
    )
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property("input_name", name)
        pins.append(pin)
    result.set_editor_property("inputs", pins)
    for name, source in inputs.items():
        wire(source, result, name)
    return result


def describe_material(path):
    asset = u.load_asset(path)
    if asset is None:
        return {"path": path, "missing": True}
    info = {
        "path": asset.get_path_name(),
        "class": asset.get_class().get_name(),
        "two_sided": bool(asset.get_editor_property("two_sided"))
        if asset.get_class().get_name() == "Material"
        else None,
    }
    parent = None
    try:
        parent = asset.get_editor_property("parent")
    except Exception:
        parent = None
    if parent:
        info["parent"] = parent.get_path_name()
        try:
            info["parent_two_sided"] = bool(parent.get_editor_property("two_sided"))
        except Exception:
            info["parent_two_sided"] = None
    textures = {}
    try:
        for item in asset.get_editor_property("texture_parameter_values") or []:
            pname = str(item.get_editor_property("parameter_info").get_editor_property("name"))
            value = item.get_editor_property("parameter_value")
            textures[pname] = value.get_path_name() if value else None
    except Exception as error:
        textures["error"] = str(error)
    info["textures"] = textures
    return info


def describe_mesh(path):
    mesh = load(path)
    slots = []
    for index, slot in enumerate(mesh.static_materials):
        material = slot.material_interface
        slots.append(
            {
                "index": index,
                "name": str(slot.material_slot_name),
                "material": material.get_path_name() if material else None,
            }
        )
    bounds = mesh.get_bounds()
    return {
        "path": mesh.get_path_name(),
        "slots": slots,
        "box_extent": [round(bounds.box_extent.x, 3), round(bounds.box_extent.y, 3), round(bounds.box_extent.z, 3)],
        "origin": [round(bounds.origin.x, 3), round(bounds.origin.y, 3), round(bounds.origin.z, 3)],
    }


def build_master():
    path = DEST + "/" + MASTER_NAME
    mat = u.load_asset(path)
    created = False
    if mat is None:
        mat = TOOLS.create_asset(MASTER_NAME, DEST, u.Material, u.MaterialFactoryNew())
        created = True
    expressions = list(L.get_material_expressions(mat) or [])
    if expressions:
        return mat, False, len(expressions)
    mat.set_editor_property("two_sided", False)
    mat.set_editor_property("tangent_space_normal", False)

    position = node(
        mat,
        u.MaterialExpressionLocalPosition,
        local_origin=u.LocalPositionOrigin.PRIMITIVE,
        included_offsets=u.PositionIncludedOffsets.EXCLUDE_OFFSETS,
    )
    normal_ws = node(mat, u.MaterialExpressionVertexNormalWS)
    normal_local = node(
        mat,
        u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_LOCAL,
    )
    wire(normal_ws, normal_local, "Input")

    scale = scalar(mat, "TileCm", 55.0)
    offset_u = scalar(mat, "OffsetU", 0.0)
    offset_v = scalar(mat, "OffsetV", 0.0)
    tint = vector(mat, "Tint", (0.48, 0.34, 0.22))
    ao_strength = scalar(mat, "AOStrength", 0.55)
    rough_bias = scalar(mat, "RoughBias", 0.04)
    normal_strength = scalar(mat, "NormalStrength", 0.55)
    specular = scalar(mat, "Specular", 0.32)

    weights = custom(
        mat,
        "float3 w=pow(abs(normalize(N)),4); return w/max(w.x+w.y+w.z,0.0001);",
        {"N": normal_local},
        3,
    )
    # Grain along local Z (limb length). U = Z, V = the plane's other axis.
    uv = {
        "X": custom(
            mat,
            "return float2(P.z, P.y)/max(Scale,1.0)+float2(OU,OV);",
            {"P": position, "Scale": scale, "OU": offset_u, "OV": offset_v},
            2,
        ),
        "Y": custom(
            mat,
            "return float2(P.z, P.x)/max(Scale,1.0)+float2(OU,OV);",
            {"P": position, "Scale": scale, "OU": offset_u, "OV": offset_v},
            2,
        ),
        "Z": custom(
            mat,
            "return float2(P.x, P.y)/max(Scale,1.0)+float2(OU,OV);",
            {"P": position, "Scale": scale, "OU": offset_u, "OV": offset_v},
            2,
        ),
    }
    textures = {
        "BaseColor": (
            load(NORM + "/T_WoodSurface_00A_BaseColor"),
            u.MaterialSamplerType.SAMPLERTYPE_COLOR,
        ),
        "Normal": (
            load(NORM + "/T_WoodSurface_00A_Normal"),
            u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        ),
        "RHAOM": (
            load(NORM + "/T_WoodSurface_00A_RHAOM"),
            u.MaterialSamplerType.SAMPLERTYPE_MASKS,
        ),
    }
    samples = {}
    for suffix, (texture, sampler) in textures.items():
        planes = {}
        for axis in ("X", "Y", "Z"):
            sample = node(mat, u.MaterialExpressionTextureSample)
            sample.set_editor_property("texture", texture)
            sample.set_editor_property("sampler_type", sampler)
            wire(uv[axis], sample, "UVs")
            planes[axis] = sample
        samples[suffix] = planes

    def blended(planes):
        return custom(mat, "return X*W.x+Y*W.y+Z*W.z;", dict(planes, W=weights), 3)

    color = custom(
        mat,
        "float m=0.97+0.03*sin(P.z*0.045+sin(P.x*0.08)+P.y*0.11);"
        "float ao=lerp(1.0, saturate(M.b), saturate(AO));"
        "return C*T*m*ao;",
        {
            "C": blended(samples["BaseColor"]),
            "T": tint,
            "P": position,
            "M": blended(samples["RHAOM"]),
            "AO": ao_strength,
        },
        3,
    )
    rough = custom(
        mat,
        "return saturate(M.r+Bias);",
        {"M": blended(samples["RHAOM"]), "Bias": rough_bias},
        1,
    )
    # Reconstruct the scan's tangent detail in local space, then to world.
    local_n = custom(
        mat,
        "float3 n=normalize(N);"
        "float3 dx=float3(0,X.y,X.x)/max(X.z,0.2);"
        "float3 dy=float3(Y.y,0,Y.x)/max(Y.z,0.2);"
        "float3 dz=float3(Z.x,Z.y,0)/max(Z.z,0.2);"
        "float3 d=(dx*W.x+dy*W.y+dz*W.z)*Strength;"
        "return normalize(n+d-n*dot(d,n));",
        dict(samples["Normal"], N=normal_local, W=weights, Strength=normal_strength),
        3,
    )
    world_n = node(
        mat,
        u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD,
    )
    wire(local_n, world_n, "Input")
    metal = node(mat, u.MaterialExpressionConstant, r=0.0)

    prop(color, "BASE_COLOR")
    prop(world_n, "NORMAL")
    prop(rough, "ROUGHNESS")
    prop(metal, "METALLIC")
    prop(specular, "SPECULAR")
    L.layout_material_expressions(mat)
    errors = L.recompile_material(mat)
    if isinstance(errors, (list, tuple)) and errors:
        raise RuntimeError("master compile failed: " + str(errors))

    samplers = {}
    for expression in L.get_material_expressions(mat) or []:
        if "TextureSample" in expression.get_class().get_name():
            texture = expression.get_editor_property("texture")
            samplers[texture.get_name() if texture else "?"] = expression.get_editor_property(
                "sampler_type"
            )
    expected = {
        "T_WoodSurface_00A_BaseColor": u.MaterialSamplerType.SAMPLERTYPE_COLOR,
        "T_WoodSurface_00A_Normal": u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        "T_WoodSurface_00A_RHAOM": u.MaterialSamplerType.SAMPLERTYPE_MASKS,
    }
    for name, wanted in expected.items():
        if samplers.get(name) != wanted:
            raise RuntimeError("sampler %s is %s not %s" % (name, samplers.get(name), wanted))
    save_asset(mat)
    return mat, created or True, len(L.get_material_expressions(mat) or [])


def make_instance(name, parent, scalars, tint):
    path = DEST + "/" + name
    instance = u.load_asset(path)
    if instance is None:
        instance = TOOLS.create_asset(
            name, DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew()
        )
    instance.set_editor_property("parent", parent)
    instance.modify()
    for key, value in scalars.items():
        L.set_material_instance_scalar_parameter_value(instance, key, float(value))
    L.set_material_instance_vector_parameter_value(
        instance, "Tint", u.LinearColor(tint[0], tint[1], tint[2], 1.0)
    )
    L.update_material_instance(instance)
    save_asset(instance)
    back = {"scalars": {}, "vectors": {}, "parent": instance.get_editor_property("parent").get_path_name()}
    for item in instance.get_editor_property("scalar_parameter_values") or []:
        back["scalars"][str(item.get_editor_property("parameter_info").get_editor_property("name"))] = (
            item.get_editor_property("parameter_value")
        )
    for item in instance.get_editor_property("vector_parameter_values") or []:
        value = item.get_editor_property("parameter_value")
        back["vectors"][str(item.get_editor_property("parameter_info").get_editor_property("name"))] = [
            round(value.r, 4),
            round(value.g, 4),
            round(value.b, 4),
        ]
    for key, value in scalars.items():
        if abs(float(back["scalars"].get(key, -999)) - float(value)) > 1e-4:
            raise RuntimeError("instance %s scalar %s not written" % (name, key))
    written = back["vectors"].get("Tint")
    if not written or any(abs(a - b) > 1e-3 for a, b in zip(written, tint)):
        raise RuntimeError("instance %s tint not written: %s" % (name, written))
    return instance, back


def bind_mesh(path, mapping):
    mesh = load(path)
    slots = list(mesh.static_materials)
    before = [
        {
            "index": i,
            "name": str(slot.material_slot_name),
            "material": slot.material_interface.get_path_name() if slot.material_interface else None,
        }
        for i, slot in enumerate(slots)
    ]
    for index, material in mapping.items():
        if index >= len(slots):
            raise RuntimeError("%s missing slot %s" % (path, index))
        mesh.set_material(index, material)
        slot = slots[index]
        slot.set_editor_property("material_interface", material)
        slots[index] = slot
    mesh.set_editor_property("static_materials", slots)
    save_asset(mesh)
    after = []
    for index, slot in enumerate(list(mesh.static_materials)):
        material = slot.material_interface
        after.append(
            {
                "index": index,
                "name": str(slot.material_slot_name),
                "material": material.get_path_name() if material else None,
            }
        )
        if index in mapping and (not material or material.get_path_name() != mapping[index].get_path_name()):
            raise RuntimeError(
                "bind failed %s[%s] -> %s"
                % (path, index, material.get_path_name() if material else None)
            )
    return {"before": before, "after": after}


def main():
    receipt = {
        "runtime_tested": False,
        "shared_textures": [
            NORM + "/T_WoodSurface_00A_BaseColor",
            NORM + "/T_WoodSurface_00A_RHAOM",
            NORM + "/T_WoodSurface_00A_Normal",
        ],
        "diagnosis": {
            "original_riser": describe_mesh(RISER),
            "original_arrow": describe_mesh(ARROW),
            "original_materials": {
                name: describe_material("/Game/Weapons/DarkBow20260925/" + name)
                for name in ("Material_003", "Material_005", "Material_002")
            },
            "notes": [
                "Original Fab sections are three near-black FBX Phong instances, no wood albedo.",
                "Slot 2 has collapsed UV0 (area 0) so UV-based wood would be a single texel.",
                "Grain uses LocalPosition so first-person aim does not swim the scan.",
            ],
        },
    }
    master, rebuilt, expression_count = build_master()
    receipt["master"] = {
        "path": master.get_path_name(),
        "rebuilt": rebuilt,
        "expressions": expression_count,
        "tangent_space_normal": bool(master.get_editor_property("tangent_space_normal")),
    }
    variants = {
        "MI_BowWood_Body": (
            {"TileCm": 55.0, "OffsetU": 0.0, "OffsetV": 0.0, "RoughBias": 0.04, "NormalStrength": 0.55, "AOStrength": 0.55},
            (0.48, 0.34, 0.22),
        ),
        "MI_BowWood_Limb": (
            {"TileCm": 50.0, "OffsetU": 0.37, "OffsetV": 0.18, "RoughBias": 0.02, "NormalStrength": 0.6, "AOStrength": 0.5},
            (0.62, 0.44, 0.28),
        ),
        "MI_BowWood_Inlay": (
            {"TileCm": 35.0, "OffsetU": 0.61, "OffsetV": 0.44, "RoughBias": 0.10, "NormalStrength": 0.45, "AOStrength": 0.65},
            (0.30, 0.20, 0.13),
        ),
        "MI_BowWood_Arrow": (
            {"TileCm": 40.0, "OffsetU": 0.19, "OffsetV": 0.07, "RoughBias": 0.03, "NormalStrength": 0.5, "AOStrength": 0.45},
            (0.70, 0.48, 0.28),
        ),
    }
    instances = {}
    receipt["instances"] = {}
    for name, (scalars, tint) in variants.items():
        instance, back = make_instance(name, master, scalars, tint)
        instances[name] = instance
        receipt["instances"][name] = back
        receipt["instances"][name]["path"] = instance.get_path_name()

    arrow_wood_index = None
    for index, slot in enumerate(load(ARROW).static_materials):
        if "Wood" in str(slot.material_slot_name):
            arrow_wood_index = index
            break
    if arrow_wood_index is None:
        raise RuntimeError("arrow has no Wood slot")

    receipt["binds"] = {
        "riser": bind_mesh(
            RISER,
            {
                0: instances["MI_BowWood_Body"],
                1: instances["MI_BowWood_Limb"],
                2: instances["MI_BowWood_Inlay"],
            },
        ),
        "arrow": bind_mesh(ARROW, {arrow_wood_index: instances["MI_BowWood_Arrow"]}),
    }
    (HERE / "wood_finish_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("BOW_WOOD_FINISH_SAVED", json.dumps({"master": receipt["master"]["path"], "instances": list(instances)}), flush=True)


if __name__ == "__main__":
    import runpy

    runpy.run_path(str(HERE / "recolor_structure_woods.py"), run_name="__main__")
