"""Import the user-downloaded Quixel scan and author the ward Substrate decal."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / 'BloodScan20260929'
SOURCE = SCAN / 'Source/blood_stain_sgfjdepc_8k__extracted/Textures'
CFG = json.loads((ROOT / 'Config/room.json').read_text(encoding='utf-8'))
BASE = CFG['ue_base'] + '/BloodScan'
MATERIAL = CFG['blood_scatter']['material']
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Wrong project')
if editor and editor.get_game_world():
    raise RuntimeError('Preserve active PIE; scan import pending')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(BASE) or p == MATERIAL for p in dirty):
    raise RuntimeError('Preserve unsaved scan assets')

textures = {}
for suffix, name, srgb, compression in (
    ('B-O', 'T_WardBlood_BaseOpacity', True, u.TextureCompressionSettings.TC_BC7),
    ('N', 'T_WardBlood_Normal', False, u.TextureCompressionSettings.TC_NORMALMAP),
    ('ORM', 'T_WardBlood_ORM', False, u.TextureCompressionSettings.TC_MASKS),
):
    path = BASE + '/Textures/' + name
    texture = u.load_asset(path) if E.does_asset_exist(path) else None
    if not texture:
        task = u.AssetImportTask()
        task.set_editor_property('filename', str(SOURCE / ('T_sgfjdepc_8K_' + suffix + '.png')))
        task.set_editor_property('destination_path', BASE + '/Textures')
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', False)
        task.set_editor_property('factory', u.TextureFactory())
        A.import_asset_tasks([task])
        texture = u.load_asset(path)
    if not texture:
        raise RuntimeError('Texture import failed: ' + path)
    texture.modify()
    texture.set_editor_property('srgb', srgb)
    texture.set_editor_property('compression_settings', compression)
    texture.set_editor_property('max_texture_size', 2048)
    texture.set_editor_property('virtual_texture_streaming', False)
    texture.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
    # The downloaded glTF normal is OpenGL (+Y); UE requires DirectX (-Y).
    if suffix == 'N':
        texture.set_editor_property('flip_green_channel', True)
    if not E.save_loaded_asset(texture, False):
        raise RuntimeError('Texture save failed: ' + path)
    textures[suffix] = texture

folder, name = MATERIAL.rsplit('/', 1)
m = u.load_asset(MATERIAL) if E.does_asset_exist(MATERIAL) else A.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
m.modify()
L.delete_all_material_expressions(m)
m.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)

def node(kind, **props):
    n = L.create_material_expression(m, getattr(u, 'MaterialExpression' + kind))
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n

def wire(src, dst, pin):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, out, dst, pin):
        raise RuntimeError('Cannot connect ' + pin)

def custom(code, inputs, width=1):
    n = node('Custom', code=code, output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for key in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', key)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for key, value in inputs.items():
        wire(value, n, key)
    return n

uv = node('TextureCoordinate')
samples = {}
for key, sampler in (('B-O', u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                     ('N', u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
                     ('ORM', u.MaterialSamplerType.SAMPLERTYPE_MASKS)):
    s = node('TextureSample', texture=textures[key], sampler_type=sampler)
    wire(uv, s, 'UVs')
    samples[key] = s
seed = (node('DecalColor'), 'R')
color = custom('return Color * float3(0.92, 0.78, 0.78) * lerp(0.85, 1.0, Seed);',
               {'Color': (samples['B-O'], 'RGB'), 'Seed': seed}, 3)
alpha = custom('return saturate(Alpha) * 0.98;', {'Alpha': (samples['B-O'], 'A')})
rough = custom('return clamp(Roughness * 0.8 + 0.12 + Seed * 0.07, 0.2, 0.88);',
               {'Roughness': (samples['ORM'], 'G'), 'Seed': seed})
normal = custom('return normalize(float3(N.xy * 0.4, N.z));', {'N': (samples['N'], 'RGB')}, 3)
specular = node('Constant', r=0.3)
metallic = node('Constant', r=0.0)
slab = node('SubstrateShadingModels', shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for value, pin, prop in ((color, 'BaseColor', 'BASE_COLOR'), (rough, 'Roughness', 'ROUGHNESS'),
                         (alpha, 'Opacity', 'OPACITY'), (normal, 'Normal', 'NORMAL'),
                         (specular, 'Specular', 'SPECULAR'), (metallic, 'Metallic', 'METALLIC')):
    wire(value, slab, pin)
    L.connect_material_property(value, '', getattr(u.MaterialProperty, 'MP_' + prop))
convert = node('SubstrateConvertToDecal')
wire(slab, convert, str(L.get_material_expression_input_names(convert)[0]))
wire(alpha, convert, 'Coverage')
if not L.connect_material_property(convert, '', u.MaterialProperty.MP_FRONT_MATERIAL):
    raise RuntimeError('Cannot connect scanned blood Substrate decal')
errors = L.recompile_material(m)
if errors:
    raise RuntimeError('Scanned blood material compilation failed: ' + str(errors))
L.layout_material_expressions(m)
if not E.save_loaded_asset(m, False):
    raise RuntimeError('Scanned blood material save failed')
receipt = dict(stage='scanned_blood_textures_and_material_saved', material=MATERIAL,
               textures={k: v.get_path_name() for k, v in textures.items()},
               source_resolution=8192, runtime_max_resolution=2048,
               source_scan_size_cm=25, normal_green_flipped=True,
               source_url='https://www.fab.com/listings/765d43e1-45ef-42f2-80a5-43d6214aa1d3',
               tests_run=False, rendered=False)
(SCAN / 'Receipts/material.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('WARD_SCANNED_BLOOD_MATERIAL_SAVED', json.dumps(receipt), flush=True)
