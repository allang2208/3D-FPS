"""M25 game-mesh production helpers. No runtime or visual acceptance is performed."""
from pathlib import Path
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
BASE = '/Game/Monsters/VortexCofferM25'
DEST = BASE + '/OptimizedV01'
REV = 'M25GameMesh20261005V1'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EDITOR = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
GAME_NAME = 'SK_M25_VortexCoffer_Game_V01'
WORK_NAME = 'SK_M25_ReductionSource_V01'
FBX = ROOT / (GAME_NAME + '.fbx')
TARGETS = [350000, 120000, 40000, 10000]
SCREENS = [1.0, 0.55, 0.22, 0.08]
SPEC = json.loads((ROOT.parent / 'RigV01/skeleton_spec.json').read_text(encoding='utf-8'))
PRIORITY_BONES = [b['name'] for b in SPEC if b['region'] in ('mouth', 'maw_rim', 'electrode', 'tendril_tip')]

def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Required asset missing: ' + path)
    return asset

def owned(path):
    if not LIB.does_asset_exist(path):
        return None
    asset = load(path)
    if LIB.get_metadata_tag(asset, 'M25.OptimizationRevision') != REV:
        raise RuntimeError('Preserving unowned asset: ' + path)
    return asset

def save(asset):
    LIB.set_metadata_tag(asset, 'M25.OptimizationRevision', REV)
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())
    return asset.get_path_name()

def write_receipt(filename, data):
    (ROOT / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def reduction(target, keep_source=False, lock_edges=True):
    settings = u.SkeletalMeshOptimizationSettings()
    values = dict(
        termination_criterion=u.SkeletalMeshTerminationCriterion.SMTC_NUM_OF_TRIANGLES if keep_source else u.SkeletalMeshTerminationCriterion.SMTC_ABS_NUM_OF_TRIANGLES,
        num_of_triangles_percentage=1.0, num_of_vert_percentage=1.0,
        max_num_of_triangles=target, max_bones_per_vertex=4,
        recalc_normals=False, remap_morph_targets=False,
        enforce_bone_boundaries=True, merge_coincident_vert_bones=True,
        welding_threshold=0.0001, volume_importance=1.0,
        lock_edges=lock_edges, improve_triangles_for_cloth=False, base_lod=0,
        silhouette_importance=u.SkeletalMeshOptimizationImportance.SMOI_HIGHEST,
        texture_importance=u.SkeletalMeshOptimizationImportance.SMOI_HIGH,
        shading_importance=u.SkeletalMeshOptimizationImportance.SMOI_HIGH,
        skinning_importance=u.SkeletalMeshOptimizationImportance.SMOI_HIGHEST)
    for key, value in values.items():
        settings.set_editor_property(key, value)
    return settings

def lod_settings(name, targets, keep_base=False):
    asset = owned(DEST + '/' + name)
    if asset is None:
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.SkeletalMeshLODSettings.static_class())
        asset = TOOLS.create_asset(name, DEST, u.SkeletalMeshLODSettings, factory)
        if asset is None:
            raise RuntimeError('LOD settings creation failed')
    groups = []
    for index, target in enumerate(targets):
        group = u.SkeletalMeshLODGroupSettings()
        screen = u.PerPlatformFloat()
        screen.set_editor_property('default', SCREENS[index])
        group.set_editor_property('screen_size', screen)
        group.set_editor_property('lod_hysteresis', 0.025)
        group.set_editor_property('bones_to_prioritize', PRIORITY_BONES)
        group.set_editor_property('weight_of_prioritization', 10.0)
        group.set_editor_property('bone_list', [])
        # Lock open edges in close views. Far LODs can simplify those edges as well,
        # while bone priorities, UV attributes and volume penalties remain active.
        group.set_editor_property('reduction_settings', reduction(target, keep_base and index == 0, lock_edges=index < 2))
        groups.append(group)
    asset.set_editor_property('lod_groups', groups)
    save(asset)
    return asset

def export_fbx(mesh, filename, all_lods=False):
    options = u.FbxExportOption()
    for key, value in dict(ascii=False, level_of_detail=all_lods, collision=False,
                           bake_material_inputs=u.FbxMaterialBakeMode.DISABLED,
                           export_source_mesh=False, export_morph_targets=False).items():
        options.set_editor_property(key, value)
    task = u.AssetExportTask()
    task.object = mesh
    task.filename = str(filename)
    task.exporter = u.SkeletalMeshExporterFBX()
    task.options = options
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('FBX export failed: ' + str(task.errors))

def production_context():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        raise RuntimeError('This high-memory production pass requires the closed-editor commandlet')

def mesh_receipt(mesh):
    data = u.AssetRegistryHelpers.create_asset_data(mesh)
    return dict(path=mesh.get_path_name(),
                lod_count=EDITOR.get_lod_count(mesh),
                vertices_by_lod=[EDITOR.get_num_verts(mesh, i) for i in range(EDITOR.get_lod_count(mesh))],
                sections_by_lod=[EDITOR.get_num_sections(mesh, i) for i in range(EDITOR.get_lod_count(mesh))],
                lod0_triangles=data.get_tag_value('Triangles'),
                bones=data.get_tag_value('Bones'),
                skeleton=mesh.get_editor_property('skeleton').get_path_name())
