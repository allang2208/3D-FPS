"""Extend the fireball combustion field to current meteor/flame-armor materials.

Changes only four project-owned RealisticV5 materials. Original pack materials,
Niagara topology, emission counts, native atlas decoding and opacity stay intact.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
from apply_fireball_fluid_core import ensure_texture, input_pin, connect, save

SOURCE = ROOT / 'SourceAssets/FireMagicFluidFields20260923'
DEST = '/Game/Skills/FireMagic20260921/RealisticV5'
LIB = unreal.MaterialEditingLibrary
TAG = 'Fire magic Mantaflow thermal detail'
# Native SubUV grids must remain independent of the shared 8x8 simulation atlas.
PROFILES = {
    'Blade': {'material': 'M_NaturalBladeFlame', 'grid': [8, 4],
              'values': [14.0, 0.11, 0.55, 0.0]},
    'Fire': {'material': 'M_NaturalRollingFlame', 'grid': [6, 6],
             'values': [18.0, 0.37, 0.72, 0.0]},
    'Meteor': {'material': 'M_NaturalMeteorFlame', 'grid': [6, 6],
               'values': [23.0, 0.67, 0.78, 0.0]},
    'Impact': {'material': 'M_NaturalImpact', 'grid': [12, 12],
               'values': [0.0, 0.0, 0.62, 1.0]},
}


def install_on_material(material, kind):
    profile = PROFILES[kind]
    texture = ensure_texture()
    nodes = LIB.get_material_expressions(material)
    detail = next((n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom)
                   and n.get_editor_property('description') == TAG), None)
    if detail is None:
        # Keep EyeAdaptationInverse at the final emission connection so a future
        # RealisticV5 rebuild will not wrap the result in a second compensation.
        exposure = LIB.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if not isinstance(exposure, unreal.MaterialExpressionEyeAdaptationInverse):
            raise RuntimeError('Expected the current exposure-compensated fire material: ' + material.get_path_name())
        inputs = LIB.get_inputs_for_material_expression(material, exposure)
        if not inputs or inputs[0] is None:
            raise RuntimeError('Missing native flame emission in ' + material.get_path_name())
        native = inputs[0]
        detail = LIB.create_material_expression(material, unreal.MaterialExpressionCustom)
        detail.set_editor_property('description', TAG)
        detail.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        detail.set_editor_property('inputs', [input_pin(name) for name in
            ('NativeEmission', 'NativeUV', 'NativeGrid', 'Clock', 'ParticleAge', 'Atlas', 'Profile')])
        uv = LIB.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('coordinate_index', 0)
        clock = LIB.create_material_expression(material, unreal.MaterialExpressionTime)
        age = LIB.create_material_expression(material, unreal.MaterialExpressionParticleRelativeTime)
        atlas = LIB.create_material_expression(material, unreal.MaterialExpressionTextureObject)
        atlas.set_editor_property('texture', texture)
        atlas.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        grid = LIB.create_material_expression(material, unreal.MaterialExpressionConstant2Vector)
        grid.set_editor_property('desc', TAG + ' native grid')
        params = LIB.create_material_expression(material, unreal.MaterialExpressionConstant4Vector)
        params.set_editor_property('desc', TAG + ' profile')
        for name, node in [('NativeEmission', native), ('NativeUV', uv), ('NativeGrid', grid),
                           ('Clock', clock), ('ParticleAge', age), ('Atlas', atlas), ('Profile', params)]:
            connect(node, '', detail, name)
        connect(detail, '', exposure, str(LIB.get_material_expression_input_names(exposure)[0]))
    nodes = LIB.get_material_expressions(material)
    grid = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionConstant2Vector)
                and n.get_editor_property('desc') == TAG + ' native grid')
    grid.set_editor_property('r', profile['grid'][0])
    grid.set_editor_property('g', profile['grid'][1])
    params = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionConstant4Vector)
                  and n.get_editor_property('desc') == TAG + ' profile')
    params.set_editor_property('constant', unreal.LinearColor(*profile['values']))
    detail.set_editor_property('code', (SOURCE / 'CombustionDetail.hlsl').read_text(encoding='utf-8'))
    return texture


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    saved = []
    backups = []
    for kind, profile in PROFILES.items():
        path = DEST + '/' + profile['material']
        material = unreal.load_asset(path)
        if material is None:
            raise RuntimeError('Missing current fire-magic material: ' + path)
        previous = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        backup = SOURCE / 'Before' / previous.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(previous, backup)
        backups.append({'asset': path, 'path': str(backup),
                        'sha256': hashlib.sha256(backup.read_bytes()).hexdigest()})
        texture = install_on_material(material, kind)
        errors = LIB.recompile_material(material)
        if errors:
            raise RuntimeError('Fire magic material compilation failed: ' + str(errors))
        save(material)
        saved.append(material.get_path_name())
    (SOURCE / 'delivery.json').write_text(json.dumps({
        'status': 'materials_updated_compilation_requested_and_saved',
        'materials': saved, 'shared_texture': texture.get_path_name(),
        'profiles': PROFILES, 'backups': backups,
        'systems_using_materials': [DEST + '/' + name for name in (
            'NS_ArmorNaturalFire', 'NS_ArmorNaturalAura', 'NS_MeteorNaturalMantle',
            'NS_MeteorNaturalWake', 'NS_MeteorNaturalImpact', 'NS_MeteorNaturalAfterfire')],
        'particle_count_changed': False, 'opacity_changed': False, 'gameplay_changed': False,
        'additional_lights': 0, 'runtime_volume_simulation': False,
        'new_texture_assets': 0,
        'shader_compile_note': 'Recompile API returned no immediate errors; not a rendered acceptance test',
        'runtime_tested': False, 'visual_tested': False, 'performance_measured': False,
    }, indent=2), encoding='utf-8')
    unreal.log('FIRE_MAGIC_FLUID_FIELDS_INSTALLED materials=4 systems=6')


if __name__ == '__main__':
    main()
