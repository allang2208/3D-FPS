"""Import Style V1 meshes and materials without changing the active monsters.

Run through UE Python with the editor closed. No previews or runtime checks.
"""
import json
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/MonsterStyleV1'
LIB = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
MASTER = '/Game/Monsters/Shared/InfectedSurfaceV1/M_InfectedSurface_V1'
TARGETS = {
    'handbrain': {
        'folder': '/Game/Monsters/HandBrain/StyleV1',
        'mesh_name': 'SK_HandBrain_StyleV1',
        'old_mesh': '/Game/Monsters/HandBrain/SurfaceV07/SK_HandBrain_Surface',
        'blueprint': '/Game/Monsters/HandBrain/BP_HandBrain'},
    'maggot': {
        'folder': '/Game/Monsters/PoisonMaggot/StyleV1',
        'mesh_name': 'SK_PoisonMaggot_StyleV1',
        'old_mesh': '/Game/Monsters/PoisonMaggot/SK_PoisonMaggot',
        'blueprint': '/Game/Monsters/PoisonMaggot/BP_PoisonMaggot'},
    'mutant': {
        'folder': '/Game/Monsters/Mutant3Meshy/StyleV1',
        'old_mesh': '/Game/Monsters/Mutant3Meshy/SK_Mutant3_Meshy'}
}

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())

def load(path):
    asset = u.load_asset(path)
    if asset is None: raise RuntimeError('Required asset missing: ' + path)
    return asset

def import_asset(filename, name, folder, options=None):
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None: task.options = options
    TOOLS.import_asset_tasks([task])
    return load(folder + '/' + name)

master = load(MASTER)
report = {'master': master.get_path_name(), 'monsters': {},
          'activated': False, 'preview_rendered': False, 'runtime_tested': False}
for mode, target in TARGETS.items():
    source = json.loads((ROOT / mode / 'authoring_manifest.json').read_text(encoding='utf-8'))
    materials = {}
    textures_report = {}
    for record in source['materials']:
        textures = {}
        for semantic, filename in record['textures'].items():
            tex = import_asset(filename, Path(filename).stem, target['folder'] + '/Textures')
            tex.set_editor_property('srgb', semantic == 'BaseColor')
            tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP
                if semantic == 'Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
            if semantic == 'Normal':
                tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property('flip_green_channel', False)
            elif semantic in ('ORM', 'TissueMasks'):
                tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
            save(tex)
            textures[semantic] = tex
        name = 'MI_' + record['name']
        instance = u.load_asset(target['folder'] + '/' + name) or TOOLS.create_asset(
            name, target['folder'], u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(instance, master)
        for semantic, tex in textures.items():
            MEL.set_material_instance_texture_parameter_value(instance, semantic, tex)
        # Species-specific values share the same dry skin / wet tissue contract.
        for parameter, value in {
            'NormalStrength': 1.0, 'WoundWetness': 1.0,
            'DrySpecular': .28 if mode != 'maggot' else .30,
            'WetSpecular': .35 if mode != 'maggot' else .36}.items():
            MEL.set_material_instance_scalar_parameter_value(instance, parameter, value)
        MEL.update_material_instance(instance)
        LIB.set_metadata_tag(instance, 'MonsterStyle.Revision', 'SharedSurfaceV1')
        save(instance)
        materials[record['name']] = instance
        textures_report[record['name']] = {k: v.get_path_name() for k, v in textures.items()}

    mesh = None
    if source['mesh_fbx']:
        previous = load(target['old_mesh'])
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal = True
        options.import_mesh = True
        options.import_animations = False
        options.import_materials = False
        options.import_textures = False
        options.create_physics_asset = False
        options.skeleton = previous.skeleton
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)
        mesh = import_asset(source['mesh_fbx'], target['mesh_name'], target['folder'], options)
        mesh.set_editor_property('physics_asset', previous.get_editor_property('physics_asset'))
        slots = mesh.get_editor_property('materials')
        for index, slot in enumerate(slots):
            key = str(slot.get_editor_property('imported_material_slot_name'))
            if key not in materials: key = str(slot.material_slot_name)
            if key not in materials:
                raise RuntimeError('No authored material for imported slot: ' + key)
            slot.material_interface = materials[key]
            slots[index] = slot
        mesh.set_editor_property('materials', slots)
        save(mesh)
    report['monsters'][mode] = dict(target, mesh=mesh.get_path_name() if mesh else target['old_mesh'],
        materials={k: v.get_path_name() for k, v in materials.items()}, textures=textures_report)
    u.log('MONSTER_STYLE_IMPORTED ' + mode)

(ROOT / 'ue_import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('MONSTER_STYLE_IMPORT_COMPLETE')
