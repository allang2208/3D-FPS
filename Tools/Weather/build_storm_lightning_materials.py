"""Connect the weather manager's continuous flash to existing sky/cloud graphs.

Reusable by cloud/sky authoring scripts. Running this file patches only the
project-owned materials, compiles them and saves them; no game or preview runs.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
MPC = '/Game/Weather/Materials/MPC_FPS_Weather'
CLOUD = '/Game/Weather/Materials/M_FPSLayeredClouds'
HILLS = '/Game/WorldGeneration/TemperateHills/Sky/M_HillsDayNightSky'


def _node(master, cls, desc):
    for n in LIB.get_material_expressions(master):
        if isinstance(n, cls) and n.get_editor_property('desc') == desc:
            return n, False
    n = LIB.create_material_expression(master, cls)
    n.set_editor_property('desc', desc)
    return n, True


def _scalar(master, name, default):
    for n in LIB.get_material_expressions(master):
        if isinstance(n, u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name')) == name:
            return n
    n = LIB.create_material_expression(master, u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', default)
    n.set_editor_property('group', 'FPS Lightning')
    return n


def _flash(master):
    n, _ = _node(master, u.MaterialExpressionCollectionParameter, 'FPS storm lightning driver')
    collection = u.load_asset(MPC)
    if collection is None:
        raise RuntimeError('Weather MPC is missing')
    n.set_editor_property('collection', collection)
    n.set_editor_property('parameter_name', 'WeatherLightning')
    return n


def _custom(master, desc, code, inputs):
    n, fresh = _node(master, u.MaterialExpressionCustom, desc)
    if fresh:
        pins = []
        for name in inputs:
            p = u.CustomInput()
            p.set_editor_property('input_name', name)
            pins.append(p)
        n.set_editor_property('inputs', pins)
    n.set_editor_property('code', code)
    n.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    for name, (source, output) in inputs.items():
        if not LIB.connect_material_expressions(source, output, n, name):
            raise RuntimeError('Cannot connect lightning input ' + name)
    return n


def connect_cloud_lightning(master, extinction=None, density=None):
    extinction = extinction or LIB.get_material_property_input_node(master, u.MaterialProperty.MP_SUBSURFACE_COLOR)
    output = LIB.get_material_property_input_node_output_name(master, u.MaterialProperty.MP_SUBSURFACE_COLOR)
    if extinction is None:
        raise RuntimeError('Cloud has no extinction output')
    density = density or _scalar(master, 'Cloud_GlobalDensity', .008)
    light = _custom(master, 'FPS storm lightning cloud radiance', '''
// Reuse the already evaluated density: no extra volume-texture samples.
// Emission/extinction is bounded, so a deeper cloud cannot accumulate unbounded light.
float3 extinction = max((float3)Extinction, 0.0);
float body = saturate(dot(extinction, float3(.333333,.333333,.333333)) / max(Density,.0001));
float relief = lerp(.92,.52,body);
return extinction * float3(.78,.87,1.0) * saturate(Flash) * max(Energy,0.0) * relief;
''', dict(Extinction=(extinction, output), Density=(density, ''),
          Flash=(_flash(master), ''), Energy=(_scalar(master, 'FPS_LightningCloudLuminance', 1.2), '')))
    if not LIB.connect_material_property(light, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect cloud lightning emission')


def connect_sky_lightning(master):
    desc = 'FPS storm lightning sky radiance'
    existing = [n for n in LIB.get_material_expressions(master)
                if isinstance(n, u.MaterialExpressionCustom) and n.get_editor_property('desc') == desc]
    if existing:
        base = LIB.get_inputs_for_material_expression(master, existing[0])[0]
        output = LIB.get_input_node_output_name_for_material_expression(existing[0], base)
    else:
        base = LIB.get_material_property_input_node(master, u.MaterialProperty.MP_EMISSIVE_COLOR)
        output = LIB.get_material_property_input_node_output_name(master, u.MaterialProperty.MP_EMISSIVE_COLOR)
    if base is None:
        raise RuntimeError('Sky has no emissive output: ' + master.get_path_name())
    light = _custom(master, desc, '''
return Base + float3(.78,.87,1.0) * saturate(Flash) * max(Energy,0.0);
''', dict(Base=(base, output), Flash=(_flash(master), ''),
          Energy=(_scalar(master, 'FPS_LightningSkyLuminance', .35), '')))
    if not LIB.connect_material_property(light, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect sky lightning emission')


def build():
    out = ROOT / 'Saved/StormLightning20260919'
    backup = out / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    out.mkdir(parents=True, exist_ok=True)
    cloud, hills = u.load_asset(CLOUD), u.load_asset(HILLS)
    if cloud is None or hills is None:
        raise RuntimeError('Author the project cloud and hills sky materials first')
    masters = {cloud.get_path_name(): cloud, hills.get_path_name(): hills}
    presentation = u.load_asset('/Game/Weather/RainVisibility/DA_WeatherPresentation')
    if presentation:
        for material in presentation.get_editor_property('sky_materials').values():
            while isinstance(material, u.MaterialInstance):
                material = material.get_editor_property('parent')
            if material and material.get_path_name().startswith('/Game/Weather/'):
                masters[material.get_path_name()] = material
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for path in masters:
        if path.split('.')[0] in dirty:
            raise RuntimeError('Unsaved edits in lightning target: ' + path)
        file = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
        if file.exists():
            dest = backup / file.relative_to(ROOT / 'Content')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
    for material in masters.values():
        if material == cloud:
            connect_cloud_lightning(material)
        else:
            connect_sky_lightning(material)
        LIB.layout_material_expressions(material)
        LIB.recompile_material(material)
    u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
    for material in masters.values():
        if not EAL.save_loaded_asset(material, False):
            raise RuntimeError('Cannot save ' + material.get_path_name())
    report = dict(saved=list(masters), backup=str(backup), parameter='WeatherLightning',
                  cloud_luminance=1.2, sky_luminance=.35,
                  scope='Asset authoring/build only; no runtime or visual testing')
    (out / 'materials-authored.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.log('FPS_STORM_LIGHTNING_MATERIALS_BUILT ' + ', '.join(masters))


if __name__ == '__main__':
    build()
