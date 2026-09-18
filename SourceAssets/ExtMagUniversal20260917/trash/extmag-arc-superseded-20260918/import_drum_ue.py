"""Import the three rebuilt drum meshes into /Game/Weapons/DrumRemodel20260917,
rename slots to each rifle's existing convention and bind the current
per-rifle finish materials. Never touches the old assets.
"""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
A = u.AssetToolsHelpers.get_asset_tools()
FBX = O / "FBX" / "drum"

BINDINGS = {
    "M4": {
        "file": "SM_M4_LargeDrum_new.fbx", "dest": "SM_M4_LargeDrum",
        "dir": "/Game/Weapons/DrumRemodel20260917/M4",
        "slots": {
            "DrumPolymer": "/Game/Weapons/M4Drum/M_M4DrumPolymer.M_M4DrumPolymer",
            "DrumFasteners": "/Game/Weapons/AttachmentFinish20260913/M4/Materials/M_M4_drum_1.M_M4_drum_1",
            "DrumIndex": "/Game/Weapons/M4Drum/M_M4DrumIndex.M_M4DrumIndex",
        },
    },
    "AKM": {
        "file": "SM_AKM_drum_new.fbx", "dest": "SM_AKM_drum",
        "dir": "/Game/Weapons/DrumRemodel20260917/AKM",
        "slots": {
            "drum_DrumPolymer": "/Game/Weapons/M4Drum/M_M4DrumPolymer.M_M4DrumPolymer",
            "drum_DrumFasteners": "/Game/Weapons/AttachmentFinish20260913/AKM/Materials/M_AKM_drum_1.M_AKM_drum_1",
            "drum_DrumIndex": "/Game/Weapons/M4Drum/M_M4DrumIndex.M_M4DrumIndex",
        },
    },
    "QBZ": {
        "file": "SM_QBZ191_drum_new.fbx", "dest": "SM_QBZ191_drum",
        "dir": "/Game/Weapons/DrumRemodel20260917/QBZ",
        "slots": {
            "QBZ_SRC_drum_0": "/Game/Weapons/QBZ191/MetalCoat20260913/Materials/M_QBZ191_Receiver_drum_0.M_QBZ191_Receiver_drum_0",
            "QBZ_SRC_drum_1": "/Game/Weapons/QBZ191/MetalCoat20260913/Materials/M_QBZ191_Receiver_drum_1.M_QBZ191_Receiver_drum_1",
            "QBZ_SRC_drum_2": "/Game/Weapons/M4Drum/M_M4DrumIndex.M_M4DrumIndex",
        },
    },
}

report = {}
u.log("DRUM_IMPORT_BEGIN")
for gun, cfg in BINDINGS.items():
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal = False
    opt.import_mesh = True
    opt.import_animations = False
    opt.import_materials = False
    opt.import_textures = False
    opt.create_physics_asset = False
    opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    opt.static_mesh_import_data.convert_scene_unit = False
    opt.static_mesh_import_data.import_uniform_scale = 1.0
    opt.static_mesh_import_data.combine_meshes = True

    task = u.AssetImportTask()
    task.filename = str(FBX / cfg["file"])
    task.destination_path = cfg["dir"]
    task.destination_name = cfg["dest"]
    task.options = opt
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])

    mesh = u.load_asset(cfg["dir"] + "/" + cfg["dest"])
    if not mesh:
        raise RuntimeError("drum import failed: " + gun)
    slots = mesh.get_editor_property('static_materials')
    # FBX brings slots in source order (Polymer, Fasteners, Index); rename to
    # the rifle's convention and bind the existing finish materials.
    order = ["DrumPolymer", "DrumFasteners", "DrumIndex"]
    slot_names = [str(s.material_slot_name) for s in slots]
    for i, s in enumerate(slots):
        key = order[i] if i < 3 else None
        if key is None:
            continue
        new_name = cfg["slots"] and [k for k, v in cfg["slots"].items() if k.endswith(key)]
        # AKM uses drum_DrumX names, QBZ uses QBZ_SRC_drum_N (order-based)
        if gun == "AKM":
            s.material_slot_name = "drum_" + key
        elif gun == "QBZ":
            s.material_slot_name = "QBZ_SRC_drum_" + str(i)
        else:
            s.material_slot_name = key
        mat = u.load_asset(cfg["slots"][str(s.material_slot_name)])
        if mat:
            s.material_interface = mat
        slots[i] = s
    mesh.set_editor_property('static_materials', slots)
    u.EditorAssetLibrary.save_loaded_asset(mesh, False)
    b = mesh.get_bounds()
    report[gun] = {"mesh": mesh.get_path_name(), "slots": [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')],
                   "extent": [round(b.box_extent.x, 2), round(b.box_extent.y, 2), round(b.box_extent.z, 2)]}
    u.log("DRUM_IMPORTED " + gun)

(O / "import_drum_receipt.json").write_text(json.dumps(report, indent=2))
u.log("DRUM_IMPORT_DONE " + json.dumps(report))
