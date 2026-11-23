"""Build the wind-responsive handheld flame from the saved R9 assets."""
import json
import os
import sys
from pathlib import Path

import unreal as u

project = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source = project / "SourceAssets/WoodenTorch20261122/WindResponseR10"
family = "/Game/Weapons/WoodenTorch20261122/"
lib = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
sys.path.insert(0, str(project / "Tools/Skills"))
from build_fireball_assets import API, assignments, put, ref, setdata
from build_fireball_flight import user_parameter


def fork(name):
    path = family + "WindResponseR10/" + name
    asset = lib.load_asset(path) if lib.does_asset_exist(path) else lib.duplicate_asset(family + "StaffCombatR9/" + name, path)
    if not asset:
        raise RuntimeError(path)
    return asset


def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError(asset.get_path_name())


def connect(src, dst, pin):
    if not edit.connect_material_expressions(src, "", dst, pin):
        raise RuntimeError(f"Cannot connect {src.get_name()} to {dst.get_name()}.{pin}")


def input_pin(name):
    pin = u.CustomInput()
    pin.set_editor_property("input_name", name)
    return pin


material = fork("M_HearthFlameVolume")
nodes = edit.get_material_expressions(material)
density, = [n for n in nodes if isinstance(n, u.MaterialExpressionCustom) and "FlowTex" in n.get_editor_property("code")]
local, = [n for n in nodes if isinstance(n, u.MaterialExpressionLocalPosition)]
local.set_editor_property("included_offsets", u.PositionIncludedOffsets.EXCLUDE_OFFSETS)


def node(cls, label):
    existing = next((n for n in nodes if n.get_editor_property("desc") == label), None)
    obj = existing or edit.create_material_expression(material, cls)
    obj.set_editor_property("desc", label)
    return obj


slope = node(u.MaterialExpressionVectorParameter, "Torch plume slope")
slope.set_editor_properties(dict(parameter_name="PlumeSlope", default_value=u.LinearColor(0,0,0,0),
                                 use_custom_primitive_data=True, primitive_data_index=1))
pins = list(density.get_editor_property("inputs"))
for i, pin in enumerate(pins):
    if str(pin.get_editor_property("input_name")) == "UpLocal":
        pins[i] = input_pin("PlumeSlope")
density.set_editor_property("inputs", pins)
density.set_editor_property("code", (source / "HearthFlame.hlsl").read_text(encoding="utf8"))
connect(slope, density, "PlumeSlope")
shear = node(u.MaterialExpressionCustom, "Wind shear about fuel band")
shear.set_editor_properties(dict(inputs=[input_pin("P"), input_pin("Slope")],
    output_type=u.CustomMaterialOutputType.CMOT_FLOAT3, code="return float3(Slope.xy*(P.z-8.),0.);"))
connect(local, shear, "P")
connect(slope, shear, "Slope")
offset = node(u.MaterialExpressionTransform, "Torch shear in world space")
offset.set_editor_properties(dict(transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                                  transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD))
connect(shear, offset, "")
if not edit.connect_material_property(offset, "", u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
    raise RuntimeError("Cannot connect proxy shear")
errors = edit.recompile_material(material)
if errors:
    raise RuntimeError("Torch volume material compile failed: " + str(errors))
save(material)

volume = fork("SM_HearthFlameVolume")
volume.set_material(0, material)
# Only the culling bounds grow. The drawing proxy follows the optical volume.
for prop in ("positive_bounds_extension", "negative_bounds_extension"):
    volume.set_editor_property(prop, u.Vector(33, 33, 0))
save(volume)

system = fork("NS_HearthWrap")
vec3 = "/Script/CoreUObject.Vector3f"
scalar = "/Script/Niagara.NiagaraFloat"
pos = "/Script/Niagara.NiagaraPosition"
if "User.PlumeSlope" not in API.call_method("GetUserVariables",(system,)).export_text():
    user_parameter(system, "PlumeSlope", vec3)
seed = "frac(float(Particles.UniqueID)*.61803399)"
angle = f"(6.2831853*{seed})"
radial = f"float3(cos({angle}),sin({angle}),0.)"
axis = "float3(User.PlumeSlope.xy,1.)"
spawn = "ParticleSpawnScript"
update = "ParticleUpdateScript"
assignments(system, "Fire", spawn, {
    "Particles.Position": (pos, f"float3(0.,0.,11.5)+User.PlumeSlope*3.5+{radial}*1.8"),
    "Particles.Velocity": (vec3, f"{axis}*8.+{radial}*4.6")})
# Append a final update assignment so an already burning sprite follows a reversal.
# This module is separate from the inherited spawn and atlas animation assignments.
tag = "WoodenTorch.WindResponseR10.FireUpdate"
module = lib.get_metadata_tag(system, tag)
if not module:
    entries = []
    for name, typ in (("Particles.Position",pos), ("Particles.SpriteAlignment",vec3), ("Particles.SpriteRotation",scalar)):
        entry = u.NiagaraExt_SetParameterEntry()
        entry.import_text(f'(Variable=(Name="{name}",Type=(ClassStructOrEnum="{typ}",UnderlyingType=2)))')
        entries.append(entry)
    module = str(API.call_method("AddSetParametersModule",(ref(system,"Fire",update),entries)).get_editor_property("module_name"))
    lib.set_metadata_tag(system, tag, module)
age = "Particles.Age"
for name, expr in {
    "Particles.Position": f"float3(0.,0.,11.5+8.*{age})+User.PlumeSlope*(3.5+8.*{age})+{radial}*(1.8+4.6*{age})",
    "Particles.SpriteAlignment": f"normalize({axis})", "Particles.SpriteRotation":"0."}.items():
    put(system, "Fire", update, module, name, f'(HlslExpression="{expr}")',
        "/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression")
setdata("SetRendererData", u.NiagaraExt_RendererData, ref(system, "Fire", renderer=0), {"Alignment":"CustomAlignment"})

assignments(system, "Smoke", spawn, {
    "Particles.Position": (pos, "float3(0.,0.,21.5)+User.PlumeSlope*13.5"),
    "Particles.Velocity": (vec3, f"{axis}*10.")})
assignments(system, "Sparks", spawn, {
    "Particles.Position": (pos, f"float3(0.,0.,12.)+{radial}*2.+User.PlumeSlope*4."),
    "Particles.Velocity": (vec3, f"{axis}*lerp(11.,19.,{seed})+{radial}")})
box = {"min":{"x":-46,"y":-46,"z":-16}, "max":{"x":46,"y":46,"z":53}, "isValid":True}
for emitter in ("Fire", "Smoke", "Sparks"):
    setdata("SetEmitterData", u.NiagaraExt_EmitterData, ref(system,emitter), {"FixedBounds":box})
system.set_editor_property("fixed_bounds", u.Box(min=u.Vector(-46,-46,-16), max=u.Vector(46,46,53)))
if not u.RainAssetEditor.compile_rain(system, True):
    raise RuntimeError("Torch Niagara compile failed")
save(system)
Path(os.environ["TORCH_BATCH"], "assets.json").write_text(json.dumps({
    "saved":[a.get_path_name() for a in (material, volume, system)],
    "slot":volume.get_material(0).get_path_name(), "material_compiled":True, "niagara_compiled":True},
    indent=2), encoding="utf8")
