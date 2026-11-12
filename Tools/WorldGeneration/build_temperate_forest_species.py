"""Install the locally available woodland species without rebuilding the level.

Run with the project's serialized background Python commandlet wrapper. Original
Fab packages remain untouched. Tree palette slots stay stable; native generation
selects beech as the primary species while retaining a small poplar admixture.
"""
import json
import re
import runpy
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/TemperateForestSpecies20261110'
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE + '/ForestSpecies20261110'
DA_PATH = BASE + '/DA_TemperateHillsStreaming'
GRAPH_PATH = BASE + '/PCG_HillsShrubs'
BEECH = '/Game/Megaplant_Library/Tree_European_Beech'
HAZEL = '/CitySamplePCG/Megaplants/Tree_Common_Hazel'
CITY_BEECH = '/CitySamplePCG/Megaplants/Tree_European_Beech'
FERN = '/Game/Megaplant_Library/Plant_Bracken_Fern'
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'saved': [], 'source_assets_modified': False, 'map_modified': False,
          'runtime_tested': False, 'visual_tested': False}
BACKUP = ROOT / 'Backups' / ('Assets-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
BACKED_UP = set()
MESH_COPIES = {}


def backup(path):
    package = path.split('.')[0]
    if package in BACKED_UP or not package.startswith('/Game/'):
        return
    BACKED_UP.add(package)
    rel = package[len('/Game/'):]
    for suffix in ('.uasset', '.uexp', '.ubulk'):
        source = PROJECT / 'Content' / (rel + suffix)
        if source.exists():
            target = BACKUP / (rel + suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def load(path):
    result = u.load_asset(path)
    if result is None:
        raise RuntimeError('Required woodland asset not available: ' + path)
    return result


def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Unable to save: ' + asset.get_path_name())
    REPORT['saved'].append(asset.get_path_name())
    return asset


def duplicate(source, target):
    backup(target)
    result = load(target) if EAL.does_asset_exist(target) else AT.duplicate_asset(
        target.rsplit('/', 1)[1], target.rsplit('/', 1)[0], load(source))
    if result is None:
        raise RuntimeError('Unable to duplicate: ' + source)
    return result


def clone_material(source, parent, texture_cache):
    src = load(source)
    target = DEST + '/Materials/' + src.get_name()
    mi = duplicate(source, target)
    LIB.set_material_instance_parent(mi, parent)
    for key in LIB.get_texture_parameter_names(src):
        texture = LIB.get_material_instance_texture_parameter_value(src, key)
        if texture is None:
            continue
        source_path = texture.get_path_name()
        if source_path not in texture_cache:
            copied = duplicate(source_path, DEST + '/Textures/' + texture.get_name())
            # NAH/NT are custom packed maps, not ordinary tangent normals.
            # Keep the original compression and colour space for the PVE shader.
            copied.set_editor_property('max_texture_size', 2048)
            copied.set_editor_property('never_stream', False)
            texture_cache[source_path] = save(copied)
        LIB.set_material_instance_texture_parameter_value(mi, key, texture_cache[source_path])
    LIB.update_material_instance(mi)
    return save(mi)


def clone_mesh(source, name, material_map):
    source = load(source).get_path_name()
    if source in MESH_COPIES:
        return MESH_COPIES[source]
    mesh = duplicate(source, DEST + '/Meshes/' + name)
    MESH_COPIES[source] = mesh
    prop = 'materials' if isinstance(mesh, u.SkeletalMesh) else 'static_materials'
    slots = list(load(source).get_editor_property(prop))
    for slot in slots:
        current = slot.get_editor_property('material_interface')
        replacement = material_map[current.get_path_name()]
        slot.set_editor_property('material_interface', replacement)
    mesh.set_editor_property(prop, slots)
    # Nanite assemblies retain source part paths; carry local donor branches and
    # leaves into /Game too, rather than relying on a temporary plugin mount.
    if source.startswith('/CitySamplePCG/'):
        settings = load(source).get_editor_property('nanite_settings')
        assembly = settings.get_editor_property('nanite_assembly_data')
        parts = list(assembly.get_editor_property('parts'))
        settings_text = settings.export_text()
        for part in parts:
            match = re.search(r'/CitySamplePCG/[^\s\"\x27(),]+', part.export_text())
            if match:
                part_path = match.group(0)
                part_source = load(part_path)
                family = 'Hazel_' if '/Tree_Common_Hazel/' in part_path else 'Beech_'
                copied = clone_mesh(part_path, 'SM_Part_' + family + part_source.get_name(), material_map)
                settings_text = settings_text.replace(part_path, copied.get_path_name())
        # Assembly's nested fields are VisibleAnywhere; import the complete
        # settings value to preserve its node transforms and material remaps.
        settings.import_text(settings_text)
        mesh.set_editor_property('nanite_settings', settings)
    return save(mesh)


def import_floor():
    for name, compression, srgb in (
            ('T_ForestFloor_BaseColor', u.TextureCompressionSettings.TC_DEFAULT, True),
            ('T_ForestFloor_Normal', u.TextureCompressionSettings.TC_NORMALMAP, False),
            ('T_ForestFloor_ARH', u.TextureCompressionSettings.TC_MASKS, False)):
        target = DEST + '/Textures/' + name
        backup(target)
        task = u.AssetImportTask()
        task.set_editor_property('filename', str(ROOT / 'Textures' / (name + '.png')))
        task.set_editor_property('destination_path', DEST + '/Textures')
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('save', False)
        AT.import_asset_tasks([task])
        texture = load(target)
        texture.set_editor_property('compression_settings', compression)
        texture.set_editor_property('srgb', srgb)
        texture.set_editor_property('max_texture_size', 2048)
        texture.set_editor_property('never_stream', False)
        save(texture)


def install_ferns(da):
    """Fill the existing streamed understory layer with four whole-plant exports."""
    sources = [load(FERN + '/Plant_Bracken_Fern_01/Plant_Bracken_Fern_01_' + v) for v in 'ABCD']
    if any(not isinstance(mesh, u.SkeletalMesh) for mesh in sources):
        raise RuntimeError('ForestFerns requires whole-plant skeletal exports')
    source_mi = load(FERN + '/Materials/MI_Bracken_Fern_01')
    material = clone_material(source_mi.get_path_name(), load(DEST + '/Materials/M_ForestPCG'), {})
    materials = {source_mi.get_path_name(): material}
    ferns = [clone_mesh(mesh.get_path_name(), 'SK_BrackenFern_' + v, materials)
             for mesh, v in zip(sources, 'ABCD')]
    da.set_editor_property('forest_ferns', ferns)
    REPORT['bracken_fern'] = len(ferns)
    REPORT['fern_sources'] = [{'path': mesh.get_path_name(),
                               'height_cm': mesh.get_bounds().box_extent.z * 2,
                               'nanite': mesh.get_editor_property('nanite_settings').get_editor_property('enabled')}
                              for mesh in sources]
    return ferns


def connect_understory():
    graph = load(GRAPH_PATH)
    backup(GRAPH_PATH)
    generator = None
    output = None
    for node in graph.get_editor_property('nodes'):
        settings = node.get_settings()
        if isinstance(settings, u.TemperateHillsPointsSettings) and settings.get_editor_property('layer') == 4:
            generator = node
        if isinstance(settings, u.PCGSkinnedMeshSpawnerSettings):
            output = node
    if generator is None:
        generator, settings = graph.add_node_of_type(u.TemperateHillsPointsSettings)
        settings.set_editor_property('layer', 4)
    if output is None:
        output, spawn = graph.add_node_of_type(u.PCGSkinnedMeshSpawnerSettings)
    else:
        spawn = output.get_settings()
    selector = spawn.get_editor_property('mesh_selector_parameters')
    attribute = selector.get_editor_property('mesh_attribute')
    attribute.import_text('PCGBegin(Mesh)PCGEnd')
    selector.set_editor_property('mesh_attribute', attribute)
    tree_graph = load(BASE + '/PCG_BlackPoplar')
    tree_spawn = next(n.get_settings() for n in tree_graph.get_editor_property('nodes')
                      if isinstance(n.get_settings(), u.PCGSkinnedMeshSpawnerSettings))
    descriptor = tree_spawn.get_editor_property('mesh_selector_parameters').get_editor_property('template_descriptor')
    body = descriptor.get_editor_property('body_instance')
    body.set_editor_property('collision_profile_name', 'NoCollision')
    descriptor.set_editor_property('body_instance', body)
    descriptor.set_editor_property('cast_shadow', True)
    descriptor.set_editor_property('component_tags', ['TemperateHills', 'ForestUnderstory'])
    descriptor.set_editor_property('instance_start_cull_distance', 4500)
    descriptor.set_editor_property('instance_end_cull_distance', 7000)
    selector.set_editor_property('template_descriptor', descriptor)
    graph.add_edge(generator, 'Out', output, 'In')
    graph.add_edge(output, 'Out', graph.get_output_node(), 'Out')
    save(graph)


def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Cannot author woodland assets during PIE')
    shared = {DA_PATH, GRAPH_PATH, BASE + '/M_TemperateGround', BASE + '/PebbleShore/M_PebbleShoreGround'}
    conflicts = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                 if p.get_name() in shared or p.get_name().startswith(DEST)]
    if conflicts:
        raise RuntimeError('Preserve unsaved packages: ' + repr(conflicts))
    if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
        # The donor's branches can otherwise still be building at commandlet shutdown.
        u.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Editor.AsyncStaticMeshCompilation 0')
    da = load(DA_PATH)
    # A native build must precede asset authoring so these reflected properties exist.
    da.get_editor_property('forest_saplings')
    backup(DA_PATH)
    u.SystemLibrary.execute_console_command(editor.get_editor_world(),
        'PackageName.RegisterMountPoint /CitySamplePCG/ "D:/FPS3D/FPSGAME/城市示例/Plugins/Experimental/CitySamplePCG/Content/"')
    u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/CitySamplePCG/Megaplants'], True)
    for path in (DEST + '/Textures', DEST + '/Materials', DEST + '/Meshes'):
        EAL.make_directory(path)

    parent = duplicate('/ProceduralVegetationEditor/SampleAssets/Materials/MasterMaterials/MA_Foliage_Trees',
                       DEST + '/Materials/M_ForestPCG')
    parent.set_editor_property('used_with_instanced_skinned_mesh', True)
    parent.set_editor_property('used_with_instanced_static_meshes', True)
    LIB.recompile_material(parent)
    save(parent)
    materials = {}
    textures = {}
    for root, names in ((BEECH, ['MI_European_Beech_Bark_01', 'MI_European_Beech_Foliage_01']),
                        (HAZEL, ['MI_Common_Hazel_Bark_01', 'MI_Common_Hazel_Foliage_01'])):
        for name in names:
            source = root + '/Materials/' + name
            materials[load(source).get_path_name()] = clone_material(source, parent, textures)
    for name in ['MI_European_Beech_Bark_01', 'MI_European_Beech_Foliage_01']:
        # Both locally installed beech exports use the same PVE material family.
        materials[load(CITY_BEECH + '/Materials/' + name).get_path_name()] = materials[load(BEECH + '/Materials/' + name).get_path_name()]

    adults = [clone_mesh(BEECH + '/Tree_European_Beech_01/Tree_European_Beech_01_' + v,
                         'SK_Beech_' + v, materials) for v in 'ABCD']
    saplings = [clone_mesh(BEECH + '/Tree_European_Beech_Saplings_01/Tree_European_Beech_Sapling_01_' + v,
                           'SK_BeechSapling_' + v, materials) for v in 'ABCD']
    hazel = [clone_mesh(HAZEL + '/Tree_Common_Hazel_01/SM_Common_Hazel_01_' + v,
                        'SM_Hazel_' + v, materials) for v in 'ABCD']
    # Slot order is an identity contract, not a species weight. TreeCandidate
    # selects beech across the established canopy as well as infill points.
    original_trees = list(da.get_editor_property('trees'))[:4]
    da.set_editor_property('trees', original_trees + adults)
    da.set_editor_property('forest_saplings', saplings)
    da.set_editor_property('shrubs', hazel)
    da.set_editor_property('backdrop_trees', [clone_mesh(
        CITY_BEECH + '/Tree_European_Beech_01/SM_European_Beech_01_' + v,
        'SM_BeechBackdrop_' + v, materials) for v in 'AB'])
    ferns = install_ferns(da)
    connect_understory()
    import_floor()
    # Retain the current landscape, river blend and all map actors.
    ground = runpy.run_path(str(PROJECT / 'Tools/WorldGeneration/build_hills_ground_v2.py'), run_name='__main__')
    REPORT['saved'].extend(ground['REPORT']['saved'])
    save(da)
    # Reapply the authored wind parent/provider after refreshing species assets.
    # This entry preserves the level and the current light/weather ownership.
    atmosphere = runpy.run_path(str(PROJECT / 'Tools/WorldGeneration/build_temperate_forest_atmosphere.py'), run_name='__main__')
    REPORT['saved'].extend(atmosphere['REPORT']['saved'])
    REPORT.update({'adult_beech': len(adults), 'beech_saplings': len(saplings), 'hazel': len(hazel),
                   'hazel_source': HAZEL, 'forest_floor_scan': 'wgykaio',
                   'bracken_fern': len(ferns),
                   'old_tree_slots_preserved': 4})
    (ROOT / 'Receipts' / 'assets.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('FOREST_SPECIES_SAVED ' + json.dumps(REPORT, ensure_ascii=False))


if __name__ == '__main__':
    main()
