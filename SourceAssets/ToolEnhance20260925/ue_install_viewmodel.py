# Stage C: replace both tool viewmodels with the Metal/Wood split exports and
# bind slots by name (arms keep their current materials, Metal takes the factory
# stone instance, Wood takes the original tool material). Commandlet-safe.
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SPLIT = ROOT / 'SourceAssets/ToolEnhance20260925'
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

ARMS = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'
TARGETS = {
    'Axe': {
        'sk': '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe',
        'fbx': SPLIT / 'Viewmodel/Export/SK_Harvest_Axe.fbx',
        'stone': '/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_Axe_Stone',
        'wood': '/Game/Items/ProductionTools/BattleAxe20260919/M_BattleAxe',
    },
    'Pick': {
        'sk': '/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe',
        'fbx': SPLIT / 'Viewmodel/Export/SK_RusticPickaxe.fbx',
        'stone': '/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_Pick_Stone',
        'wood': '/Game/Items/ProductionTools/RusticPickaxe20260919/M_RusticPickaxe',
    },
}

report = {}
for tag, cfg in TARGETS.items():
    old = u.load_asset(cfg['sk'])
    if old is None:
        raise RuntimeError('Missing viewmodel: ' + cfg['sk'])
    previous = {str(slot.material_slot_name): slot.material_interface
                for slot in old.get_editor_property('materials')}
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    options.skeletal_mesh_import_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task = u.AssetImportTask()
    task.filename = str(cfg['fbx'])
    task.destination_path = cfg['sk'].rsplit('/', 1)[0]
    task.destination_name = cfg['sk'].rsplit('/', 1)[1]
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    TOOLS.import_asset_tasks([task])
    mesh = u.load_asset(cfg['sk'])
    if mesh is None:
        raise RuntimeError('Import did not produce ' + cfg['sk'])

    stone = u.load_asset(cfg['stone'])
    wood = u.load_asset(cfg['wood'])
    if stone is None or wood is None:
        raise RuntimeError('Stage C needs stage A/B materials for ' + tag)
    slots = mesh.get_editor_property('materials')
    resolved = []
    for index, slot in enumerate(slots):
        name = str(slot.material_slot_name)
        if name == 'Metal':
            material = stone
        elif name == 'Wood':
            material = wood
        elif name in previous and previous[name] is not None:
            material = previous[name]
        else:
            raise RuntimeError('Unmapped viewmodel slot on %s: %s' % (tag, name))
        slot.material_interface = material
        slots[index] = slot
        resolved.append({'slot': name, 'material': material.get_path_name()})
    mesh.set_editor_property('materials', slots)
    mesh.set_editor_property('positive_bounds_extension', u.Vector(80, 80, 80))
    mesh.set_editor_property('negative_bounds_extension', u.Vector(80, 80, 80))
    skeleton = mesh.get_editor_property('skeleton')
    if skeleton is None:
        raise RuntimeError('Imported viewmodel has no skeleton: ' + tag)
    # 保存必须走 save_packages 并回读校验：EAL.save_asset／save_loaded_asset 在 PIE
    # 期间会静默返回 false（2026-09-25 事故：task.save 先落了导入态，绑定没落盘，
    # 游戏里金属槽退回 WorldGridMaterial，镐头在白测试场里"消失"）。
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_package(), skeleton.get_package()], False):
        raise RuntimeError('Could not save viewmodel packages: ' + tag)
    reread = u.load_asset(cfg['sk'])
    got = {str(s.material_slot_name): (s.material_interface.get_path_name() if s.material_interface else None)
           for s in reread.get_editor_property('materials')}
    for entry in resolved:
        if got.get(entry['slot']) != entry['material']:
            raise RuntimeError('Save did not persist slot %s on %s: %s' % (entry['slot'], tag, got))
    report[tag] = {'asset': mesh.get_path_name(), 'slots': resolved,
                   'skeleton': skeleton.get_path_name(),
                   'previous_slots': sorted(previous)}

(SPLIT / 'ue-viewmodel-receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
