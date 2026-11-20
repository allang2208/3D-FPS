"""Build the new full-body skeletal mesh against the herbalist's production skeleton."""
import json
import math
import os
from pathlib import Path

import unreal as ue


HOST = Path(os.environ["LINZHI_R3_HOST"]).resolve()
if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() != HOST:
    raise RuntimeError("Head authoring requires the isolated host")
SOURCE = HOST / "SourceAssets/VillageHerbalist/FullBody/HeadR3"
BODY = "/Game/Characters/VillageHerbalist"
DEST = BODY + "/HeadR3"
NAME = "SK_VillageHerbalist_HeadR3"
MEL = ue.MaterialEditingLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
LIB = ue.EditorAssetLibrary
saved = []


def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())
    saved.append(asset.get_path_name().split(".")[0])


def import_one(path, dest, factory, options=None):
    task = ue.AssetImportTask()
    task.filename = str(path)
    task.destination_path = dest
    task.destination_name = path.stem
    task.factory = factory
    task.automated = True
    task.save = False
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    results = task.get_objects()
    asset = ue.load_asset(dest + "/" + path.stem)
    if not asset or asset not in results:
        raise RuntimeError("Could not import " + str(path))
    return asset


def wire(source, channel, target, pin):
    if not MEL.connect_material_expressions(source, channel, target, pin):
        raise RuntimeError(f"Could not connect {source.get_name()}.{channel} to {pin}")


