"""Import the fitted torch mesh, keep the original Fab materials and baked head socket."""
import json
import os
from pathlib import Path

import unreal as u

root = Path(os.environ["FPS_PROJECT_ROOT"])
src = root / "SourceAssets/WoodenTorch20261122/StaffGripR6/Export"
family = "/Game/Weapons/WoodenTorch20261122"
dest = family + "/StaffGripR6"
name = "SM_HandheldStaffGrip"
lib = u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")
opt = u.FbxImportUI()
opt.import_mesh = True
opt.import_as_skeletal = opt.import_materials = opt.import_textures = opt.import_animations = False
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.static_mesh_import_data.combine_meshes = True
opt.static_mesh_import_data.auto_generate_collision = False
task = u.AssetImportTask()
task.filename = str(src/(name+".fbx"))
task.destination_path, task.destination_name = dest, name
task.automated, task.replace_existing, task.save, task.options = True, True, False, opt
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = lib.load_asset(dest+"/"+name)
slots=[]
for i, slot in enumerate(mesh.static_materials):
    part = str(slot.material_slot_name)
    material = lib.load_asset(family+"/FabHandheldR2/M_HandheldTorch_"+part)
    if not material: raise RuntimeError("Missing torch material "+part)
    mesh.set_material(i, material)
    slots.append(part)
fit = json.loads((src/"fit.json").read_text())
for socket_name,point in {"Grip":[0,0,0], "Flame":fit["flame_socket_ue_cm"]}.items():
    sock = mesh.find_socket(socket_name)
    if not sock:
        sock=u.new_object(u.StaticMeshSocket,outer=mesh)
        sock.set_editor_property("socket_name",socket_name)
        mesh.add_socket(sock)
    sock.set_editor_property("relative_location",u.Vector(*point))
height = mesh.get_bounds().box_extent.z * 2
if set(slots)!={"Wood","Rope","Cloth"} or abs(height-fit["length_cm"])>.1:
    raise RuntimeError("Imported mesh differs from authored torch")
if not lib.save_loaded_asset(mesh,False): raise RuntimeError("Could not save torch")
(Path(os.environ["TORCH_BATCH"])/"mesh-saved.json").write_text(json.dumps({
    "asset":mesh.get_path_name(), "height_cm":height, "materials":slots, "fit":fit},indent=2),encoding="utf8")
