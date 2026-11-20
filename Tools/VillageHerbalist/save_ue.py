"""Author the herbalist's PBR materials, skinned model and native standing loop."""
import json
import os
import subprocess
from pathlib import Path

import unreal as ue


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/VillageHerbalist/FullBody/UEAuthoringR1"
DONOR_TOOL = ROOT / "Tools/VillageTavernKeeper/Idle/retarget_idle.py"
DEST = "/Game/Characters/VillageHerbalist"
LIB = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
MEL = ue.MaterialEditingLibrary
saved = []


def store(asset):
    if not asset or not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + str(asset))
    saved.append(asset.get_path_name().split(".")[0])


def import_asset(path, dest, factory, options=None):
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
    asset = ue.load_asset(dest + "/" + path.stem)
    if not asset:
        raise RuntimeError("Import failed for " + str(path))
    return asset


def surface(entry):
    mat = TOOLS.create_asset(entry["name"], DEST + "/Materials", ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_property("two_sided", entry["two_sided"])
    if entry["alpha"] == "MASK":
        mat.set_editor_property("blend_mode", ue.BlendMode.BLEND_MASKED)
        mat.set_editor_property("opacity_mask_clip_value", entry["cutoff"])
    elif entry["alpha"] == "BLEND":
        mat.set_editor_property("blend_mode", ue.BlendMode.BLEND_TRANSLUCENT)
    MEL.set_material_usage(mat, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab = MEL.create_material_expression(mat, ue.MaterialExpressionSubstrateShadingModels, 0, 0)
    types = {"Color": (ue.TextureCompressionSettings.TC_DEFAULT, ue.MaterialSamplerType.SAMPLERTYPE_COLOR),
             "Normal": (ue.TextureCompressionSettings.TC_NORMALMAP, ue.MaterialSamplerType.SAMPLERTYPE_NORMAL),
             "ORM": (ue.TextureCompressionSettings.TC_MASKS, ue.MaterialSamplerType.SAMPLERTYPE_MASKS)}
    samples = {}
    for row, (role, filename) in enumerate(entry["files"].items()):
        tex = import_asset(OUT / filename, DEST + "/Textures", ue.TextureFactory())
        compression, sampler = types[role]
        tex.set_editor_property("compression_settings", compression)
        tex.set_editor_property("srgb", role == "Color")
        group = ue.TextureGroup.TEXTUREGROUP_CHARACTER
        if role == "Normal":
            group = ue.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP
            tex.set_editor_property("flip_green_channel", True)
        tex.set_editor_property("lod_group", group)
        store(tex)
        sample = MEL.create_material_expression(mat, ue.MaterialExpressionTextureSample, -800, 320 * row - 280)
        sample.texture = tex
        sample.sampler_type = sampler
        samples[role] = sample

    def connect(node, channel, dest, pin):
        if not MEL.connect_material_expressions(node, channel, dest, pin):
            raise RuntimeError(f"Cannot connect {entry['name']} {channel} -> {pin}")

    def value(role, channel, factor, row):
        node = samples.get(role)
        vector = isinstance(factor, list)
        if node and (all(v == 1. for v in factor) if vector else factor == 1.):
            return node, channel
        kind = ue.MaterialExpressionConstant3Vector if vector else ue.MaterialExpressionConstant
        constant = MEL.create_material_expression(mat, kind, -530, row * 170)
        if vector:
            constant.set_editor_property("constant", ue.LinearColor(*factor, 1.))
        else:
            constant.set_editor_property("r", factor)
        if not node:
            return constant, ""
        multiply = MEL.create_material_expression(mat, ue.MaterialExpressionMultiply, -270, row * 170)
        connect(node, channel, multiply, "A")
        connect(constant, "", multiply, "B")
        return multiply, ""

    connect(*value("Color", "RGB", entry["color"][:3], 0), slab, "BaseColor")
    connect(*value("ORM", "G", entry["rough"], 1), slab, "Roughness")
    connect(*value("ORM", "B", entry["metal"], 2), slab, "Metallic")
    if "Normal" in samples:
        connect(samples["Normal"], "RGB", slab, "Normal")
    if entry["has_occlusion"]:
        MEL.connect_material_property(samples["ORM"], "R", ue.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if entry["alpha"] != "OPAQUE":
        node, channel = value("Color", "A", entry["color"][3], 3)
        if entry["alpha"] == "MASK":
            MEL.connect_material_property(node, channel, ue.MaterialProperty.MP_OPACITY_MASK)
        else:
            connect(node, channel, slab, "Opacity")
    if not MEL.connect_material_property(slab, "", ue.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Could not bind surface " + entry["name"])
    MEL.recompile_material(mat)
    store(mat)
    return mat


def character(materials):
    ue.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    ui = ue.FbxImportUI()
    ui.automated_import_should_detect_type = False
    ui.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_as_skeletal = True
    ui.import_mesh = True
    ui.import_materials = False
    ui.import_textures = False
    ui.import_animations = False
    ui.create_physics_asset = False
    data = ui.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = False
    data.set_editor_property("bUseT0AsRefPose", False)
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh = import_asset(OUT / "SK_VillageHerbalist.fbx", DEST, ue.FbxFactory(), ui)
    slots = list(mesh.materials)
    for slot in slots:
        slot.material_interface = (materials[str(slot.material_slot_name)] if len(materials) > 1
                                   else next(iter(materials.values())))
    mesh.set_editor_property("materials", slots)
    store(mesh.skeleton)
    store(mesh)
    return mesh


def channels(transform):
    p, q, s = transform.translation, transform.rotation, transform.scale3d
    return [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]


def idle(mesh):
    skeleton = mesh.skeleton
    ref = skeleton.get_reference_pose()
    poses = ue.AnimPoseExtensions
    names = [str(n) for n in poses.get_bone_names(ref)]
    indices = {n: i for i, n in enumerate(names)}
    component = ue.new_object(ue.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    local = [channels(poses.get_bone_pose(ref, n, ue.AnimPoseSpaces.LOCAL)) for n in names]
    parents = [indices.get(str(component.get_parent_bone(n)), -1) for n in names]
    reference = OUT / "idle_reference.json"
    motion_path = OUT / "idle_motion.json"
    reference.write_text(json.dumps(dict(names=names, parents=parents, reference=local)), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    subprocess.run([env["HERBALIST_PYTHON"], "-I", str(DONOR_TOOL), str(reference), str(motion_path)],
                   env=env, check=True)
    motion = json.loads(motion_path.read_text(encoding="utf-8"))
    factory = ue.AnimSequenceFactory()
    factory.set_editor_property("target_skeleton", skeleton)
    factory.set_editor_property("preview_skeletal_mesh", mesh)
    sequence = TOOLS.create_asset("A_VillageHerbalist_Idle", DEST, ue.AnimSequence, factory)
    controller = sequence.get_editor_property("controller")
    controller.open_bracket("Adapt relaxed standing loop to herbalist", False)
    try:
        controller.set_frame_rate(ue.FrameRate(motion["rate"], 1), False)
        controller.set_number_of_frames(ue.FrameNumber(motion["frame_count"]), False)
        for i, name in enumerate(names):
            keys = motion["tracks"].get(name, [local[i]])
            controller.add_bone_curve(name, False)
            if not controller.set_bone_track_keys(name, [ue.Vector(*k[:3]) for k in keys],
                    [ue.Quat(*k[3:7]) for k in keys], [ue.Vector(*k[7:]) for k in keys], False):
                raise RuntimeError("Could not write idle track " + name)
    finally:
        controller.close_bracket(False)
    sequence.set_editor_property("enable_root_motion", False)
    sequence.set_editor_property("force_root_lock", True)
    sequence.set_editor_property("root_motion_root_lock", ue.RootMotionRootLock.REF_POSE)
    sequence.set_editor_property("loop", True)
    store(sequence)


manifest = json.loads((OUT / "surfaces.json").read_text(encoding="utf-8"))
mesh = character({entry["name"]: surface(entry) for entry in manifest})
idle(mesh)
(Path(os.environ["HERBALIST_HOST"]) / "saved.json").write_text(json.dumps(saved, indent=2), encoding="utf-8")