def surface(name, spec):
    mat = TOOLS.create_asset(name, DEST + "/Materials", ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_property("two_sided", spec.get("two_sided", False))
    mode = spec.get("alpha", "OPAQUE")
    if mode == "MASK":
        mat.set_editor_property("blend_mode", ue.BlendMode.BLEND_MASKED)
        mat.set_editor_property("opacity_mask_clip_value", spec["cutoff"])
    elif mode == "BLEND":
        mat.set_editor_property("blend_mode", ue.BlendMode.BLEND_TRANSLUCENT)
    MEL.set_material_usage(mat, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab = MEL.create_material_expression(mat, ue.MaterialExpressionSubstrateShadingModels, 0, 0)
    types = {"Color": (ue.TextureCompressionSettings.TC_DEFAULT, ue.MaterialSamplerType.SAMPLERTYPE_COLOR),
             "Normal": (ue.TextureCompressionSettings.TC_NORMALMAP, ue.MaterialSamplerType.SAMPLERTYPE_NORMAL),
             "ORM": (ue.TextureCompressionSettings.TC_MASKS, ue.MaterialSamplerType.SAMPLERTYPE_MASKS)}
    textures = {}
    for row, (role, file) in enumerate(spec.get("files", {}).items()):
        tex = import_one(SOURCE / "UE/Textures" / file, DEST + "/Textures", ue.TextureFactory())
        compression, sampler = types[role]
        tex.set_editor_property("compression_settings", compression)
        tex.set_editor_property("srgb", role == "Color")
        tex.set_editor_property("lod_group", ue.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if role == "Normal"
                               else ue.TextureGroup.TEXTUREGROUP_CHARACTER)
        if role == "Normal":
            tex.set_editor_property("flip_green_channel", True)
        save(tex)
        sample = MEL.create_material_expression(mat, ue.MaterialExpressionTextureSample, -800, 360 * row)
        sample.texture = tex
        sample.sampler_type = sampler
        textures[role] = sample

    def scaled(role, channel, factor, row):
        sample = textures.get(role)
        vector = isinstance(factor, list)
        if sample and (all(k == 1. for k in factor) if vector else factor == 1.):
            return sample, channel
        kind = ue.MaterialExpressionConstant3Vector if vector else ue.MaterialExpressionConstant
        const = MEL.create_material_expression(mat, kind, -510, row * 170)
        if vector:
            const.set_editor_property("constant", ue.LinearColor(*factor, 1.))
        else:
            const.set_editor_property("r", factor)
        if not sample:
            return const, ""
        multiply = MEL.create_material_expression(mat, ue.MaterialExpressionMultiply, -280, row * 170)
        wire(sample, channel, multiply, "A")
        wire(const, "", multiply, "B")
        return multiply, ""

    wire(*scaled("Color", "RGB", spec["color"][:3], 0), slab, "BaseColor")
    wire(*scaled("ORM", "G", spec["rough"], 1), slab, "Roughness")
    wire(*scaled("ORM", "B", spec["metal"], 2), slab, "Metallic")
    if "Normal" in textures:
        wire(textures["Normal"], "RGB", slab, "Normal")
    if spec.get("ao"):
        MEL.connect_material_property(textures["ORM"], "R", ue.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if mode == "MASK":
        source, channel = scaled("Color", "A", spec["color"][3], 3)
        MEL.connect_material_property(source, channel, ue.MaterialProperty.MP_OPACITY_MASK)
    elif mode == "BLEND":
        wire(*scaled("Color", "A", spec["color"][3], 3), slab, "Opacity")
    if not MEL.connect_material_property(slab, "", ue.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Could not bind " + name)
    MEL.recompile_material(mat)
    save(mat)
    return mat


def rig(mesh):
    component = ue.new_object(ue.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    bones = [component.get_bone_name(i) for i in range(component.get_num_bones())]
    return ([(str(bone), str(component.get_parent_bone(bone))) for bone in bones],
            [component.get_ref_pose_transform(i) for i in range(len(bones))])


def pose_error(old, new):
    distances, angles, scales = [], [], []
    for a, b in zip(old, new):
        distances.append(math.dist(a.translation.to_tuple(), b.translation.to_tuple()))
        q = [a.rotation.x, a.rotation.y, a.rotation.z, a.rotation.w]
        r = [b.rotation.x, b.rotation.y, b.rotation.z, b.rotation.w]
        cosine = abs(sum(x * y for x, y in zip(q, r))) / math.hypot(*q) / math.hypot(*r)
        angles.append(math.degrees(2. * math.acos(min(1., cosine))))
        scales.append(max(abs(x-y) for x, y in zip(a.scale3d.to_tuple(), b.scale3d.to_tuple())))
    return dict(max_local_translation_cm=max(distances), max_local_rotation_degrees=max(angles),
                max_scale_component=max(scales))


body_mesh = ue.load_asset(BODY + "/SK_VillageHerbalist")
expected_tree, original_pose = rig(body_mesh)
original_skeleton = body_mesh.skeleton
animations = [ue.load_asset(BODY + "/A_VillageHerbalist_" + motion) for motion in ("Idle", "Walk")]
if len(expected_tree) != 66 or any(not a or a.get_editor_property("skeleton") != original_skeleton for a in animations):
    raise RuntimeError("The installed herbalist mesh and animations do not share the expected skeleton")
ue.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
options = ue.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = options.import_mesh = True
options.import_materials = options.import_textures = options.import_animations = False
options.create_physics_asset = False
options.skeleton = original_skeleton
data = options.skeletal_mesh_import_data
data.convert_scene = True
data.convert_scene_unit = True
data.force_front_x_axis = False
data.set_editor_property("bUseT0AsRefPose", False)
data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh = import_one(SOURCE / "Assembly" / (NAME + ".fbx"), DEST, ue.FbxFactory(), options)
tree, pose = rig(mesh)
if mesh.skeleton != original_skeleton or tree != expected_tree:
    raise RuntimeError("The FBX does not preserve the herbalist's original 66-bone hierarchy")
deviation = pose_error(original_pose, pose)
if (deviation["max_local_translation_cm"] > .02 or deviation["max_local_rotation_degrees"] > .2 or
        deviation["max_scale_component"] > .001):
    raise RuntimeError(f"The assembled FBX has a different bind pose: {deviation}")
specs = json.loads((SOURCE / "UE/surfaces.json").read_text(encoding="utf-8"))
specs["M_LinZhiLenses"] = dict(color=[.89, .93, .96, .045], rough=.12, metal=0., alpha="BLEND",
                              two_sided=True)
materials = {"M_VillageHerbalist": body_mesh.materials[0].material_interface}
slots = list(mesh.materials)
names = [str(slot.material_slot_name) for slot in slots]
if not {"M_VillageHerbalist", "M_LinZhiHead", "M_LinZhiFrames"}.issubset(names):
    raise RuntimeError(f"Missing requested skin, face or glasses surface: {names}")
for slot, slot_name in zip(slots, names):
    if slot_name not in materials:
        materials[slot_name] = surface(slot_name, specs[slot_name])
    slot.material_interface = materials[slot_name]
mesh.set_editor_property("materials", slots)
mesh.set_editor_property("physics_asset", body_mesh.physics_asset)
save(mesh)
sections = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)
report = dict(engine=ue.SystemLibrary.get_engine_version(), mesh=mesh.get_path_name(),
              skeleton=original_skeleton.get_path_name(), bone_count=len(expected_tree), bind_pose_error=deviation,
              animations=[a.get_path_name() for a in animations], saved_packages=saved,
              lods=[dict(vertices=sections.get_num_verts(mesh, i),
                         sections=[sections.get_lod_material_slot(mesh, i, j)
                                   for j in range(sections.get_num_sections(mesh, i))])
                    for i in range(sections.get_lod_count(mesh))],
              materials={n: material.get_path_name() for n, material in materials.items()})
(HOST / "authored.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
