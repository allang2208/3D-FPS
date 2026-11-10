"""Copy the original charge flame structure, recolor, and adapt follow coordinates.

No emitter reconstruction, density changes, opacity thickening, or extra flares.
The original charge system and its blue materials are read-only donors.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
DEST = '/Game/Skills/FlameArmor20261108/SwordRestoreV11'
SYSTEM = DEST+'/NS_FlameArmorSword'
sys.path.insert(0, str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API, LIB, ref, put, setdata, user_parameter, VEC3
from build_fireball_assets import emitters
from flame_expression_compat import nonnegative_random_hashes

spec = importlib.util.spec_from_file_location('original_charge_warm_copy', ROOT/'SourceAssets/FlameArmorSword20261108/install.py')
warm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(warm)
warm.DEST = DEST
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'


def calibrate_warm_tongues(material):
    # The blue donor's 0.12 multiplier was an accent beside its luminous core.
    # Preserve the actual atlas and alpha while giving warm attached fire a
    # readable radiance in daylight. The blue source material is never edited.
    nodes = list(LIB.get_material_expressions(material))
    eye = next(n for n in nodes if isinstance(n, u.MaterialExpressionEyeAdaptationInverse))
    gain = LIB.get_inputs_for_material_expression(material, eye)[0]
    if not isinstance(gain, u.MaterialExpressionMultiply) or LIB.get_inputs_for_material_expression(material, gain)[1] is not None:
        raise RuntimeError('Unexpected warm tongue radiance chain')
    gain.set_editor_property('const_b', 3.0)
    gain.set_editor_property('desc', 'Warm attached flame radiance before exposure 20261109')
    if LIB.recompile_material(material):
        raise RuntimeError('Warm tongue material compilation failed')
    warm.save(material)


def local_expression(value):
    value = nonnegative_random_hashes(value)
    # The copied local-space emitters now receive vectors in the weapon frame.
    # Convert the former world-space birth positions without changing stations,
    # widths, lifetimes, rates, atlas timing, masks, or emitter module structure.
    for name, replacement in (
        ('User.WeaponStartWorld', 'float3(0,0,0)'),
        ('User.WeaponEndWorld', 'User.WeaponEnd'),
        ('User.PreviousStart', 'float3(0,0,0)'),
        ('User.PreviousEnd', 'User.WeaponEnd'),
    ):
        value = value.replace(name, replacement)
    # Preserve physical world-up after the component starts inheriting rotation.
    # The third argument may contain nested calls, so match balanced parentheses.
    cursor = 0
    pattern = re.compile(r'float3\(\s*0(?:\.0*)?\s*,\s*0(?:\.0*)?\s*,')
    while (match := pattern.search(value, cursor)) is not None:
        depth, end = 1, match.end()
        while end < len(value) and depth:
            if value[end] == '(':
                depth += 1
            elif value[end] == ')':
                depth -= 1
            end += 1
        if depth:
            raise RuntimeError('Unbalanced source expression')
        z = value[match.end():end-1].strip()
        if re.fullmatch(r'0(?:\.0*)?', z):
            cursor = end
            continue
        replacement = '(User.FlameUp*('+z+'))'
        value = value[:match.start()]+replacement+value[end:]
        cursor = match.start()+len(replacement)
    return value


def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving the restored warm sword copy')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p == SYSTEM or p.startswith(DEST+'/Materials/') for p in dirty):
        raise RuntimeError('Preserve unsaved restoration assets')
    donor = u.load_asset(warm.DONOR)
    if donor is None:
        raise RuntimeError('Original charge fire asset missing')
    # Duplicate rather than rerun historical authors against the original.
    system = warm.owned(warm.DONOR, SYSTEM)
    user_parameter(system, 'FlameUp', VEC3)
    system.set_editor_property('require_current_frame_data', True)
    system.set_editor_property('fixed_tick_delta', False)
    changes, layers = [], emitters(donor)
    for name in layers:
        data = json.loads(API.call_method('GetRendererData', (ref(donor, name, renderer=0),)).get_editor_property('property_values'))
        material_path = data['Material']
        if isinstance(material_path, dict):
            material_path = material_path['refPath']
        source_material = u.load_asset(material_path)
        if source_material is None:
            raise RuntimeError('Source material missing: '+str(material_path))
        material = warm.warm_material(source_material)
        if name == 'WeaponFireballTongues':
            calibrate_warm_tongues(material)
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0),
                {'Material': material.get_path_name()})
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
                {'bLocalSpace': True, 'bInterpolatedSpawning': False})
        for script in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            modules = API.call_method('GetScriptStackInputValues', (ref(donor, name, script),))
            for module in modules:
                module_name = str(module.get_editor_property('module_name'))
                for entry in module.get_editor_property('inputs'):
                    input_name = str(entry.get_editor_property('name'))
                    value = str(u.RainAssetEditor.read_input(donor, name, script, module_name, input_name))
                    if 'HlslExpression=' not in value:
                        continue
                    local = local_expression(value)
                    if local != value:
                        put(system, name, script, module_name, input_name, local, EXPR)
                        changes.append(dict(emitter=name, script=script, module=module_name, input=input_name))
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Restored sword Niagara compilation failed')
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Revision', 'OriginalChargeWarmFollowV11-20261108')
    warm.save(system)
    (OUT/'restore-receipt.json').write_text(json.dumps(dict(
        revision='OriginalChargeWarmFollowV11', source=warm.DONOR, active_asset=SYSTEM,
        source_revision=u.EditorAssetLibrary.get_metadata_tag(donor, 'StarMarrow.Revision'),
        saved_assets=warm.SAVED, material_copies=warm.MATERIAL_MAP,
        emitter_structure_preserved=layers, coordinate_adaptations=changes,
        opacity_changed=False, spawn_rates_changed=False, particle_sizes_changed=False,
        added_emitters=False, original_blue_assets_modified=False,
        all_layers_local=True, require_current_frame_data=True, fixed_tick_delta=False,
        runtime_tested=False, rendered=False), indent=2), encoding='utf-8')
    print('ORIGINAL_CHARGE_WARM_FOLLOW_SAVED', SYSTEM, layers, 'coordinate_inputs', len(changes))


if __name__ == '__main__':
    run()
