"""Import the brown hunt-glove pickup. Leaves SM_FieldGloves_Pickup for black."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path("D:/FPS3D/FPSGAME")
FBX = PROJECT / "SourceAssets/ModularOutfit20260924/Exports/SM_HuntFieldGloves_Pickup.fbx"
DEST = "/Game/Characters/ModularOutfit20260924/Pickups"
NAME = "SM_HuntFieldGloves_Pickup"
ITEMS = PROJECT / "Content/ColdSteelData/items.json"
MATERIAL = "/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
SAVE = u.EditorLoadingAndSavingUtils

if not FBX.is_file():
    raise RuntimeError("Missing hunt pickup FBX")
path = DEST + "/" + NAME
mesh = u.load_asset(path)
if not mesh:
    E.make_directory(DEST)
    task = u.AssetImportTask()
    task.filename = str(FBX)
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = False
    options = u.FbxImportUI()
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("mesh_type_to_import", u.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.get_editor_property("static_mesh_import_data").set_editor_property("combine_meshes", True)
    task.options = options
    A.import_asset_tasks([task])
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError("Hunt pickup import failed")
mat = u.load_asset(MATERIAL)
if mat:
    mesh.set_material(0, mat)
if not (SAVE.save_packages([mesh.get_outer()], False) or E.save_loaded_asset(mesh, False)):
    raise RuntimeError("Cannot save hunt pickup")
catalog = json.loads(ITEMS.read_text(encoding="utf-8-sig"))
catalog["ue_field_gloves"]["world_mesh"] = mesh.get_path_name()
ITEMS.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("HUNT_PICKUP_SAVED", mesh.get_path_name(), flush=True)
