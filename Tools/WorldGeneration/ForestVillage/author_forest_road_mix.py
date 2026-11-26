"""Install the exterior B-full road finish into the existing shared road function."""
import json
import os
import re
from pathlib import Path

import unreal as u

REF = '/Game/ForestPathStudy/VillageRegion/Reference'
DEST = REF + '/GateRoad/RoadMix'
LAYERS = {
    'StonyColor': ('DEFAULT', 'COLOR'), 'StonyNormal': ('NORMALMAP', 'NORMAL'),
    'StonyARH': ('MASKS', 'MASKS'), 'TireColor': ('DEFAULT', 'COLOR'),
    'TireNormal': ('NORMALMAP', 'NORMAL'), 'TireARH': ('MASKS', 'MASKS'),
    'RoadMixField': ('VECTOR_DISPLACEMENTMAP', 'LINEAR_COLOR'),
    'TrackFrames': ('VECTOR_DISPLACEMENTMAP', 'LINEAR_COLOR'),
}
ed = u.MaterialEditingLibrary
lib = u.EditorAssetLibrary


def import_maps(source):
    lib.make_directory(DEST)
    for pin, (compression, sampler) in LAYERS.items():
        name = 'T_' + pin
        asset = u.AssetImportTask()
        asset.filename = str(source / (name + '.png'))
        asset.destination_path = DEST
        asset.destination_name = name
        asset.replace_existing = True
        asset.automated = True
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([asset])
        tex = u.load_asset(DEST + '/' + name)
        if not tex:
            raise RuntimeError(name)
        tex.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, 'TC_' + compression))
        tex.set_editor_property('srgb', sampler == 'COLOR')
        mode = u.TextureAddress.TA_WRAP if pin.startswith('Tire') else u.TextureAddress.TA_CLAMP
        for axis in ('address_x', 'address_y'):
            tex.set_editor_property(axis, mode)
        if pin in ('RoadMixField', 'TrackFrames'):
            tex.set_editor_property('compression_no_alpha', False)
            tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            tex.set_editor_property('never_stream', True)
            tex.set_editor_property('filter', u.TextureFilter.TF_NEAREST if pin == 'TrackFrames' else u.TextureFilter.TF_BILINEAR)
        if not lib.save_loaded_asset(tex, False):
            raise RuntimeError('Save failed: ' + tex.get_path_name())


def bind(fn, custom, code):
    inputs = list(custom.get_editor_property('inputs'))
    existing = {str(i.get_editor_property('input_name')) for i in inputs}
    for pin in LAYERS:
        if pin not in existing:
            item = u.CustomInput()
            item.set_editor_property('input_name', pin)
            inputs.append(item)
    custom.set_editor_property('inputs', inputs)
    nodes = {str(n.get_editor_property('desc')): n for n in ed.get_material_function_expressions(fn)}
    for pin, (_, sampler) in LAYERS.items():
        label = 'Exterior road ' + pin
        tex = u.load_asset(DEST + '/T_' + pin)
        if not tex:
            raise RuntimeError('Missing ' + pin)
        expr = nodes.get(label) or ed.create_material_expression_in_function(fn, u.MaterialExpressionTextureObject)
        expr.set_editor_property('desc', label)
        expr.set_editor_property('texture', tex)
        expr.set_editor_property('sampler_type', getattr(u.MaterialSamplerType, 'SAMPLERTYPE_' + sampler))
        if not ed.connect_material_expressions(expr, '', custom, pin):
            raise RuntimeError('Could not connect ' + pin)
    source = (Path(__file__).parent / 'forest_road_mix.ush').read_text(encoding='utf-8-sig')
    pre, blend = source.split('// INSERT AFTER BASE PALETTE')
    for key, anchor, fragment in (('PRE', '[unroll] for(int layer=0;layer<2;++layer)', pre),
                                  ('BLEND', 'float wet=saturate(RainWetness)', blend)):
        begin, end = '// R45_' + key + '_START\n', '// R45_' + key + '_END\n'
        code = re.sub(re.escape(begin) + '.*?' + re.escape(end), '', code, flags=re.S)
        if code.count(anchor) != 1:
            raise RuntimeError('Unexpected road shader anchor ' + anchor)
        code = code.replace(anchor, begin + fragment.strip() + '\n' + end + anchor)
    return code


def install(source, batch):
    import_maps(source)
    fn = u.load_asset(REF + '/MF_TrailDirt')
    custom, = [n for n in ed.get_material_function_expressions(fn)
               if str(n.get_editor_property('desc')) == 'R21 independent soil and moss']
    custom.set_editor_property('code', bind(fn, custom, str(custom.get_editor_property('code'))))
    ed.update_material_function(fn)
    if not lib.save_loaded_asset(fn, False):
        raise RuntimeError('Could not save ' + fn.get_path_name())
    compile_surfaces(batch)
    (batch / 'authored.json').write_text(json.dumps({'function': fn.get_path_name(), 'maps': list(LAYERS)}, indent=2))


def compile_surfaces(batch):
    compiled = {}
    for path in ('/M_ForestReferenceMesh', '/TrailCover/M_ForestVillageLandscape', '/Terrain/MI_ForestTilePacked'):
        material = u.load_asset(REF + path)
        if not material:
            raise RuntimeError(path)
        stats = ed.get_statistics(material)
        compiled[material.get_path_name()] = {
            key: stats.get_editor_property(key) for key in ('num_pixel_shader_instructions', 'num_samplers')
        }
    (batch / 'compiled.json').write_text(json.dumps(compiled, indent=2))


if __name__ == '__main__':
    install(Path(os.environ['FPS_FOREST_REFERENCE_SOURCE']), Path(os.environ['FPS_FOREST_REFERENCE_BATCH']))
