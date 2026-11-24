"""Build the instanced laser/afterglow material in the Aurora art host."""
import unreal as u

package = "/Game/Weapons/FrontierCompoundBow/AuroraLaserR4"
name = "M_AuroraLaser"
lib = u.MaterialEditingLibrary
if u.Paths.get_base_filename(u.Paths.get_project_file_path()) != "AuroraLaser":
    raise RuntimeError("Run the material recipe in the isolated AuroraLaser art host")
material = u.EditorAssetLibrary.load_asset(package + "/" + name) if u.EditorAssetLibrary.does_asset_exist(package + "/" + name) else None
if material:
    lib.delete_all_material_expressions(material)
else:
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, package, u.Material, u.MaterialFactoryNew())
material.set_editor_property("blend_mode", u.BlendMode.BLEND_ADDITIVE)
material.set_editor_property("shading_model", u.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property("used_with_instanced_static_meshes", True)

def node(kind, **params):
    expr = lib.create_material_expression(material, kind)
    for key, value in params.items():
        expr.set_editor_property(key, value)
    return expr

def wire(src, dst, pin):
    if not lib.connect_material_expressions(src, "", dst, pin):
        raise RuntimeError(f"Cannot connect {pin}")

def custom_value(index):
    source = node(u.MaterialExpressionPerInstanceCustomData, data_index=index, const_default_value=1.)
    interp = node(u.MaterialExpressionVertexInterpolator)
    wire(source, interp, str(lib.get_material_expression_input_names(interp)[0]))
    return interp

local = node(u.MaterialExpressionVertexInterpolator)
wire(node(u.MaterialExpressionPreSkinnedPosition), local, str(lib.get_material_expression_input_names(local)[0]))
inputs = {"TailStrength": custom_value(0), "TailHeat": custom_value(1),
          "TipStrength": custom_value(2), "TipHeat": custom_value(3), "MeshPosition": local,
          "NormalDir": node(u.MaterialExpressionPixelNormalWS), "EyeDir": node(u.MaterialExpressionCameraVectorWS),
          "Exposure": node(u.MaterialExpressionEyeAdaptation)}
code = """
float along = saturate(MeshPosition.z * .01 + .5);
float Strength = lerp(TailStrength,TipStrength,along);
float Heat = lerp(TailHeat,TipHeat,along);
float facing = saturate(abs(dot(normalize(NormalDir),normalize(EyeDir))));
float edge = smoothstep(0.,.82,facing);
// Internal end caps of consecutive cylinders must not appear as a row of discs.
// The pulse front and particles have their own spherical instances.
float cap = smoothstep(49.97,49.995,abs(MeshPosition.z));
edge *= 1.0-cap;
float core = pow(facing,12.) * saturate(Heat);
float3 blue = lerp(float3(.012,.085,.92),float3(.09,.54,1.),saturate(Heat));
float3 light = lerp(blue,float3(.55,.91,1.),core);
return float4(light*(1.8+3.8*core)/max(.01,Exposure),edge*saturate(Strength));
"""
shader = node(u.MaterialExpressionCustom, description="Aurora pulse and cooling ion trail", code=code,
              output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pins = []
for key in inputs:
    pin = u.CustomInput()
    pin.set_editor_property("input_name", key)
    pins.append(pin)
shader.set_editor_property("inputs", pins)
for key, expr in inputs.items():
    wire(expr, shader, key)
for channels, prop in [({"r":True,"g":True,"b":True,"a":False},u.MaterialProperty.MP_EMISSIVE_COLOR),
                       ({"r":False,"g":False,"b":False,"a":True},u.MaterialProperty.MP_OPACITY)]:
    mask = node(u.MaterialExpressionComponentMask, **channels)
    wire(shader, mask, "")
    if not lib.connect_material_property(mask, "", prop):
        raise RuntimeError("Cannot connect laser material output")
errors = lib.recompile_material(material)
if errors:
    raise RuntimeError(str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError("Could not save the laser material")
u.log("AURORA_LASER_MATERIAL_SAVED " + material.get_path_name())
