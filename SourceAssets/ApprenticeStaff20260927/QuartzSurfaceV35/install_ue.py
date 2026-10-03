"""Import the two V35 default-quartz meshes/maps and save at current paths.

Only the original default head is changed. Existing runtime paths, UI coverage,
lamp controls, wood, elemental heads, inventory and gameplay remain compatible.
"""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE + '/QuartzSurfaceV35'
WORLD = BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
entries = json.loads((ROOT / 'Export/meshes.json').read_text(encoding='utf-8'))
inputs = json.loads((ROOT / 'inputs-receipt.json').read_text(encoding='utf-8'))
receipt = {'revision': 35, 'complete': False, 'stage': 'surface-and-transmission',
           'saved_assets': [], 'installed': [], 'backups': inputs['backups'],
           'runtime_tested': False, 'rendered': False, 'internal_volume_added': False,
           'refraction_added': False, 'lamp_changed': False, 'cpp_changed': False}


def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


targets = {WORLD, PREVIEW}
targets.update(BASE + group + e['name'] for group in ('/Meshes/', '/BarkRebuildV21/Meshes/') for e in entries)
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = [p for p in dirty if p in targets or p.startswith(DEST + '/')]
if conflicts:
    raise RuntimeError('Unsaved default quartz targets: ' + ', '.join(conflicts))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('Default quartz replacement requires PIE to end; current assets preserved.')

for suffix in ('Normal', 'Masks'):
    name = 'T_QuartzSurface_' + suffix + '_V35'
    task = u.AssetImportTask()
    for key, value in {'filename': str(ROOT / 'Export/Textures' / (name + '.png')),
                       'destination_path': DEST + '/Textures', 'destination_name': name,
                       'automated': True, 'replace_existing': True, 'save': False}.items():
        task.set_editor_property(key, value)
    A.import_asset_tasks([task])
    texture = u.load_asset(DEST + '/Textures/' + name)
    if not texture:
        raise RuntimeError('Quartz texture import failed ' + name)
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if suffix == 'Normal' else u.TextureCompressionSettings.TC_MASKS)
    if suffix == 'Normal':
        texture.set_editor_property('flip_green_channel', True)
    texture.set_editor_property('max_texture_size', 512)
    save(texture)

builder = runpy.run_path(str(ROOT / 'ue_material.py'))['build_quartz_material']
candidate_world = builder(rebuild=True, candidate=True)
candidate_preview = builder(rebuild=True, preview=True, candidate=True)
receipt['saved_assets'] += [candidate_world.get_path_name(), candidate_preview.get_path_name()]
record()
materials = {}
for entry in entries:
    for slot in entry['slots']:
        path = slot['material']
        if not path:
            raise RuntimeError('Retained staff material slot is empty')
        materials[path] = u.load_asset(path)
        if not materials[path]:
            raise RuntimeError('Missing retained staff material ' + path)

mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    options = u.FbxImportUI()
    for key, value in {'import_mesh': True, 'import_as_skeletal': False,
                       'mesh_type_to_import': u.FBXImportType.FBXIT_STATIC_MESH,
                       'automated_import_should_detect_type': False, 'import_materials': False,
                       'import_textures': False}.items():
        options.set_editor_property(key, value)
    data = options.get_editor_property('static_mesh_import_data')
    for key, value in {'combine_meshes': True, 'auto_generate_collision': False,
                       'import_uniform_scale': 1., 'convert_scene': True, 'convert_scene_unit': False,
                       'normal_import_method': u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                       'vertex_color_import_option': u.VertexColorImportOption.REPLACE}.items():
        data.set_editor_property(key, value)
    for entry in entries:
        task = u.AssetImportTask()
        for key, value in {'filename': entry['fbx'], 'destination_path': DEST + '/Meshes',
                           'destination_name': entry['name'], 'automated': True,
                           'replace_existing': True, 'save': False, 'options': options}.items():
            task.set_editor_property(key, value)
        A.import_asset_tasks([task])
        mesh = u.load_asset(DEST + '/Meshes/' + entry['name'])
        if not mesh:
            raise RuntimeError('Default quartz mesh import failed ' + entry['name'])
        if len(mesh.static_materials) != len(entry['slots']):
            raise RuntimeError('Default quartz material slot count changed ' + entry['name'])
        for i, slot in enumerate(entry['slots']):
            mesh.set_material(i, candidate_world if slot['material'].split('.')[-1].startswith('M_Staff_Quartz')
                              else materials[slot['material']])
        settings = mesh_editor.get_lod_build_settings(mesh, 0)
        settings.use_full_precision_u_vs = True
        settings.recompute_normals = False
        mesh_editor.set_lod_build_settings(mesh, 0, settings)
        save(mesh)

    # Author/import the entire candidate before touching the current packages.
    active_world = builder(rebuild=True)
    active_preview = builder(rebuild=True, preview=True)
    receipt['saved_assets'] += [active_world.get_path_name(), active_preview.get_path_name()]
    record()
    for entry in entries:
        mesh = u.load_asset(DEST + '/Meshes/' + entry['name'])
        dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh, u.DynamicMesh(),
            u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
        if status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot transfer candidate geometry ' + entry['name'])
        slots = list(mesh.static_materials)
        installed_materials = [active_world if s.material_interface == candidate_world else s.material_interface for s in slots]
        for group in ('/Meshes/', '/BarkRebuildV21/Meshes/'):
            target = BASE + group + entry['name']
            old = u.load_asset(target)
            if not old:
                raise RuntimeError('Missing stable staff mesh ' + target)
            write = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True,
                replace_materials=True, new_materials=installed_materials,
                new_material_slot_names=[s.material_slot_name for s in slots], use_build_scale=False)
            _, status = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, old, write, u.GeometryScriptMeshWriteLOD())
            if status != u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Cannot install default quartz ' + target)
            old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'], 0, 'QuartzSurfaceV35')
            settings = mesh_editor.get_lod_build_settings(old, 0)
            settings.use_full_precision_u_vs = True
            settings.recompute_normals = False
            mesh_editor.set_lod_build_settings(old, 0, settings)
            save(old)
            receipt['installed'].append(target)
            record()
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))

receipt['complete'] = True
record()
print('STAFF_QUARTZ_V35_SAVED meshes=4 materials=4 textures=2 tested=false rendered=false')
