# Commandlet batch: full v2 world reinstall (delete + fresh import + LODs + screen
# sizes + nanite off + Metal/Wood bind + save). import_lod is synchronous here.
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SPLIT = ROOT / 'SourceAssets/ToolEnhance20260925'
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

TOOLS_DEF = {
    'Axe': {
        'mesh_asset': '/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe',
        'mesh': SPLIT / 'Export/BattleAxe_16000.fbx',
        'lods': [SPLIT / 'Export/BattleAxe_LOD1.fbx', SPLIT / 'Export/BattleAxe_LOD2.fbx'],
        'wood': '/Game/Items/ProductionTools/BattleAxe20260919/M_BattleAxe',
        'stone': '/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_Axe_Stone',
    },
    'Pick': {
        'mesh_asset': '/Game/Items/ProductionTools/RusticPickaxe20260919/SM_RusticPickaxe',
        'mesh': SPLIT / 'Export/RusticPickaxe_World.fbx',
        'lods': [SPLIT / 'Export/RusticPickaxe_LOD1.fbx', SPLIT / 'Export/RusticPickaxe_LOD2.fbx'],
        'wood': '/Game/Items/ProductionTools/RusticPickaxe20260919/M_RusticPickaxe',
        'stone': '/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_Pick_Stone',
    },
}

report = {}
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for tag, cfg in TOOLS_DEF.items():
    if EAL.does_asset_exist(cfg['mesh_asset']):
        EAL.delete_asset(cfg['mesh_asset'])
    options = u.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = True
    options.static_mesh_import_data.generate_lightmap_u_vs = True
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(cfg['mesh'])
    task.destination_path = cfg['mesh_asset'].rsplit('/', 1)[0]
    task.destination_name = cfg['mesh_asset'].rsplit('/', 1)[1]
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    TOOLS.import_asset_tasks([task])
    mesh = u.load_asset(cfg['mesh_asset'])
    if mesh is None:
        raise RuntimeError('Import did not produce ' + cfg['mesh_asset'])
    got = [str(s.material_slot_name) for s in mesh.static_materials]
    if got != ['Metal', 'Wood']:
        raise RuntimeError('%s: slots %s' % (tag, got))
    for index, lod_file in enumerate(cfg['lods'], start=1):
        before = mesh.get_num_lods()
        ret = editor.import_lod(mesh, index, str(lod_file))
        after = mesh.get_num_lods()
        report.setdefault('lod_returns', []).append(
            {'tag': tag, 'index': index, 'ret': repr(ret), 'before': before, 'after': after})
        if after != index + 1:
            raise RuntimeError('Could not import %s LOD%d (ret=%s, lods=%d)' % (tag, index, ret, after))
    if not editor.set_lod_screen_sizes(mesh, [1.0, 0.35, 0.1]):
        raise RuntimeError('Could not set %s LOD screen sizes' % tag)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = False
    mesh.set_editor_property('nanite_settings', nanite)
    wood = u.load_asset(cfg['wood'])
    stone = u.load_asset(cfg['stone'])
    assigned = {}
    for index, name in enumerate(('Metal', 'Wood')):
        mat = stone if name == 'Metal' else wood
        mesh.set_material(index, mat)
        assigned[name] = mat.get_path_name()
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_package()], False):
        raise RuntimeError('Could not save ' + cfg['mesh_asset'])
    reread = u.load_asset(cfg['mesh_asset'])
    report[tag] = {'assigned': assigned, 'lods': reread.get_num_lods(),
                   'tris_lod0': reread.get_num_triangles(0),
                   'slots': [(str(s.material_slot_name),
                              s.material_interface.get_path_name() if s.material_interface else None)
                             for s in reread.static_materials]}
(SPLIT / 'ue-world-v2-receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
