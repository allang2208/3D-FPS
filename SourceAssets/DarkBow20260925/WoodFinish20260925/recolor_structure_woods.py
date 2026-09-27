"""Restain bow structure slots as distinct woods without rebuilding the live master.

The first wood pass multiplied one walnut scan by similar browns and a heavy AO
term, so Body / Limb / Inlay read as one muddy material. This pass adds
M_BowWood_LocalScanV2: local triplanar (grain locked to the bow) plus luminance
stain so each instance can pick a real wood color. Existing MI_BowWood_* paths
are kept and reparented. Original Fab Phong and M_BowWood_LocalScan stay on disk.
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
DEST = "/Game/Weapons/DarkBow20260925/ArmsV2/Materials"
RISER = "/Game/Weapons/DarkBow20260925/ArmsV2/SM_DarkBow_Riser"
RISER_DETAIL = "/Game/Weapons/DarkBow20260925/RiserDetail20260925/SM_DarkBow_RiserDetail"
ARROW = "/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow"
NORM = "/Game/UnrealNormandy/Textures"
MASTER_NAME = "M_BowWood_LocalScanV2"
WOOD = {
    "BaseColor": NORM + "/T_WoodSurface_00A_BaseColor",
    "Normal": NORM + "/T_WoodSurface_00A_Normal",
    "RHAOM": NORM + "/T_WoodSurface_00A_RHAOM",
}
ROTTEN = {
    "BaseColor": NORM + "/T_RottenWoodSurface_00A_BaseColor",
    "Normal": NORM + "/T_RottenWoodSurface_00A_Normal",
    "RHAOM": NORM + "/T_RottenWoodSurface_00A_RHAOM",
}
EAL = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL.make_directory(DEST)

# Target stains are the wood color, not multipliers on the already-brown scan.
# Body = walnut riser, Limb = honey maple, Inlay = rosewood, Arrow = pale ash.
VARIANTS = {
    "MI_BowWood_Body": {
        "textures": ROTTEN,
        "tint": (0.34, 0.18, 0.09),
        "scalars": {
            "TileCm": 26.0,
            "OffsetU": 0.08,
            "OffsetV": 0.04,
            "Contrast": 1.35,
            "Saturation": 1.12,
            "ScanMix": 0.16,
            "Brightness": 1.05,
            "AOStrength": 0.18,
            "RoughBias": 0.08,
            "NormalStrength": 0.62,
            "Specular": 0.28,
        },
    },
    "MI_BowWood_Limb": {
        "textures": WOOD,
        "tint": (0.86, 0.58, 0.26),
        "scalars": {
            "TileCm": 20.0,
            "OffsetU": 0.41,
            "OffsetV": 0.19,
            "Contrast": 1.22,
            "Saturation": 1.28,
            "ScanMix": 0.10,
            "Brightness": 1.18,
            "AOStrength": 0.10,
            "RoughBias": -0.02,
            "NormalStrength": 0.70,
            "Specular": 0.36,
        },
    },
    "MI_BowWood_Inlay": {
        "textures": WOOD,
        "tint": (0.46, 0.11, 0.08),
        "scalars": {
            "TileCm": 12.0,
            "OffsetU": 0.67,
            "OffsetV": 0.52,
            "Contrast": 1.42,
            "Saturation": 1.22,
            "ScanMix": 0.08,
            "Brightness": 0.92,
            "AOStrength": 0.16,
            "RoughBias": 0.02,
            "NormalStrength": 0.48,
            "Specular": 0.40,
        },
    },
    "MI_BowWood_Arrow": {
        "textures": WOOD,
        "tint": (0.90, 0.68, 0.38),
        "scalars": {
            "TileCm": 16.0,
            "OffsetU": 0.22,
            "OffsetV": 0.11,
            "Contrast": 1.16,
            "Saturation": 1.10,
            "ScanMix": 0.14,
            "Brightness": 1.12,
            "AOStrength": 0.12,
            "RoughBias": 0.00,
            "NormalStrength": 0.52,
            "Specular": 0.30,
        },
    },
}


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

    scale = scalar(mat, "TileCm", 24.0)
    offset_u = scalar(mat, "OffsetU", 0.0)
    offset_v = scalar(mat, "OffsetV", 0.0)
    tint = vector(mat, "Tint", (0.52, 0.32, 0.16))
    contrast = scalar(mat, "Contrast", 1.25)
    saturation = scalar(mat, "Saturation", 1.15)
    scan_mix = scalar(mat, "ScanMix", 0.12)
    brightness = scalar(mat, "Brightness", 1.0)
    ao_strength = scalar(mat, "AOStrength", 0.16)
    rough_bias = scalar(mat, "RoughBias", 0.04)
    normal_strength = scalar(mat, "NormalStrength", 0.58)
    specular = scalar(mat, "Specular", 0.32)

    weights = custom(
        mat,
        "float3 w=pow(abs(normalize(N)),4); return w/max(w.x+w.y+w.z,0.0001);",
        {"N": normal_local},
        3,
    )
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
        "TexBaseColor": (load(WOOD["BaseColor"]), u.MaterialSamplerType.SAMPLERTYPE_COLOR),
        "TexNormal": (load(WOOD["Normal"]), u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        "TexRHAOM": (load(WOOD["RHAOM"]), u.MaterialSamplerType.SAMPLERTYPE_MASKS),
    }
    samples = {}
    for parameter, (texture, sampler) in textures.items():
        planes = {}
        for axis in ("X", "Y", "Z"):
            sample = node(
                mat,
                u.MaterialExpressionTextureSampleParameter2D,
                parameter_name=parameter,
                texture=texture,
                sampler_type=sampler,
            )
            wire(uv[axis], sample, "UVs")
            planes[axis] = sample
        samples[parameter] = planes

    def blended(planes):
        return custom(mat, "return X*W.x+Y*W.y+Z*W.z;", dict(planes, W=weights), 3)

    color = custom(
        mat,
        "float3 scan=max(C,0.0);"
        "float luma=dot(scan,float3(0.299,0.587,0.114));"
        "float grain=saturate((luma-0.30)*max(Contrast,0.05)+0.50);"
        "float3 stained=T*max(Bright,0.0)*lerp(0.52,1.38,grain);"
        "float g=dot(stained,float3(0.299,0.587,0.114));"
        "stained=lerp(g.xxx,stained,Sat);"
        "float3 mixed=lerp(stained,scan*T*max(Bright,0.0),saturate(Mix));"
        "float m=0.975+0.025*sin(P.z*0.045+sin(P.x*0.08)+P.y*0.11);"
        "float ao=lerp(1.0,saturate(M.b),saturate(AO));"
        "return saturate(mixed*m*ao);",
        {
            "C": blended(samples["TexBaseColor"]),
            "T": tint,
            "P": position,
            "M": blended(samples["TexRHAOM"]),
            "AO": ao_strength,
            "Contrast": contrast,
            "Sat": saturation,
            "Mix": scan_mix,
            "Bright": brightness,
        },
        3,
    )
    rough = custom(
        mat,
        "return saturate(M.r+Bias);",
        {"M": blended(samples["TexRHAOM"]), "Bias": rough_bias},
        1,
    )
    local_n = custom(
        mat,
        "float3 n=normalize(N);"
        "float3 dx=float3(0,X.y,X.x)/max(X.z,0.2);"
        "float3 dy=float3(Y.y,0,Y.x)/max(Y.z,0.2);"
        "float3 dz=float3(Z.x,Z.y,0)/max(Z.z,0.2);"
        "float3 d=(dx*W.x+dy*W.y+dz*W.z)*Strength;"
        "return normalize(n+d-n*dot(d,n));",
        dict(samples["TexNormal"], N=normal_local, W=weights, Strength=normal_strength),
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
            samplers[str(expression.get_editor_property("parameter_name"))] = (
                expression.get_editor_property("sampler_type")
            )
    expected = {
        "TexBaseColor": u.MaterialSamplerType.SAMPLERTYPE_COLOR,
        "TexNormal": u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        "TexRHAOM": u.MaterialSamplerType.SAMPLERTYPE_MASKS,
    }
    for name, wanted in expected.items():
        if samplers.get(name) != wanted:
            raise RuntimeError("sampler %s is %s not %s" % (name, samplers.get(name), wanted))
    save_asset(mat)
    return mat, created or True, len(L.get_material_expressions(mat) or [])


def read_instance(instance):
    back = {
        "scalars": {},
        "vectors": {},
        "textures": {},
        "parent": instance.get_editor_property("parent").get_path_name()
        if instance.get_editor_property("parent")
        else None,
    }
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
    for item in instance.get_editor_property("texture_parameter_values") or []:
        value = item.get_editor_property("parameter_value")
        back["textures"][str(item.get_editor_property("parameter_info").get_editor_property("name"))] = (
            value.get_path_name() if value else None
        )
    return back


def make_instance(name, parent, spec):
    path = DEST + "/" + name
    instance = u.load_asset(path)
    if instance is None:
        instance = TOOLS.create_asset(
            name, DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew()
        )
    L.set_material_instance_parent(instance, parent)
    instance.set_editor_property("parent", parent)
    instance.modify()
    for key, value in spec["scalars"].items():
        L.set_material_instance_scalar_parameter_value(instance, key, float(value))
    tint = spec["tint"]
    L.set_material_instance_vector_parameter_value(
        instance, "Tint", u.LinearColor(tint[0], tint[1], tint[2], 1.0)
    )
    for parameter, tex_path in (
        ("TexBaseColor", spec["textures"]["BaseColor"]),
        ("TexNormal", spec["textures"]["Normal"]),
        ("TexRHAOM", spec["textures"]["RHAOM"]),
    ):
        L.set_material_instance_texture_parameter_value(instance, parameter, load(tex_path))
    L.update_material_instance(instance)
    save_asset(instance)
    back = read_instance(instance)
    for key, value in spec["scalars"].items():
        if abs(float(back["scalars"].get(key, -999)) - float(value)) > 1e-4:
            raise RuntimeError("instance %s scalar %s not written: %s" % (name, key, back["scalars"]))
    written = back["vectors"].get("Tint")
    if not written or any(abs(a - b) > 1e-3 for a, b in zip(written, tint)):
        raise RuntimeError("instance %s tint not written: %s" % (name, written))
    for parameter, tex_path in (
        ("TexBaseColor", spec["textures"]["BaseColor"]),
        ("TexNormal", spec["textures"]["Normal"]),
        ("TexRHAOM", spec["textures"]["RHAOM"]),
    ):
        got = back["textures"].get(parameter) or ""
        if load(tex_path).get_path_name() not in got and tex_path not in got:
            raise RuntimeError("instance %s texture %s not written: %s" % (name, parameter, got))
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
            WOOD["BaseColor"],
            WOOD["RHAOM"],
            WOOD["Normal"],
            ROTTEN["BaseColor"],
            ROTTEN["RHAOM"],
            ROTTEN["Normal"],
        ],
        "notes": [
            "V1 multiplied one walnut scan by similar browns and crushed AO, so slots did not read as different woods.",
            "V2 stains from scan luminance: Body walnut on RottenWood, Limb honey maple, Inlay rosewood, Arrow pale ash.",
            "LocalPosition triplanar kept so first-person aim does not swim the grain.",
            "M_BowWood_LocalScan and original Fab Phong remain on disk as rollback.",
        ],
    }
    master, rebuilt, expression_count = build_master()
    receipt["master"] = {
        "path": master.get_path_name(),
        "rebuilt": rebuilt,
        "expressions": expression_count,
        "tangent_space_normal": bool(master.get_editor_property("tangent_space_normal")),
    }
    instances = {}
    receipt["instances"] = {}
    for name, spec in VARIANTS.items():
        instance, back = make_instance(name, master, spec)
        instances[name] = instance
        receipt["instances"][name] = back
        receipt["instances"][name]["path"] = instance.get_path_name()
        receipt["instances"][name]["family"] = (
            "rotten" if spec["textures"] is ROTTEN else "wood"
        )

    arrow_wood_index = None
    for index, slot in enumerate(load(ARROW).static_materials):
        if "Wood" in str(slot.material_slot_name):
            arrow_wood_index = index
            break
    if arrow_wood_index is None:
        raise RuntimeError("arrow has no Wood slot")

    riser_map = {
        0: instances["MI_BowWood_Body"],
        1: instances["MI_BowWood_Limb"],
        2: instances["MI_BowWood_Inlay"],
    }
    receipt["binds"] = {
        "riser_detail": bind_mesh(RISER_DETAIL, riser_map),
        "riser": bind_mesh(RISER, riser_map),
        "arrow": bind_mesh(ARROW, {arrow_wood_index: instances["MI_BowWood_Arrow"]}),
    }
    (HERE / "structure_woods_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "BOW_STRUCTURE_WOODS_SAVED",
        json.dumps({"master": receipt["master"]["path"], "instances": list(instances)}),
        flush=True,
    )


if __name__ == "__main__":
    main()
