"""Import the rebuilt A762 drum mesh over its existing asset path.

Only the static mesh is replaced; the material assignment of the shipping asset is
copied slot by slot, and the old package is backed up under Before/ first.
"""
import json
import shutil
import unreal as u
from pathlib import Path

O = Path(__file__).parent
P = O.parents[1]
ASSET = '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_drum'
FBX = O / 'Exports/SM_A762_drum.fbx'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

old = u.load_asset(ASSET)
if not old:
    raise RuntimeError('missing shipping drum ' + ASSET)
old_slots = [(str(s.material_slot_name), s.material_interface) for s in old.static_materials]
old_bbox = old.get_bounds().box_extent
old_tris = u.StaticMeshDescriptionHelper if False else None
print('shipping slots:', [n for n, _ in old_slots], flush=True)

disk = P / 'Content' / (ASSET.removeprefix('/Game/') + '.uasset')
backup = O / 'Before' / (ASSET.removeprefix('/Game/') + '.uasset')
if disk.exists() and not backup.exists():
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(disk, backup)

opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_materials = False
opt.import_textures = False
opt.import_animations = False
opt.set_editor_property('reset_to_fbx_on_material_conflict', True)
d = opt.static_mesh_import_data
d.combine_meshes = True
d.auto_generate_collision = False
d.generate_lightmap_u_vs = False
d.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
d.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
d.vertex_color_import_option = u.VertexColorImportOption.REPLACE

task = u.AssetImportTask()
task.filename = str(FBX)
task.destination_path = ASSET.rsplit('/', 1)[0]
task.destination_name = ASSET.rsplit('/', 1)[1]
task.options = opt
task.factory = u.FbxFactory()
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = True
A.import_asset_tasks([task])
mesh = u.load_asset(ASSET)
if not mesh or not task.imported_object_paths:
    raise RuntimeError('import failed for ' + ASSET)

slots = mesh.static_materials
by_name = {n: m for n, m in old_slots}
for i, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    mat = by_name.get(name) or (old_slots[i][1] if i < len(old_slots) else None)
    if mat is None:
        raise RuntimeError('no material for slot ' + name)
    slot.material_interface = mat
    slots[i] = slot
mesh.set_editor_property('static_materials', slots)
if not E.save_loaded_asset(mesh, False):
    raise RuntimeError('save failed for ' + ASSET)

def extent(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


receipt = {
    'asset': mesh.get_path_name(),
    'source': str(FBX),
    'slots_before': [n for n, _ in old_slots],
    'slots_after': [str(s.material_slot_name) for s in mesh.static_materials],
    'materials': [s.material_interface.get_path_name() if s.material_interface else None
                  for s in mesh.static_materials],
    'bbox_extent_before_cm': extent(old_bbox),
    'bbox_extent_after_cm': extent(mesh.get_bounds().box_extent),
    'saved': True, 'game_tested': False,
}
(O / 'install_receipt.json').write_text(json.dumps(receipt, indent=1), encoding='utf-8')
print('DRUM_IMPORTED', json.dumps(receipt), flush=True)
