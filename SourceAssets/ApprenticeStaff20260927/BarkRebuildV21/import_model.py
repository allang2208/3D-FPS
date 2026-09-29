"""Import the authored branch and install at existing runtime mesh paths.

Use the already running editor bridge, or a commandlet with the editor closed.
No gameplay, preview, test, or editor launch. Preserve the previous meshes.
"""
import json
import re
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE + '/BarkRebuildV21'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
entries = json.loads((ROOT / 'Export/meshes.json').read_text(encoding='utf-8'))
# Once V33 is installed, subsequent full staff imports must retain its four
# authored crystal heads rather than restore the old flat-colour V21 pieces.
craft_root = ROOT.parent / 'CrystalCraftV33'
craft_receipt = craft_root / 'install-receipt.json'
if craft_receipt.exists() and json.loads(craft_receipt.read_text(encoding='utf-8')).get('complete'):
    crafted = {e['name']: e for e in json.loads((craft_root / 'Export/meshes.json').read_text(encoding='utf-8'))}
    entries = [crafted.get(e['name'], e) for e in entries]
receipt_path = ROOT / 'import-receipt.json'
receipt = {
    'revision': 21, 'complete': False, 'tested': False, 'preview_rendered': False,
    'saved_assets': [], 'installed': [], 'backups': [],
    'reference': '../BranchCrystalV18/Design/staff_three_views.png',
    'wood': 'Continuous closed Blender bark shell with real geometric relief',
    'quartz': 'QuartzDenseV22',
}
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before replacing the staff meshes.')

targets = {folder + '/' + e['name'] for folder in (BASE + '/Meshes', DEST + '/Meshes', DEST + '/PreviousMeshes') for e in entries}
conflicts = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if conflicts:
    raise RuntimeError('Unsaved target staff meshes: ' + ', '.join(conflicts))


def record():
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


static_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)


def full_precision(mesh):
    settings = static_editor.get_lod_build_settings(mesh, 0)
    if not settings.use_full_precision_u_vs:
        settings.use_full_precision_u_vs = True
        static_editor.set_lod_build_settings(mesh, 0, settings)


materials = {}
for name in ('M_Staff_BranchWoodV19', 'M_Staff_PineV19', 'M_Staff_SandalV19', 'M_Staff_HempV19'):
    materials[name] = u.load_asset(BASE + '/SolidRepairV19/Materials/' + name)
materials['M_Staff_QuartzDenseV22'] = u.load_asset(BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22')
materials['M_Staff_QuartzMilkV20'] = materials['M_Staff_QuartzDenseV22']
for name in ('M_Staff_ice', 'M_Staff_fire', 'M_Staff_light', 'M_Staff_electric', 'M_Staff_metal', 'M_Staff_RuneV2'):
    materials[name] = u.load_asset(BASE + '/Materials/' + name)
for entry in entries:
    for name in entry['materials']:
        if name.startswith('M_StaffCraft_'):
            materials[name] = u.load_asset(BASE + '/CrystalCraftV33/Materials/' + name)
for name, material in materials.items():
    if not material:
        raise RuntimeError('Missing existing staff material ' + name)

flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    options = u.FbxImportUI()
    for key, value in {
        'import_mesh': True, 'import_as_skeletal': False,
        'mesh_type_to_import': u.FBXImportType.FBXIT_STATIC_MESH,
        'automated_import_should_detect_type': False, 'import_materials': False,
        'import_textures': False,
    }.items():
        options.set_editor_property(key, value)
    data = options.get_editor_property('static_mesh_import_data')
    for key, value in {
        'combine_meshes': True, 'auto_generate_collision': False,
        'import_uniform_scale': 1, 'convert_scene': True, 'convert_scene_unit': False,
        'normal_import_method': u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
    }.items():
        data.set_editor_property(key, value)

    for entry in entries:
        task = u.AssetImportTask()
        for key, value in {
            'filename': entry['fbx'], 'destination_path': DEST + '/Meshes',
            'destination_name': entry['name'], 'automated': True,
            'replace_existing': True, 'save': False, 'options': options,
        }.items():
            task.set_editor_property(key, value)
        A.import_asset_tasks([task])
        mesh = u.load_asset(DEST + '/Meshes/' + entry['name'])
        if not mesh:
            raise RuntimeError('Import failed: ' + entry['name'])
        for i, slot in enumerate(mesh.get_editor_property('static_materials')):
            name = str(slot.get_editor_property('imported_material_slot_name'))
            if name not in entry['materials']:
                name = entry['materials'][min(i, len(entry['materials']) - 1)]
            name = re.sub(r'\.\d{3}$', '', name)
            mesh.set_material(i, materials[name])
        full_precision(mesh)
        save(mesh)

    # Update existing objects so equipped weapons, pickups and modifications all
    # keep their references. Materials are copied together with the new geometry.
    for entry in entries:
        path = BASE + '/Meshes/' + entry['name']
        old = u.load_asset(path)
        backup = DEST + '/PreviousMeshes/' + entry['name']
        if old and not E.does_asset_exist(backup):
            preserved = E.duplicate_asset(path, backup)
            if not preserved:
                raise RuntimeError('Cannot preserve previous staff mesh: ' + path)
            save(preserved)
            receipt['backups'].append(backup)
            record()
        new = u.load_asset(DEST + '/Meshes/' + entry['name'])
        if old:
            dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
                new, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
            if status != u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Cannot transfer geometry: ' + path)
            slots = list(new.get_editor_property('static_materials'))
            write = u.GeometryScriptCopyMeshToAssetOptions(
                enable_recompute_normals=False, enable_recompute_tangents=True,
                replace_materials=True,
                new_materials=[s.material_interface for s in slots],
                new_material_slot_names=[s.material_slot_name for s in slots], use_build_scale=False)
            _, status = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, old, write, u.GeometryScriptMeshWriteLOD())
            if status != u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Cannot install geometry: ' + path)
            old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'], 0, 'BarkRebuildV21')
        else:
            old = E.duplicate_asset(new.get_path_name(), path)
            if not old:
                raise RuntimeError('Cannot install ' + path)
        full_precision(old)
        save(old)
        receipt['installed'].append(entry['name'])
        record()
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))

receipt.update({'complete': True, 'active_mesh_root': BASE + '/Meshes',
                'versioned_mesh_root': DEST + '/Meshes', 'full_precision_uvs': True})
record()
print('STAFF_BARK_V21_SAVED meshes=' + str(len(receipt['installed'])))
