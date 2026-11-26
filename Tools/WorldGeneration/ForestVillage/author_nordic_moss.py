"""Match Nordic Moss to Forest Floor's world-space 2 m tile on the hill terrain."""
import json
import os
import runpy
from pathlib import Path

import unreal as u

surface = runpy.run_path(str(Path(__file__).with_name('author_wild_grass.py')))
ed = u.MaterialEditingLibrary
assets = u.EditorAssetLibrary
load = surface['load']
save = surface['save']
wire = surface['wire']


def create_projection(context):
    path = surface['MOSS_FUNCTION']
    fn = load(path) if assets.does_asset_exist(path) else assets.duplicate_asset(
        '/Game/Landscape/Materials/Functions/MF_Material', path)
    if not fn:
        raise RuntimeError('Cannot create the Nordic Moss material function')
    nodes = ed.get_material_function_expressions(fn)
    # Preserve the artist's A-layer sampling, color, height, normal and cell variation.
    # Only the UV supplied to the near and far tiling nodes changes.
    scales = {}
    for node in nodes:
        if not isinstance(node, u.MaterialExpressionMultiply):
            continue
        pins = surface['inputs'](context, node)
        source = pins.get('B')
        if isinstance(source, u.MaterialExpressionFunctionInput):
            name = str(source.get_editor_property('input_name'))
            if name in ('Size', 'SizeFar'):
                scales[name] = node
    if set(scales) != {'Size', 'SizeFar'}:
        raise RuntimeError('Cannot identify the two Sensei UV scale inputs')
    tag = 'Nordic Moss world XY in metres'
    uv = next((n for n in nodes if n.get_editor_property('desc') == tag), None)
    if not uv:
        make = ed.create_material_expression_in_function
        world = make(fn, u.MaterialExpressionWorldPosition, -2600, 2700)
        xy = make(fn, u.MaterialExpressionComponentMask, -2400, 2700)
        for k in ('r', 'g', 'b', 'a'):
            xy.set_editor_property(k, k in ('r', 'g'))
        wire(world, '', xy, '')
        uv = make(fn, u.MaterialExpressionDivide, -2200, 2700)
        uv.set_editor_property('const_b', 100.0)
        uv.set_editor_property('desc', tag)
        wire(xy, '', uv, 'A')
    for node in scales.values():
        wire(uv, '', node, 'A')
    ed.update_material_function(fn)
    save(fn)


def publish(batch):
    road = surface['ROAD']
    sample = surface['SAMPLE']
    master = load(surface['ROOT']+'/M_ForestPathRoadVerge')
    mats = [master, load(road+'/M_EastRoad_Sensei'), load(sample+'/M_ForestVillageFringe')]
    create_projection(master)
    for mat in mats:
        surface['bind_moss_projection'](mat)
        save(mat)

    palette = load(sample+'/MI_ForestSamplePalette')
    instances = [load(surface['STUDY']), load(road+'/MI_EastRiverRoad'), palette,
                 load(sample+'/MI_ForestVillageFringe')]
    frequency = surface['MOSS_UV_PER_METER']
    for instance in instances:
        ed.set_material_instance_scalar_parameter_value(instance, 'Size A', frequency)
        ed.update_material_instance(instance)
        save(instance)

    # The village core and the gate also consume a copy of the palette with frozen parameters.
    captured = load(sample+'/MF_ForestVillageSurface')
    if not u.ForestVillageRegion.build_surface_function(palette, captured):
        raise RuntimeError('Could not rebuild the village surface from the moss palette')
    surface['connect_sample_verge'](captured)
    ed.update_material_function(captured)
    save(captured)
    mats.extend([load(sample+'/M_ForestVillageSurface'), load(sample+'/M_ForestVillageGateApron')])
    for mat in mats:
        errors = ed.recompile_material(mat)
        if errors:
            raise RuntimeError(mat.get_name()+' '+str(errors))
        ed.get_statistics(mat)
        save(mat)
    receipt = {'world_tile_cm': 100.0 / frequency, 'projection': surface['MOSS_FUNCTION'],
               'instances': [i.get_path_name() for i in instances], 'sample': captured.get_path_name(),
               'materials': [m.get_path_name() for m in mats]}
    (batch/'published.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    publish(Path(os.environ['FPS_MOSS_BATCH']))
