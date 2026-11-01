"""Extend all five existing blade finishes to the UV-isolated native root carrier.

Run after SwordBladeMaterials / Damascus / MeteoricIron material installers.
Preserves their code, Substrate output, wetness, native emission and mode 0.
"""
from pathlib import Path
import json
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
REVISION = 'FullBladeFinish20261101V1'
DEST = '/Game/Weapons/AzureRunesword20260913/BladeFinishes20261031'
NAME = 'T_RuneSword_FullBladeFinishMask'
MASTERS = [
    '/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
    '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold',
]

task = u.AssetImportTask()
for key, value in dict(filename=str(P / (NAME + '.png')), destination_path=DEST,
                       destination_name=NAME, automated=True, replace_existing=True, save=False).items():
    task.set_editor_property(key, value)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = u.load_asset(DEST + '/' + NAME)
if not texture:
    raise RuntimeError('Root coverage texture import failed')
texture.set_editor_property('srgb', False)
texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
if not E.save_loaded_asset(texture, False):
    raise RuntimeError('Root coverage texture was not saved')

def node(mat, cls, **props):
    result = L.create_material_expression(mat, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result

def link(source, output, target, pin):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Material input connection failed: ' + pin)

saved = []
for path in MASTERS:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing active blade material: ' + path)
    if E.get_metadata_tag(material, 'FullBladeFinishRevision') == REVISION:
        saved.append({'path': path, 'already_current': True})
        continue
    source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = P / 'BeforeAssets' / source.relative_to(ROOT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(source, backup)
    finishes = [n for n in L.get_material_expressions(material)
                if isinstance(n, u.MaterialExpressionCustom)
                and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    if len(finishes) != 4:
        raise RuntimeError('Expected the four current PBR finish nodes: ' + path)
    scope = node(material, u.MaterialExpressionScalarParameter,
                 parameter_name='BladeFinishGuardRoot', default_value=0.)
    packed = node(material, u.MaterialExpressionTextureSample, texture=texture,
                  sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    mask = node(material, u.MaterialExpressionCustom, desc=REVISION + ' CoverageAndInk',
                output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,
                code='''float scope=saturate(GuardRoot);
float coverage=lerp(1.0,Packed.b,scope);
float ink=lerp(Packed.r,Packed.g,scope);
// Existing finish shaders use 1-saturate(Mask*3); fold coverage into that input.
return (1.0-coverage*(1.0-saturate(ink*3.0)))/3.0;''')
    pins = []
    for name in ['Packed', 'GuardRoot']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    mask.set_editor_property('inputs', pins)
    link(packed, 'RGB', mask, 'Packed')
    link(scope, '', mask, 'GuardRoot')
    for finish in finishes:
        link(mask, '', finish, 'Mask')
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Full blade material compilation failed: ' + str(errors))
    E.set_metadata_tag(material, 'FullBladeFinishRevision', REVISION)
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Full blade material was not saved: ' + path)
    saved.append({'path': path, 'saved': True, 'finish_nodes': len(finishes)})

(P / 'material-receipt.json').write_text(json.dumps({
    'revision': REVISION, 'texture': texture.get_path_name(), 'materials': saved,
    'finish_modes': [0, 1, 2, 3, 4, 5], 'gameplay_tested': False,
}, indent=2) + '\n', encoding='utf8')
print('FULL_BLADE_MATERIALS_SAVED', json.dumps(saved))
