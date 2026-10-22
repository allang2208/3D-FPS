"""Save Meteor's hold-to-aim decal. No world launch, rendering or gameplay test."""
import json
import re
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[2]
DEST = '/Game/Skills/FireMagic20260921/PreviewSurface20261022'
NAME = 'M_MeteorAimPreview'
PATH = DEST + '/' + NAME
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary


def build():
    if ROOT != Path('D:/FPS3D/FPSGAME').resolve():
        raise RuntimeError('This authoring recipe belongs to FPSGAME')
    if Path(u.Paths.project_content_dir()).resolve() != (ROOT / 'Content').resolve():
        raise RuntimeError('The author host must share FPSGAME Content')
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if PATH in dirty:
        raise RuntimeError('Preserve the unsaved Meteor preview package')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():
            raise RuntimeError('Do not author the preview during PIE')

    source = (ROOT / 'Source/FPSGAME/Skills/FPSMagicPreview.cpp').read_text(encoding='utf-8-sig')
    color = re.search(r'FPSMagicPreview::LineColor\(\)\s*\{\s*return FLinearColor\(([^)]+)\)', source)
    if not color:
        raise RuntimeError('Cannot read the shared magic preview color')
    tint_value = u.LinearColor(*(float(v.strip().rstrip('f')) for v in color.group(1).split(',')))

    EAL.make_directory(DEST)
    material = u.load_asset(PATH) if EAL.does_asset_exist(PATH) else u.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DEST, u.Material, u.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot create the Meteor preview material')
    LIB.delete_all_material_expressions(material)
    material.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)

    def parameter(name, value):
        vector = isinstance(value, u.LinearColor)
        node = LIB.create_material_expression(material, u.MaterialExpressionVectorParameter if vector else u.MaterialExpressionScalarParameter)
        node.set_editor_property('parameter_name', name)
        node.set_editor_property('default_value', value)
        return node, 'RGB' if vector else ''

    def custom(code, inputs, output_type=u.CustomMaterialOutputType.CMOT_FLOAT1):
        node = LIB.create_material_expression(material, u.MaterialExpressionCustom)
        node.set_editor_property('code', code)
        node.set_editor_property('output_type', output_type)
        pins = []
        for name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        node.set_editor_property('inputs', pins)
        for name, (value, channel) in inputs.items():
            if not LIB.connect_material_expressions(value, channel, node, name):
                raise RuntimeError('Cannot connect ' + name)
        return node

    world = LIB.create_material_expression(material, u.MaterialExpressionWorldPosition)
    opacity = custom('''
float3 delta = World - Center;
float height = dot(delta, normalize(SurfaceNormal));
float d = length(delta - normalize(SurfaceNormal) * height);
float width = max(3.0, fwidth(d) * 1.25);
float outer = 1.0 - smoothstep(width, width * 2.0, abs(d - ImpactRadius));
float inner = 1.0 - smoothstep(width * .65, width * 1.5, abs(d - FieldRadius));
float fill = (1.0 - smoothstep(ImpactRadius - width, ImpactRadius, d)) * .035;
float floorBand = 1.0 - smoothstep(90.0, 100.0, abs(height));
return saturate(outer * .92 + inner * .45 + fill) * floorBand;
''', {'World': (world, ''), 'Center': parameter('Center', u.LinearColor(0, 0, 0, 1)),
      'SurfaceNormal': parameter('SurfaceNormal', u.LinearColor(0, 0, 1, 1)),
      'ImpactRadius': parameter('ImpactRadius', 652.5), 'FieldRadius': parameter('FieldRadius', 558.0)})
    tint, channel = parameter('Tint', tint_value)
    emissive = custom('return Tint * 1.5;', {'Tint': (tint, channel)}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    for node, channel, prop in [(opacity, '', u.MaterialProperty.MP_OPACITY),
                                (tint, 'RGB', u.MaterialProperty.MP_BASE_COLOR),
                                (emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR)]:
        if not LIB.connect_material_property(node, channel, prop):
            raise RuntimeError('Cannot connect Meteor preview output')
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError(str(errors))
    if hasattr(u, 'DragonBreathAuthorLibrary') and not u.DragonBreathAuthorLibrary.compile_material_assets([material]):
        raise RuntimeError('Meteor surface preview compilation failed')
    if not EAL.save_loaded_asset(material, False):
        raise RuntimeError('Meteor preview material was not saved')
    receipt = {'complete': True, 'saved_asset': material.get_path_name(),
               'outer_ring': 'FireMagicStats(meteor).Radius',
               'inner_ring': 'FireMagicStats(meteor).AuraRadius',
               'ground_band_cm': 100, 'rendered': False, 'gameplay_tested': False}
    output = ROOT / 'SourceAssets/MeteorFormulaNetAudit20261022'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'asset-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('METEOR_AIM_PREVIEW_SAVED ' + material.get_path_name())


if __name__ == '__main__':
    build()
