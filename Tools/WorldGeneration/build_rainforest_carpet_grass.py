"""Build the rainforest's three dry-ground grass clumps from the local Project Nature library."""
from pathlib import Path
import runpy
import unreal as u


HILLS = '/Game/WorldGeneration/TemperateHills'
SOURCE = '/Game/PN_GrassLibrary/Meshes/grassMesh'
DEST = HILLS + '/WetForest/CarpetGrass'
DATA = HILLS + '/DA_TemperateHillsStreaming'
# Runtime order: a 22 cm low mat, a wider 42 cm clump, then 55 cm accents in clearings.
FORMS = (('lowGrass_01_02_SM', 'Low'), ('lowGrass_02_02_SM', 'Spreading'),
         ('lowGrass_04_03_SM', 'Tall'))
assets = u.EditorAssetLibrary
materials = u.MaterialEditingLibrary


def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing ' + path)
    return obj


def copy(source, destination):
    if assets.does_asset_exist(destination):
        return load(destination)
    obj = assets.duplicate_asset(source.get_path_name(), destination)
    if not obj:
        raise RuntimeError('Could not duplicate ' + source.get_path_name())
    return obj


def save(obj):
    if not assets.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save ' + obj.get_path_name())


def make_clump(source_name, role):
    source = load(SOURCE + '/' + source_name)
    mesh = copy(source, DEST + '/SM_RainforestGrass' + role)
    box = source.get_bounding_box()
    root_min = box.min + source.get_editor_property('negative_bounds_extension')
    root_max = box.max - source.get_editor_property('positive_bounds_extension')
    for index, slot in enumerate(source.get_editor_property('static_materials')):
        # The matching hills instance already has this clump's Pivot Painter textures,
        # blade wind, distance fade and the hills weather/interaction master.
        template = load(HILLS + '/Grass/MI_Meadow_' + slot.material_interface.get_name())
        mat = copy(template, DEST + '/MI_Rainforest_' + slot.material_interface.get_name())
        for name, value in (('MeadowDryness', 0.), ('MeadowColorVariation', .10),
                            ('Brightness', .94), ('Saturation', .90),
                            ('Subsurface Saturation', .85), ('Subsurface Strengh', .55)):
            materials.set_material_instance_scalar_parameter_value(mat, name, value)
        for name, rgb in (('MeadowDryTint', (.55, 1.03, .32)), ('MeadowOliveTint', (.43, .92, .25))):
            materials.set_material_instance_vector_parameter_value(mat, name, u.LinearColor(*rgb, 1))
        for name, corner in (('GrassRestBoundsMin', root_min), ('GrassRestBoundsMax', root_max)):
            materials.set_material_instance_vector_parameter_value(mat, name, u.LinearColor(corner.x, corner.y, corner.z, 0))
        materials.update_material_instance(mat)
        save(mat)
        mesh.set_material(index, mat)
    save(mesh)
    return mesh


def assign_carpet_grass(data):
    runpy.run_path(str(Path(__file__).with_name('restore_hills_grass_parameters.py')))['restore']()
    assets.make_directory(DEST)
    meshes = [make_clump(name, role) for name, role in FORMS]
    data.set_editor_property('rainforest_carpet_grass', meshes)
    return meshes


if __name__ == '__main__':
    data = load(DATA)
    meshes = assign_carpet_grass(data)
    save(data)
    u.log('Rainforest carpet saved to ' + data.get_path_name() + ' with ' +
          ', '.join(mesh.get_name() for mesh in meshes))
