"""Add an integrated runtime clock to the existing cloud noise animation.

Asset authoring only. Keeps the engine Time expression for editor previews and
does not add texture samples, cloud layers or shadow work.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
LIB = u.MaterialEditingLibrary
MATERIAL = '/Game/Weather/Materials/M_FPSLayeredClouds'
MARKER = 'FPS continuous cloud motion clock'


def connect_cloud_motion(master):
    nodes = LIB.get_material_expressions(master)
    if any(n.get_editor_property('desc') == MARKER for n in nodes):
        return
    # The cloud's wind clock is Time / layout-size. The other Time expression
    # belongs to engine lightning, which the weather system already disables.
    divides = []
    for n in nodes:
        if isinstance(n, u.MaterialExpressionDivide):
            inputs = LIB.get_inputs_for_material_expression(master, n)
            if inputs and isinstance(inputs[0], u.MaterialExpressionTime):
                divides.append((n, inputs[0]))
    if len(divides) != 1:
        raise RuntimeError('Cloud wind clock is ambiguous; leave the graph untouched')
    divide, original_time = divides[0]

    def scalar(name, default):
        for n in nodes:
            if isinstance(n, u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name')) == name:
                return n
        n = LIB.create_material_expression(master, u.MaterialExpressionScalarParameter)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', default)
        n.set_editor_property('group', 'FPS Cloud Motion')
        return n

    clock = LIB.create_material_expression(master, u.MaterialExpressionLinearInterpolate)
    clock.set_editor_property('desc', MARKER)
    for source, target, pin in [
        (original_time, clock, 'A'),
        (scalar('FPS_CloudMotionTime', 0.0), clock, 'B'),
        (scalar('FPS_CloudMotionDriven', 0.0), clock, 'Alpha'),
        (clock, divide, 'A'),
    ]:
        if not LIB.connect_material_expressions(source, '', target, pin):
            raise RuntimeError('Cannot connect cloud motion ' + pin)


def build():
    material = u.load_asset(MATERIAL)
    if material is None:
        raise RuntimeError('Project cloud material missing')
    if MATERIAL in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Cloud material has unsaved edits')
    out = ROOT / 'Saved/StormMotion20260919'
    backup = out / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=True)
    file = ROOT / 'Content/Weather/Materials/M_FPSLayeredClouds.uasset'
    shutil.copy2(file, backup / file.name)
    connect_cloud_motion(material)
    LIB.layout_material_expressions(material)
    LIB.recompile_material(material)
    u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
    # Save exactly the authoring package in the editor that owns its loader.
    # This does not save a PIE world or any other dirty editor packages.
    if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()], False):
        raise RuntimeError('Cannot save cloud motion material')
    (out / 'authoring.json').write_text(json.dumps(dict(
        saved=MATERIAL, backup=str(backup), runtime_clock='FPS_CloudMotionTime',
        scope='Material authoring/build only; no runtime or visual test'), indent=2), encoding='utf-8')
    u.log('FPS_CLOUD_MOTION_AUTHORED ' + MATERIAL)


if __name__ == '__main__':
    build()
