"""Create isolated portal materials in the open editor; no level modifications."""
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
ROOT = '/Game/Props/GamedevPortal20260922'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
saved = []

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(asset.get_path_name().split('.')[0])], False):
        raise RuntimeError('Package save failed: ' + asset.get_path_name())
    saved.append(asset.get_path_name())

for name, source in [('Portal_WhiteMarble', 'Altar_WhiteMarble'),
                     ('Portal_PolishedMolding', 'Altar_PolishedMolding'),
                     ('Portal_SatinGold', 'Altar_SatinGold')]:
    path = ROOT+'/Materials/M_'+name
    material = u.load_asset(path)
    if material is None:
        material = E.duplicate_asset('/Game/Props/SquareAltar20260922/Materials/M_'+source, path)
        if material is None:
            raise RuntimeError('Cannot copy the existing shared marble/gold material: '+source)
    E.set_metadata_tag(material, 'Source', 'gamedev portal_model.blend / original portal artwork')
    save(material)

path = ROOT+'/Materials/M_Portal_Energy'
material = u.load_asset(path)
if material is None:
    material = A.create_asset('M_Portal_Energy', ROOT+'/Materials', u.Material, u.MaterialFactoryNew())
if E.get_metadata_tag(material, 'PortalEnergyVersion') != '1':
    L.delete_all_material_expressions(material)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    uv = L.create_material_expression(material, u.MaterialExpressionTextureCoordinate, -500, -150)
    time = L.create_material_expression(material, u.MaterialExpressionTime, -500, 20)
    tint = L.create_material_expression(material, u.MaterialExpressionVectorParameter, -500, 160)
    tint.set_editor_property('parameter_name', 'PortalTint')
    tint.set_editor_property('default_value', u.LinearColor(.035,.42,.48,1))
    strength = L.create_material_expression(material, u.MaterialExpressionScalarParameter, -500, 280)
    strength.set_editor_property('parameter_name', 'GlowStrength')
    strength.set_editor_property('default_value', 3.2)
    energy = L.create_material_expression(material, u.MaterialExpressionCustom, -180, 0)
    energy.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name in ['UV','Time','Tint','Strength']:
        entry = u.CustomInput(); entry.set_editor_property('input_name', name); inputs.append(entry)
    energy.set_editor_property('inputs', inputs)
    energy.set_editor_property('code', '''
float2 p = UV * 2.0 - 1.0;
float slow = Time * 0.35;
float flow = sin(p.y * 7.0 - slow + sin(p.x * 4.0 + slow * 0.7));
float fine = sin(p.y * 22.0 + p.x * 8.0 - Time * 0.8 + flow * 1.4);
float mist = 0.54 + flow * 0.10 + fine * 0.045;
float edge = pow(saturate(abs(p.x)), 4.0) * 0.28;
float pulse = 0.94 + 0.06 * sin(Time * 1.1);
float3 deep = Tint * (0.52 + mist);
float3 pearl = float3(0.14, 0.26, 0.27) * pow(saturate(1.0 - length(p * float2(0.8,0.55))), 2.0);
return (deep + pearl + Tint * edge) * Strength * pulse;
''')
    for node, output, pin in [(uv,'','UV'),(time,'','Time'),(tint,'RGB','Tint'),(strength,'','Strength')]:
        if not L.connect_material_expressions(node, output, energy, pin):
            raise RuntimeError('Energy material connection failed: '+pin)
    if not L.connect_material_property(energy, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Energy emissive connection failed')
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError(str(errors))
    E.set_metadata_tag(material, 'PortalEnergyVersion', '1')
save(material)
(HERE/'materials_receipt.json').write_text(json.dumps({'saved':saved, 'runtime_tested':False}, indent=2), encoding='utf-8')
print('PORTAL_MATERIALS_SAVED '+json.dumps(saved))
