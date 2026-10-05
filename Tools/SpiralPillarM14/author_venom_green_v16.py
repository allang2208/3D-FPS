"""Recolor and save M14's owned venom materials; no map, render, or gameplay run."""
from pathlib import Path
import json
import shutil
import traceback
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV16'
DEST = '/Game/Monsters/SpiralPillarM14/VenomV09'
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
report = {'complete': False, 'saved': [], 'tested': False, 'rendered': False,
          'source_revision': 'ProductionV16', 'user_testing_pending': True}
(OUT / 'Records').mkdir(parents=True, exist_ok=True)


def record():
    (OUT / 'Records/assets.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def find_custom(material, description):
    return next(n for n in L.get_material_expressions(material)
                if isinstance(n, u.MaterialExpressionCustom)
                and n.get_editor_property('description') == description)


def replace_code(material, label, code):
    expression = find_custom(material, 'M14V10 ' + label)
    expression.set_editor_property('code', code)
    report.setdefault('shader_edits', {})[label] = code


def main():
    paths = [DEST + '/M_M14_Venom' + role for role in ('Body', 'Core', 'Film')]
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(paths):
        raise RuntimeError('Preserve unsaved target material edits: ' + str(dirty.intersection(paths)))
    backup = OUT / 'Before'
    backup.mkdir(parents=True, exist_ok=True)
    for path in paths:
        source = PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        destination = backup / source.name
        if not destination.exists():
            shutil.copy2(source, destination)

    body, core, film = [u.load_asset(path) for path in paths]
    # Preserve the thin wet interface; absorb red/blue more than green.
    replace_code(body, 'Transmission',
                 'float3 sigma=float3(.155,.030,.245)*Strength;'
                 'return exp(-sigma*T*(1-.22*F.w));')
    # More suspended pigment gives a readable silhouette against a bright floor.
    replace_code(core, 'CloudTint',
                 'return lerp(float3(.018,.16,.005),float3(.09,.55,.012),F.z);')
    replace_code(core, 'CloudCoverage',
                 'float patches=smoothstep(.31,.73,F.z);float edge=pow(saturate(1-V),1.5);'
                 'return (.14+.46*patches)*edge*(1-.35*F.w)*saturate(T*.16);')
    replace_code(film, 'FilmTransmission',
                 'return exp(-float3(4.5,.85,7.0)*F.y);')

    # A low green self-lit component makes the core legible in shadow. No light actor.
    expressions = L.get_material_expressions(core)
    glow = next((n for n in expressions if isinstance(n, u.MaterialExpressionCustom)
                 and n.get_editor_property('description') == 'M14V16 GreenVisibility'), None)
    if glow is None:
        glow = L.create_material_expression(core, u.MaterialExpressionCustom)
    glow.set_editor_property('description', 'M14V16 GreenVisibility')
    glow.set_editor_property('desc', 'M14V16 GreenVisibility')
    glow.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    glow_code = 'return float3(.04,.65,.007)*lerp(.50,1.0,saturate(F.z));'
    glow.set_editor_property('code', glow_code)
    pin = u.CustomInput()
    pin.set_editor_property('input_name', 'F')
    glow.set_editor_property('inputs', [pin])
    flow = next(n for n in expressions if isinstance(n, u.MaterialExpressionCustom)
                and n.get_editor_property('description').endswith('LiquidFlow'))
    surface = next(n for n in expressions if isinstance(n, u.MaterialExpressionSubstrateShadingModels)
                   and n.get_editor_property('desc') == 'M14V10 Surface')
    emission_pin = next(str(name) for name in L.get_material_expression_input_names(surface)
                        if str(name).replace(' ', '').lower() == 'emissivecolor')
    if not L.connect_material_expressions(flow, '', glow, 'F'):
        raise RuntimeError('Cannot connect core flow to emission')
    if not L.connect_material_expressions(glow, '', surface, emission_pin):
        raise RuntimeError('Cannot connect Substrate emission')
    if not L.connect_material_property(glow, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect legacy emission')
    report['shader_edits']['GreenVisibility'] = glow_code

    materials = [body, core, film]
    for material in materials:
        errors = L.recompile_material(material)
        if errors:
            raise RuntimeError(str(errors))
    u.PoisonMaggotMonster.compile_material_assets(materials)
    for material in materials:
        if not E.save_loaded_asset(material, False):
            raise RuntimeError('Cannot save ' + material.get_path_name())
        report['saved'].append(material.get_path_name())
        record()
    report.update(complete=True, native_code_changed=False, new_particles=0,
                  new_textures=0, shared_materials_modified=False,
                  gameplay_changed=False, death_changed=False)
    record()
    manifest_path = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004/source_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    manifest['current_revision'] = 'ProductionV16'
    manifest['production_v16'] = {
        'scope': 'M14 venom body/core/contact-film color and visibility',
        'authoring_script': 'Tools/SpiralPillarM14/author_venom_green_v16.py',
        'mesh_revision': 'ProductionV15', 'death_revision': 'ProductionV14',
        'materials': report['saved'], 'ue_saved': True, 'runtime_tested': False,
        'death_changed': False, 'user_testing_pending': True,
        'receipt': 'ProductionV16/Records/assets.json'}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('M14_V16_GREEN_VENOM_SAVED')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        report['error'] = traceback.format_exc()
        record()
        raise
