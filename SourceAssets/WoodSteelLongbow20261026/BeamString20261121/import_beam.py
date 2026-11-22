"""Author the Substrate light filament and import the beam on the original bow rig."""
import json
from pathlib import Path

import unreal as u

ART = Path(__file__).resolve().parent
DEST = "/Game/Weapons/WoodSteelLongbow20261026/BeamString20261121"
OLD = "/Game/Weapons/WoodSteelLongbow20261026/MountainEchoV13"
NAME = "SK_Highland_BeamString"
LIGHT = "M_Highland_BeamString_Light"
edit = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
catalog = u.EditorAssetLibrary

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError("Could not save " + asset.get_path_name())

def wire(src, dst, pin):
    if not edit.connect_material_expressions(src, "", dst, pin):
        raise RuntimeError("Couldn't connect " + dst.get_name() + "." + pin)

mat = u.load_asset(DEST + "/" + LIGHT) if catalog.does_asset_exist(DEST + "/" + LIGHT) else None
if mat is None:
    mat = assets.create_asset(LIGHT, DEST, u.Material, u.MaterialFactoryNew())
else:
    edit.delete_all_material_expressions(mat)

def node(cls, x, y, **properties):
    expression = edit.create_material_expression(mat, cls, x, y)
    for name, value in properties.items():
        expression.set_editor_property(name, value)
    return expression

def color(x, y, r, g, b):
    return node(u.MaterialExpressionConstant3Vector, x, y, constant=u.LinearColor(r, g, b, 1))

ivory = color(-1050, -320, 3.20, 2.54, 1.41)
gold = color(-1050, -170, 1.65, .70, .20)
facing = node(u.MaterialExpressionFresnel, -1050, -20, exponent=1.45, base_reflect_fraction=0.)
gradient = node(u.MaterialExpressionLinearInterpolate, -780, -260)
wire(ivory, gradient, "A")
wire(gold, gradient, "B")
wire(facing, gradient, "Alpha")
stacks = node(u.MaterialExpressionScalarParameter, -1050, 180,
              parameter_name="StringCharges", default_value=0., use_custom_primitive_data=True, primitive_data_index=0)
step = node(u.MaterialExpressionMultiply, -800, 160, const_b=.18)
wire(stacks, step, "A")
intensity = node(u.MaterialExpressionAdd, -580, 120, const_b=1.)
wire(step, intensity, "A")
emission = node(u.MaterialExpressionMultiply, -350, -170)
wire(gradient, emission, "A")
wire(intensity, emission, "B")
surface = node(u.MaterialExpressionSubstrateUnlitBSDF, -100, -100)
wire(emission, surface, "EmissiveColor")
if not edit.connect_material_property(surface, "", u.MaterialProperty.MP_FRONT_MATERIAL):
    raise RuntimeError("Missing Substrate surface connection")
edit.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
edit.recompile_material(mat)
save(mat)

rig = u.load_asset(OLD + "/SK_Highland_MountainEchoString_Skeleton")
if rig is None:
    raise RuntimeError("Original mountain echo rig is missing")
u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_mesh = True
options.import_as_skeletal = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.skeleton = rig
data = options.skeletal_mesh_import_data
data.set_editor_property("update_skeleton_reference_pose", False)
data.set_editor_property("use_t0_as_ref_pose", False)
data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS

task = u.AssetImportTask()
task.filename = str(ART / (NAME + ".fbx"))
task.destination_path = DEST
task.destination_name = NAME
task.options = options
task.automated = True
task.replace_existing = True
task.save = False
assets.import_asset_tasks([task])
mesh = u.load_asset(DEST + "/" + NAME)
if mesh is None or mesh.skeleton != rig:
    raise RuntimeError("New mesh did not import on the original three-anchor bow skeleton")
slots = list(mesh.get_editor_property("materials"))
materials = {}
for slot in slots:
    name = str(slot.material_slot_name)
    material = mat if name == LIGHT else u.load_asset(OLD + "/" + name)
    if not material:
        raise RuntimeError("String material is unavailable " + name)
    slot.set_editor_property("material_interface", material)
    materials[name] = material.get_path_name()
mesh.set_editor_property("materials", slots)
lods = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not lods.regenerate_lod(mesh, 3, False, False):
    raise RuntimeError("Could not retain near and distance mesh levels")
save(mesh)
(ART / "authoring-result.json").write_text(json.dumps({
    "mesh": mesh.get_path_name(), "skeleton": rig.get_path_name(), "materials": materials,
    "source": str(ART / (NAME + ".fbx")), "gameplay_tested": False,
}, indent=2), encoding="utf-8")
print("HIGHLAND_BEAM_STRING_SAVED", flush=True)
