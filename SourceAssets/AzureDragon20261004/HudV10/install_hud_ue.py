"""Import/save the Azure Dragon V10 HUD textures and UI material (no PIE, preview or test)."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AzureDragon20261004/HudV10'
TAG, REV = 'AzureDragonHudRevision', '10'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
receipt = dict(complete=False, revision=10, saved_assets=[], runtime_tested=False, rendered=False)


def record():
    (ROOT / 'install-hud-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def owned(path):
    asset = u.load_asset(path) if E.does_asset_exist(path) else None
    dirty = any(str(p.get_name()) == path.rsplit('.', 1)[0] for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty and (not asset or E.get_metadata_tag(asset, 'AzureDragonPending') != REV):
        raise RuntimeError('Preserve unsaved asset ' + path)
    if asset and E.get_metadata_tag(asset, TAG) != REV:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset


def save(asset):
    E.set_metadata_tag(asset, TAG, REV)
    E.set_metadata_tag(asset, 'AzureDragonPending', '')
    E.set_metadata_tag(asset, 'SourceAuthoring', 'AzureDragon20261004/HudV10')
    if not E.save_loaded_asset(asset, False):
        E.set_metadata_tag(asset, 'AzureDragonPending', REV)
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


def import_texture(name, compression, wrap):
    path = DEST + '/Textures/' + name
    owned(path)
    task = u.AssetImportTask()
    for key, value in dict(filename=str(ROOT / 'Export' / (name + '.png')), destination_path=DEST + '/Textures',
                           destination_name=name, automated=True, replace_existing=True, save=False).items():
        task.set_editor_property(key, value)
    A.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError('Import failed ' + name)
    E.set_metadata_tag(tex, TAG, REV)
    E.set_metadata_tag(tex, 'AzureDragonPending', REV)
    address = u.TextureAddress.TA_WRAP if wrap else u.TextureAddress.TA_CLAMP
    for key, value in dict(srgb=False, compression_settings=compression, lod_group=u.TextureGroup.TEXTUREGROUP_UI,
                           mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE, never_stream=True,
                           address_x=address, address_y=address, filter=u.TextureFilter.TF_TRILINEAR).items():
        tex.set_editor_property(key, value)
    save(tex)
    return tex


if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Stop the current PIE before importing/saving HUD V10; editor preserved.')
record()
C = u.TextureCompressionSettings
textures = {
    'EmptyTex': import_texture('T_AzureDragonHudEmpty', C.TC_BC7, False),
    'FullTex': import_texture('T_AzureDragonHudFull', C.TC_BC7, False),
    'MaskTex': import_texture('T_AzureDragonHudMask', C.TC_BC7, False),
    'NoiseTex': import_texture('T_AzureDragonHudNoise', C.TC_VECTOR_DISPLACEMENTMAP, True),
    'GlyphTex': import_texture('T_AzureDragonHudGlyphs', C.TC_GRAYSCALE, True),
}

name = 'M_AzureDragonHudV10'
mat = owned(DEST + '/Materials/' + name) or A.create_asset(name, DEST + '/Materials', u.Material, u.MaterialFactoryNew())
E.set_metadata_tag(mat, TAG, REV)
E.set_metadata_tag(mat, 'AzureDragonPending', REV)
for expression in list(L.get_material_expressions(mat)):
    L.delete_material_expression(mat, expression)
# Translucent (2026-10-06): the additive version read as too see-through over bright scenes.
for key, value in dict(material_domain=u.MaterialDomain.MD_UI, blend_mode=u.BlendMode.BLEND_TRANSLUCENT,
                       shading_model=u.MaterialShadingModel.MSM_UNLIT).items():
    mat.set_editor_property(key, value)
count = 0


def node(cls, **props):
    global count
    n = L.create_material_expression(mat, cls, -1400 + (count % 5) * 260, (count // 5) * 220)
    count += 1
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(source, target, pin):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(target)[pin])
    if not L.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Cannot connect ' + str(pin))


inputs = {'UV': node(u.MaterialExpressionTextureCoordinate)}
for key, value in [('Fill', 0.), ('Age', 0.), ('Pulse', 0.), ('Burst', 0.), ('Reveal', 1.), ('BodyOpacity', .85)]:
    inputs[key] = node(u.MaterialExpressionScalarParameter, parameter_name=key, default_value=value)
for key, tex in textures.items():
    sampler = u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if key == 'GlyphTex' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    inputs[key] = node(u.MaterialExpressionTextureObject, texture=tex, sampler_type=sampler)
code = (ROOT / 'HudLayout.hlsl').read_text(encoding='utf-8') + (ROOT / 'AzureDragonHud.hlsl').read_text(encoding='utf-8')
custom = node(u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
              description='AzureDragonHudV10')
pins = []
for key in inputs:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', key)
    pins.append(pin)
custom.set_editor_property('inputs', pins)
for key, expr in inputs.items():
    wire(expr, custom, key)
rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
wire(custom, rgb, 0)
alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
wire(custom, alpha, 0)
L.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
L.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
errors = L.recompile_material(mat)
if errors:
    raise RuntimeError('HUD material compilation failed ' + str(errors))
save(mat)
receipt['complete'] = True
record()
print('AZURE_DRAGON_HUD_V10_SAVED assets=' + str(len(receipt['saved_assets'])) + ' runtime_tested=false rendered=false')
