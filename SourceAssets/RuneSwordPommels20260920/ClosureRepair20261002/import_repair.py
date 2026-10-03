"""Save the corrected shared meteor mesh/PBR assets in one UE bridge batch."""
import unreal as u, json, shutil
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent
ROOT = SOURCE.parents[1]
D = '/Game/Weapons/AzureRunesword20260913/Pommels20260920'
A = u.AssetToolsHelpers.get_asset_tools()
L = u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('The meteor repair must run in FPSGAME')
commandlet = '-run=' in u.SystemLibrary.get_command_line().lower()
editor = None if commandlet else u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor and editor.is_in_play_in_editor():
    raise RuntimeError('Meteor source is repaired; end PIE before updating the loaded shared asset')

row = next(r for r in json.loads((SOURCE/'model_exports.json').read_text()) if r['id']=='meteor')
asset_path = D+'/Models/SM_RunePommel_Meteor'
affected = {asset_path} | {D+'/Textures/T_Pommel_meteor_'+key for key in row['textures']}
dirty = [] if commandlet else [pkg.get_name() for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if pkg.get_name() in affected]
if dirty:
    raise RuntimeError('Retained unsaved meteor asset changes: '+str(dirty))
old_mesh = u.load_asset(asset_path)
if not old_mesh:
    raise RuntimeError('The existing shared meteor mesh is missing')
old_nanite = old_mesh.get_editor_property('nanite_settings')
receipt = {'revision': 'MeteorShellOutward20261002', 'assets': [], 'complete': False,
           'runtime_tested': False, 'root_cause': 'Shared closed meteor body has inward triangle winding',
           'shared_asset_path_preserved': True, 'lod_ratios': [1.0, .55, .25]}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Meteor repair save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    print('METEOR_ASSET_SAVED', asset.get_path_name(), flush=True)
    (P/'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

for key, file in row['textures'].items():
    task = u.AssetImportTask()
    task.filename = file
    task.destination_path = D+'/Textures'
    task.destination_name = 'T_Pommel_meteor_'+key
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    tex = u.load_asset(D+'/Textures/'+task.destination_name)
    if not tex or not task.imported_object_paths:
        raise RuntimeError('Meteor PBR import failed: '+key)
    tex.set_editor_property('srgb', key in ['BaseColor', 'Emissive'])
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if key in ['BaseColor', 'Emissive'] else u.TextureCompressionSettings.TC_MASKS)
    if key=='Normal':
        tex.set_editor_property('flip_green_channel', True)
    save(tex)

u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal = False
opt.import_mesh = True
opt.import_materials = False
opt.import_textures = False
opt.import_animations = False
opt.lod_number = 3
opt.auto_compute_lod_distances = True
data = opt.static_mesh_import_data
data.combine_meshes = False
data.import_mesh_lods = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task = u.AssetImportTask()
task.filename = str(P/'SM_RunePommel_Meteor_LODs.fbx')
task.destination_path = D+'/Models'
task.destination_name = 'SM_RunePommel_Meteor'
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
task.options = opt
A.import_asset_tasks([task])
mesh = u.load_asset(asset_path)
if not mesh or not task.imported_object_paths:
    raise RuntimeError('Corrected shared meteor mesh import failed')
for index, slot in enumerate(mesh.static_materials):
    name = str(slot.material_slot_name)
    material = u.load_asset(D+'/Materials/'+name)
    if not material:
        raise RuntimeError('Shared meteor material slot has no existing material: '+name)
    mesh.set_material(index, material)
mesh.set_editor_property('nanite_settings', old_nanite)

sub = None if commandlet else u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if sub:
    reduction = u.StaticMeshReductionOptions()
    reduction.auto_compute_lod_screen_size = True
    reduction.reduction_settings = [u.StaticMeshReductionSettings(percent_triangles=ratio, screen_size=size)
                                    for ratio, size in [(1.0, 1.0), (.55, .5), (.25, .2)]]
    if sub.set_lods(mesh, reduction) != 3:
        raise RuntimeError('Could not rebuild all three meteor LODs')
else:
    # The FBX contains all three corrected meshes, so the commandlet imports
    # each LOD directly instead of retaining the previous inward surfaces.
    receipt['lod_import_mode'] = 'Explicit corrected FBX LOD group in commandlet'
L.set_metadata_tag(mesh, 'MeteorShellRevision', receipt['revision'])
save(mesh)
export = u.AssetExportTask()
export.object = mesh
export.filename = str(P/'SavedUE_Meteor_LODs.fbx')
export.automated = True
export.prompt = False
export.replace_identical = True
export.exporter = u.StaticMeshExporterFBX()
export.options = u.FbxExportOption()
export.options.ascii = False
export.options.level_of_detail = True
export.options.collision = False
if not u.Exporter.run_asset_export_task(export):
    raise RuntimeError('Could not record the saved meteor geometry for the requested diagnosis')
receipt['material_slots'] = [{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name()} for s in mesh.static_materials]
receipt['affected_hosts'] = [file.name for file in (ROOT/'Content/ColdSteelData').glob('*-modules.json')
                             if json.loads(file.read_text(encoding='utf-8-sig')).get('pommel_profile', {}).get('library')=='shared-sword-pommels.json']
receipt['complete'] = True
(P/'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('METEOR_REPAIR_SAVED', json.dumps(receipt, ensure_ascii=False))
