"""Keep third-noise detail from suppressing the primary cloud density field.

Edits one project material, compiles and saves its package. No map loads, weather
switches, PIE, screenshots or runtime tests.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
LIB = u.MaterialEditingLibrary
MATERIAL = '/Game/Weather/Materials/M_FPSLayeredClouds'
MARKER = 'FPS bounded detail erosion'


def repair_cloud_density(master):
    nodes = LIB.get_material_expressions(master)
    # Engine UseNoise3 multiplies all primary breakup by MultChannel.a * Noise.
    # The previous .18 alpha was mistakenly used like a blend amount: primary
    # breakup then retained at most 18%, often less than 10%. Preserve at least
    # 82% of the primary field and let detail only erode that bounded fraction.
    combines = [n for n in nodes if isinstance(n, u.MaterialExpressionMultiply)
                and n.get_editor_property('desc') == 'Combine Noise3 MultChannel']
    if len(combines) != 1:
        raise RuntimeError('Cloud primary/detail combine is ambiguous')
    combine = combines[0]
    connected = LIB.get_inputs_for_material_expression(master, combine)
    if len(connected) != 2 or connected[1] is None:
        raise RuntimeError('Cloud primary/detail multiplier is missing')
    old_gain = connected[1]
    if old_gain.get_editor_property('desc') == MARKER:
        erosion = old_gain
    else:
        if not isinstance(old_gain, u.MaterialExpressionMultiply):
            raise RuntimeError('Unexpected cloud detail gain; leave graph unchanged')
        sample = LIB.get_inputs_for_material_expression(master, old_gain)[0]
        sample_output = LIB.get_input_node_output_name_for_material_expression(old_gain, sample)
        erosion = LIB.create_material_expression(master, u.MaterialExpressionCustom)
        erosion.set_editor_property('desc', MARKER)
        pins = []
        for name in ['Noise', 'Strength']:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        erosion.set_editor_property('inputs', pins)
        strength = LIB.create_material_expression(master, u.MaterialExpressionScalarParameter)
        strength.set_editor_property('parameter_name', 'FPS_DetailErosion')
        strength.set_editor_property('default_value', .18)
        strength.set_editor_property('group', 'FPS Cloud Shape')
        for source, output, target, pin in [
            (sample, sample_output, erosion, 'Noise'),
            (strength, '', erosion, 'Strength'),
            (erosion, '', combine, 'B'),
        ]:
            if not LIB.connect_material_expressions(source, output, target, pin):
                raise RuntimeError('Cannot connect bounded cloud erosion: ' + pin)
    erosion.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    erosion.set_editor_property('code', '''
// Detail modifies the primary breakup instead of scaling it almost to zero.
return lerp(float3(1.0, 1.0, 1.0), saturate((float3)Noise), clamp(Strength, 0.0, 0.35));
''')
    # Keep every engine layout channel present; density and coverage, rather
    # than suppression of entire cloud families, own the soft storm profile.
    defaults = {
        'Layout_CloudType': (1.0, 1.0, 1.0, 2.0),
        'Layout_CloudPerTypeScale': (1.0, 1.0, 1.0, 1.0),
    }
    for node in nodes:
        if isinstance(node, u.MaterialExpressionVectorParameter):
            name = str(node.get_editor_property('parameter_name'))
            if name in defaults:
                node.set_editor_property('default_value', u.LinearColor(*defaults[name]))


def build():
    material = u.load_asset(MATERIAL)
    if material is None:
        raise RuntimeError('Project cloud material is missing')
    if MATERIAL in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Cloud material has unsaved edits')
    out = ROOT / 'Saved/CloudVisibilityFix20260919'
    backup = out / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'Content/Weather/Materials/M_FPSLayeredClouds.uasset'
    shutil.copy2(source, backup / source.name)
    repair_cloud_density(material)
    LIB.layout_material_expressions(material)
    LIB.recompile_material(material)
    u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
    if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()], False):
        raise RuntimeError('Could not save repaired cloud material')
    (out / 'authoring.json').write_text(json.dumps(dict(
        saved=MATERIAL, backup=str(backup), detail_erosion=.18,
        retained_primary_gain=[.82, 1.0],
        scope='Material repair and compilation; runtime appearance not tested'), indent=2), encoding='utf-8')
    u.log('FPS_CLOUD_DENSITY_REPAIRED ' + MATERIAL)


if __name__ == '__main__':
    build()
