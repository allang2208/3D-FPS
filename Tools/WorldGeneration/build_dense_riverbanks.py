"""Author the denser riverbank plant set and connect the current biome data asset.

Run with the updated FPSGAMEEditor module and -run=pythonscript -nullrhi.
This is asset authoring only; it does not load a map or run gameplay.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE + '/RiverEcologyDense'
OUT = ROOT / 'Saved/RiverbankDense20260914'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / ('BeforeAuthoring-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
REPORT = {
    'sources': [
        'https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303',
        'https://www.fab.com/listings/ef6db212-dfcf-4a50-8ade-fbca49963240'],
    'scope': 'Existing licensed local pack copies; authoring and integration only; no gameplay tests',
    'meshes': [], 'saved': []}


def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing riverbank source: ' + path)
    return obj


def backup(path):
    source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    if source.exists():
        target = BACKUP / source.relative_to(ROOT / 'Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def copy(source, target):
    backup(target)
    obj = load(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source, target)
    if obj is None:
        raise RuntimeError('Could not duplicate ' + source)
    return obj


def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save ' + obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    return obj


EAL.make_directory(DEST)
masters = {}
materials = {}


def plant(path, group):
    source = load(path)
    mesh = copy(path, DEST + '/SM_RiverDense_' + source.get_name())
    for index, slot in enumerate(source.get_editor_property('static_materials')):
        original = slot.material_interface
        key = (original.get_path_name(), group)
        if key not in materials:
            parent = original.get_editor_property('parent')
            parent_path = parent.get_path_name()
            if parent_path not in masters:
                master = copy(parent_path, DEST + '/M_RiverDense_' + parent.get_name())
                master.set_editor_property('used_with_instanced_static_meshes', True)
                opacity = LIB.get_material_property_input_node(master, u.MaterialProperty.MP_OPACITY_MASK)
                if opacity and opacity.get_editor_property('desc') != 'DenseRiverbankDistanceFade':
                    output = LIB.get_material_property_input_node_output_name(master, u.MaterialProperty.MP_OPACITY_MASK)
                    fade = LIB.create_material_expression(master, u.MaterialExpressionPerInstanceFadeAmount)
                    multiply = LIB.create_material_expression(master, u.MaterialExpressionMultiply)
                    multiply.set_editor_property('desc', 'DenseRiverbankDistanceFade')
                    if not LIB.connect_material_expressions(opacity, output, multiply, 'A'):
                        raise RuntimeError('Could not connect original plant mask')
                    if not LIB.connect_material_expressions(fade, '', multiply, 'B'):
                        raise RuntimeError('Could not connect plant distance fade')
                    if not LIB.connect_material_property(multiply, '', u.MaterialProperty.MP_OPACITY_MASK):
                        raise RuntimeError('Could not connect plant mask output')
                LIB.recompile_material(master)
                masters[parent_path] = save(master)
            master = masters[parent_path]
            mat = copy(original.get_path_name(), DEST + '/MI_RiverDense_' + group + '_' + original.get_name())
            LIB.set_material_instance_parent(mat, master)
            scalars = {str(name) for name in LIB.get_scalar_parameter_names(master)}
            # A fresher, subdued wet-bank palette, retaining the source flowers,
            # seed heads and leaf textures, separate from the dry hill meadow.
            for name, value in {
                    'Brightness': .80 if group == 'cover' else .78,
                    'Saturation': .68 if group == 'bank' else .74,
                    'Subsurface Saturation': .65,
                    'Subsurface Strengh': .50}.items():
                if name in scalars:
                    LIB.set_material_instance_scalar_parameter_value(mat, name, value)
            switches = {str(name) for name in LIB.get_static_switch_parameter_names(master)}
            for level in (1, 2, 3):
                for name, enabled in [('Level %d Bending' % level, False),
                                      ('Level %d Wind' % level, level == 1)]:
                    if name in switches:
                        LIB.set_material_instance_static_switch_parameter_value(mat, name, enabled)
            LIB.update_material_instance(mat)
            materials[key] = save(mat)
        mesh.set_material(index, materials[key])
    save(mesh)
    size = mesh.get_bounding_box().max - mesh.get_bounding_box().min
    REPORT['meshes'].append({'source': path, 'copy': mesh.get_path_name(),
                             'group': group, 'source_size_cm': [size.x, size.y, size.z]})
    return mesh


grass = '/Game/PN_GrassLibrary/Meshes/grassMesh/'
cover = [plant(grass + name, 'cover') for name in (
    'lowGrass_04_03_SM', 'lowGrass_07_02_SM', 'lowGrass_08_02_SM',
    'lowGrass_09_02_SM', 'lowGrass_10_02_SM', 'grass_12_05_mesh')]
reeds = [plant(grass + name, 'reeds') for name in (
    'grass_02_06_mesh', 'grass_02_09_mesh', 'grass_04_03_mesh', 'grass_04_04_mesh')]
banks = [plant(grass + name, 'bank') for name in (
    'grass_03_08_mesh', 'grass_05_07_mesh', 'grass_06_06_mesh',
    'grass_07_04_mesh', 'grass_09_08_mesh', 'grass_10_04_mesh')]
# Small rosettes and lanceolate leaves only, scaled to 32-64 cm by generation.
understory = [plant('/Game/PN_tropicalGroundPlants/Meshes/' + name, 'understory') for name in (
    'tropicalPlant_05_01', 'tropicalPlant_05_02', 'tropicalPlant_04_01', 'tropicalPlant_04_02')]

config_path = BASE + '/DA_TemperateHillsStreaming'
backup(config_path)
assets = load(config_path)
assets.set_editor_property('river_ground_cover', cover)
assets.set_editor_property('river_reeds', reeds)
assets.set_editor_property('river_bank_grasses', banks)
assets.set_editor_property('river_understory', understory)
assets.set_editor_property('river_plant_coverage', .95)
assets.set_editor_property('river_ground_cover_coverage', .96)
assets.set_editor_property('river_ground_cover_spacing_cm', 52.0)
save(assets)
REPORT['configuration'] = assets.get_path_name()
REPORT['reused_shrubs'] = [str(mesh) for mesh in assets.get_editor_property('shrubs')]
REPORT['generation'] = {'ground_cover_spacing_cm': 52, 'ground_cover_probability': .96,
                        'upper_layer_probability': .95, 'model_count': len(REPORT['meshes'])}
(OUT / 'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('TEMPERATE_DENSE_RIVERBANK_AUTHORING_COMPLETE')
