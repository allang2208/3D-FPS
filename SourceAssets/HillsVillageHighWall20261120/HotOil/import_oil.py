from pathlib import Path
import hashlib
import json
import os
import sys
import unreal as ue

src = Path(__file__).resolve().parent
root = src.parents[2]
os.environ['HIGH_VILLAGE_PROJECT'] = str(root)
sys.path.insert(0, str(root / 'Tools/WorldGeneration/HighVillageDefense'))
sys.path.insert(0, str(root / 'Tools/Fluids'))
import import_kit as kit
from furnace_material_graph import custom, node, prop, scalar, wire

E = ue.EditorAssetLibrary
A = ue.AssetToolsHelpers.get_asset_tools()
L = ue.MaterialEditingLibrary

dest = '/Game/WorldGeneration/TemperateHills/HotOil'
props_dest = dest + '/PropsR2'
tex_dest = props_dest + '/Textures'
tex_src = src / 'PropTextures'


def import_prop_texture(slot, channel):
    fname = tex_src / f'{slot}_{channel}.png'
    name = f'T_{slot}_{channel}'
    path = tex_dest + '/' + name
    digest = hashlib.sha256(fname.read_bytes()).hexdigest()
    old = E.load_asset(path) if E.does_asset_exist(path) else None
    if old and str(E.get_metadata_tag(old, 'VillageSourceSHA')) == digest:
        return old
    task = ue.AssetImportTask()
    task.filename = str(fname)
    task.destination_name = name
    task.destination_path = tex_dest
    task.automated = True
    task.save = False
    task.replace_existing = bool(old)
    A.import_asset_tasks([task])
    tex = kit.require(path)
    tex.set_editor_property('srgb', channel == 'base_color')
    if channel == 'normal':
        tex.set_editor_property('compression_settings', ue.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', True)
    elif channel != 'base_color':
        tex.set_editor_property('compression_settings', ue.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('max_texture_size', 1024)
    E.set_metadata_tag(tex, 'VillageSourceSHA', digest)
    if not E.save_loaded_asset(tex, False):
        raise RuntimeError('Failed saving texture ' + path)
    return tex


def tex_sampler(mat, tex, sampler_type, uv_node, param_name):
    s = node(mat, ue.MaterialExpressionTextureSampleParameter2D)
    s.set_editor_property('parameter_name', param_name)
    s.set_editor_property('texture', tex)
    s.set_editor_property('sampler_type', sampler_type)
    wire((uv_node, ''), s, 'UVs')
    return s


def build_pbr_material(name, slot, has_emissive=False, is_cast_iron=False):
    path = props_dest + '/' + name
    mat = E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name, props_dest, ue.Material, ue.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', ue.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided', False)

    slab = node(mat, ue.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', ue.MaterialShadingModel.MSM_DEFAULT_LIT)
    uv0 = node(mat, ue.MaterialExpressionTextureCoordinate)
    uv0.set_editor_property('coordinate_index', 0)

    def surface(key, pin, expr, out_pin=''):
        src_val = (expr, out_pin) if out_pin else expr
        if not L.connect_material_property(expr, out_pin, getattr(ue.MaterialProperty, 'MP_' + key)):
            raise RuntimeError('Prop link failed: ' + key)
        wire(src_val, slab, pin)

    base_tex = import_prop_texture(slot, 'base_color')
    norm_tex = import_prop_texture(slot, 'normal')
    rough_tex = import_prop_texture(slot, 'roughness')
    metal_tex = import_prop_texture(slot, 'metallic')

    sb = tex_sampler(mat, base_tex, ue.MaterialSamplerType.SAMPLERTYPE_COLOR, uv0, 'BaseColorMap')
    sn = tex_sampler(mat, norm_tex, ue.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv0, 'NormalMap')
    sr = tex_sampler(mat, rough_tex, ue.MaterialSamplerType.SAMPLERTYPE_MASKS, uv0, 'RoughnessMap')
    sm = tex_sampler(mat, metal_tex, ue.MaterialSamplerType.SAMPLERTYPE_MASKS, uv0, 'MetallicMap')

    if is_cast_iron:
        rough_scale = scalar(mat, 'RoughnessScale', 0.88)
        spec_val = scalar(mat, 'SpecularScale', 0.56)
        r_mod = custom(mat, 'return saturate(R * Scale);', {'R': (sr, 'R'), 'Scale': rough_scale}, 1)
        surface('BASE_COLOR', 'BaseColor', sb, 'RGB')
        surface('ROUGHNESS', 'Roughness', r_mod)
        surface('METALLIC', 'Metallic', sm, 'R')
        surface('SPECULAR', 'Specular', spec_val)
        surface('NORMAL', 'Normal', sn, 'RGB')
    else:
        surface('BASE_COLOR', 'BaseColor', sb, 'RGB')
        surface('ROUGHNESS', 'Roughness', sr, 'R')
        surface('METALLIC', 'Metallic', sm, 'R')
        surface('SPECULAR', 'Specular', scalar(mat, 'Specular', 0.52))
        surface('NORMAL', 'Normal', sn, 'RGB')

    if has_emissive:
        em_tex = import_prop_texture(slot, 'emissive')
        se = tex_sampler(mat, em_tex, ue.MaterialSamplerType.SAMPLERTYPE_MASKS, uv0, 'EmissiveMask')
        t = node(mat, ue.MaterialExpressionTime)
        glow_pow = scalar(mat, 'EmberIntensity', 2.8)
        em = custom(
            mat,
            'float pulse = 0.72 + 0.28 * sin(T * 2.6 + UV.x * 11.0 + UV.y * 7.0);'
            'float3 c = lerp(float3(1.0, 0.14, 0.01), float3(1.0, 0.48, 0.06), saturate(Mask * 1.25));'
            'return c * pow(saturate(Mask), 1.35) * pulse * Power;',
            {'Mask': (se, 'R'), 'T': t, 'UV': uv0, 'Power': glow_pow},
            3,
        )
        surface('EMISSIVE_COLOR', 'Emissive Color', em)

    prop(mat, slab, 'FRONT_MATERIAL')
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError(f'{name} compile failed: {errors}')
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Failed saving material ' + path)
    return mat


def make_cast_iron_instance(name, parent, rough_scale):
    path = props_dest + '/' + name
    mic = E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(
        name, props_dest, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew()
    )
    L.set_material_instance_parent(mic, parent)
    L.set_material_instance_scalar_parameter_value(mic, 'RoughnessScale', rough_scale)
    if not E.save_loaded_asset(mic, False):
        raise RuntimeError('Failed saving MIC ' + path)
    return mic


E.make_directory(dest)
E.make_directory(props_dest)
E.make_directory(tex_dest)

hand_only = os.environ.get('VILLAGE_OIL_HAND_POT_ONLY') == '1'
surface_only = os.environ.get('VILLAGE_OIL_SURFACE_ONLY') == '1'

materials = {}
if not surface_only:
    m_iron = build_pbr_material('M_OilCastIron', 'OilCastIron', has_emissive=False, is_cast_iron=True)
    m_brass = build_pbr_material('M_OilAgedBrass', 'OilAgedBrass')
    m_oak = build_pbr_material('M_OilCharredOak', 'OilCharredOak')
    materials['OilAgedBrass'] = m_brass
    materials['OilCharredOak'] = m_oak
    if hand_only:
        materials['OilCastIron'] = make_cast_iron_instance('MI_OilCastIron_HandPot', m_iron, 0.78)
    else:
        materials['OilCastIron'] = make_cast_iron_instance('MI_OilCastIron_Kettle', m_iron, 0.90)
        materials['OilHearthEmbers'] = build_pbr_material('M_OilHearthEmbers', 'OilHearthEmbers', has_emissive=True)
        materials['Footing'] = kit.require('/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFooting')

if not hand_only:
    materials['Bronze'] = kit.require(dest + '/FlowR2/M_OilBody')

if hand_only:
    roles = ('SM_OilHandPot',)
elif surface_only:
    roles = ('SM_OilSurface',)
else:
    roles = ('SM_OilHearth', 'SM_OilHandPot', 'SM_OilSurface')

receipt = {'saved': {}, 'props_r2': props_dest}
out = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())) / 'oil-saved.json'
for role in roles:
    # For SM_OilHandPot we want separate kettle MIC when building all roles cleanly:
    role_mats = dict(materials)
    if role == 'SM_OilHandPot' and not hand_only:
        role_mats['OilCastIron'] = make_cast_iron_instance('MI_OilCastIron_HandPot', m_iron, 0.78)
    kit.create_role(role, role_mats, receipt, package_root=dest, source_dir=src, receipt_file=out, preserve_silhouette=True)

if 'SM_OilSurface' in roles:
    liquid = kit.require(dest + '/SM_OilSurface').get_material(0)
    if not liquid or liquid.get_path_name() != materials['Bronze'].get_path_name():
        raise RuntimeError('Saved oil disc has a different surface')
    receipt['default_liquid'] = liquid.get_path_name()

out.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
