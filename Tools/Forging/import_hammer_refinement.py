"""Save the compact hammer and readable guide, then install its profile only."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SRC = ROOT / 'SourceAssets/ForgeHammerRefine20261024'
DEST = '/Game/Props/ForgeInteraction20260927/HammerRefine20261024'
E = u.EditorAssetLibrary
authored = json.loads((SRC / 'authored.json').read_text(encoding='utf-8'))
destinations = {row['mesh'].rsplit('/', 1)[0] for row in authored['assets']}

dirty = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
if any(p.startswith(folder + '/') for p in dirty for folder in destinations):
    raise RuntimeError('Unsaved hammer refinement packages; preserve current editor work')

steel = u.load_asset('/Game/Props/ForgeInteraction20260927/M_ForgeHotSteel')
if steel is None:
    raise RuntimeError('Existing hot steel material unavailable')

sys.path.insert(0, str(ROOT / 'Tools/Forging'))
from forge_guide_material import build_guide_material
guide = build_guide_material(DEST + '/M_ForgeHammerGuide')
u.MaterialEditingLibrary.recompile_material(guide)
if not E.save_loaded_asset(guide, False):
    raise RuntimeError('Guide material save failed')

saved = [guide.get_path_name()]
for row in authored['assets']:
    target = row['mesh']
    mesh = u.load_asset(target) if E.does_asset_exist(target) else None
    if mesh is None:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_materials = False
        options.import_textures = False
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.convert_scene = True
        data.convert_scene_unit = True
        data.transform_vertex_to_absolute = True
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        task = u.AssetImportTask()
        task.filename = row['file']
        task.destination_path = target.rsplit('/', 1)[0]
        task.destination_name = target.rsplit('/', 1)[-1]
        task.automated = True
        task.replace_existing = False
        task.save = False
        task.options = options
        task.factory = u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = u.load_asset(target)
    if mesh is None:
        raise RuntimeError('Import failed: ' + target)
    mesh.modify()
    mesh.set_material(0, guide if target.endswith('Guide') else steel)
    if target.endswith('Guide'):
        # Four translucent vertices are an interaction overlay, not Nanite geometry.
        settings = mesh.get_editor_property('nanite_settings')
        settings.enabled = False
        mesh.set_editor_property('nanite_settings', settings)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Save failed: ' + target)
    saved.append(mesh.get_path_name())

# Read at installation time; preserve every other blank and concurrent edit.
runtime_path = ROOT / 'Content/ColdSteelData/forge-blanks.json'
raw = runtime_path.read_text(encoding='utf-8-sig')
runtime = json.loads(raw)
backup = SRC / 'warhammer_profile_before.json'
if not backup.exists():
    backup.write_text(json.dumps(runtime['profiles']['warhammer'], ensure_ascii=False, indent=2), encoding='utf-8')
profiles = json.loads((SRC / 'profiles.json').read_text(encoding='utf-8'))['profiles']
exported = {row['mesh'] for row in authored['assets']}
installed = []
for key, profile in profiles.items():
    if all(stage['mesh'] in exported for stage in profile['stages']):
        runtime['profiles'][key] = profile
        installed.append(key)
if runtime_path.read_text(encoding='utf-8-sig') != raw:
    raise RuntimeError('Blank profiles changed during installation; assets saved, reference not installed')
runtime_path.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt = {'saved': saved, 'runtime_profiles_installed': installed,
           'runtime_tested': False, 'rendered': False}
(SRC / 'import_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('FORGE_HAMMER_REFINEMENT_SAVED ' + json.dumps(receipt))
