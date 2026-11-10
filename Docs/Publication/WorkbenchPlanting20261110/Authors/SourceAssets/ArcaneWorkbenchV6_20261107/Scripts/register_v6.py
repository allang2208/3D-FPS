"""Run through the project MCP mutex in an existing editor, or a background Python commandlet when the editor is closed.
Targeted registration: requires the V6 mesh and all 28 materials already imported.
Does not import missing source, launch PIE, or save unrelated packages.
"""
import json, math
from pathlib import Path
import unreal as u
ROOT = Path(r"D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107")
MESH = "/Game/Building/ArcaneWorkbenchV6_20261107/Meshes/SM_ArcaneWorkbench_V6"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
mesh = u.load_asset(MESH)
if not mesh:
    raise RuntimeError("V6 mesh has not been imported: " + MESH)
if len(mesh.get_editor_property("static_materials")) != 28:
    raise RuntimeError("Complete the V6 28-slot material binding before registration")
if any(mesh.get_material(i) is None for i in range(28)):
    raise RuntimeError("V6 material binding is incomplete")
# Refuse registration until authored, axis-resolved sockets are present.
# A zero rotation is valid; a zero position is an unconfigured anchor.
socket_positions = {}
for socket_name in ("ArcaneItem", "ArcaneCamera"):
    socket = mesh.find_socket(socket_name)
    if socket is None:
        raise RuntimeError("Missing required V6 socket: " + socket_name)
    location = socket.get_editor_property("relative_location")
    rotation = socket.get_editor_property("relative_rotation")
    scale = socket.get_editor_property("relative_scale")
    xyz = [location.x, location.y, location.z]
    values = xyz + [rotation.pitch, rotation.yaw, rotation.roll, scale.x, scale.y, scale.z]
    if not all(math.isfinite(v) for v in values):
        raise RuntimeError("Non-finite V6 socket transform: " + socket_name)
    if sum(v * v for v in xyz) <= 0.000001:
        raise RuntimeError("Unconfigured zero-position V6 socket: " + socket_name)
    if any(abs(v) <= 0.000001 for v in (scale.x, scale.y, scale.z)):
        raise RuntimeError("Degenerate V6 socket scale: " + socket_name)
    socket_positions[socket_name] = xyz
if sum((a - b) ** 2 for a, b in zip(socket_positions["ArcaneItem"], socket_positions["ArcaneCamera"])) <= 0.000001:
    raise RuntimeError("V6 item and camera sockets must have distinct positions")

palette = u.load_asset(PALETTE)
if not palette:
    raise RuntimeError("Active build palette not found")
if palette.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    raise RuntimeError("Active build palette has unsaved edits; preserve them before registration")
bounds = mesh.get_bounds()
extent, origin = bounds.box_extent, bounds.origin
cells = [max(1, math.ceil(v * 2 / 20 - 0.0001)) for v in (extent.x, extent.y, extent.z)]
rows = list(palette.get_editor_property("components"))
entry = next((x for x in rows if str(x.get_editor_property("id")) == "arcane_workbench"), None)
if entry is None:
    entry = u.VoxelBuildPrefab()
    rows.append(entry)
entry.set_editor_property("id", "arcane_workbench")
entry.set_editor_property("display_name", u.Text("强化附魔台"))
entry.set_editor_property("mesh", mesh)
entry.set_editor_property("footprint", u.IntVector(*cells))
entry.set_editor_property("mount", u.VoxelPrefabMount.FREE)
# Keep imported multi-slot materials. Surface is intentionally not a global override.
entry.set_editor_property("surface", None)
entry.set_editor_property("pivot_offset_cm", u.Vector(0, 0, extent.z - cells[2] * 10.0))
palette.modify()
palette.set_editor_property("components", rows)
if not u.EditorAssetLibrary.save_loaded_asset(palette, False):
    raise RuntimeError("Palette save failed")
receipt = {"stage":"registered", "mesh":mesh.get_path_name(), "palette":palette.get_path_name(),
           "prefab_id":"arcane_workbench", "footprint_cells":cells,
           "mesh_bounds_origin_cm":[origin.x,origin.y,origin.z],
           "tests_run":False, "renders_run":False}
(ROOT/"Receipts").mkdir(exist_ok=True)
(ROOT/"Receipts"/"registration.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(receipt,ensure_ascii=False))
