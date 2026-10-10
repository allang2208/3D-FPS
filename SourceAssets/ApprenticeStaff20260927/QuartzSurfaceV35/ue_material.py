"""Surface-first quartz recipe, with separate UI coverage and root clouding.

The existing StaffLightAmount/V32 exposure branch is retained unchanged. This
first candidate deliberately leaves refraction and interior volume for stage 2.
"""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE + '/QuartzSurfaceV35'
WORLD = BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
L = u.MaterialEditingLibrary


def build_quartz_material(rebuild=False, preview=False, candidate=False):
    # V35 still owns geometry. Preserve a successfully installed V36 optical
    # material when the older full-surface installer rebuilds stable paths.
    optics = ROOT.parent / 'QuartzOpticsV36'
    receipt = optics / 'install-receipt.json'
    if not candidate and receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')).get('complete'):
        return runpy.run_path(str(optics / 'ue_material.py'))['build_quartz_material'](rebuild=rebuild, preview=preview)
    path = (DEST + '/Materials/' + ('M_QuartzSurfacePreview_V35' if preview else 'M_QuartzSurface_V35')
            if candidate else PREVIEW if preview else WORLD)
    material = u.load_asset(path)
    if material and not rebuild:
        return material
    if not material:
        folder, name = path.rsplit('/', 1)
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot create quartz surface material ' + path)
    for expression in list(L.get_material_expressions(material)):
        L.delete_material_expression(material, expression)
    index = 0

    def node(cls, **props):
        nonlocal index
        n = L.create_material_expression(material, cls, -1800 + (index % 8) * 220, (index // 8) * 200)
        index += 1
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    def scalar(value):
        return node(u.MaterialExpressionConstant, r=float(value))

    def color(value):
        return node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*value, 1))

    def wire(a, b, pin, output=''):
        if pin == 'Input':
            pin = str(L.get_material_expression_input_names(b)[0])
        if not L.connect_material_expressions(a, output, b, pin):
            raise RuntimeError('Cannot connect quartz ' + pin)

    def output(a, prop, channel=''):
        if not L.connect_material_property(a, channel, prop):
            raise RuntimeError('Cannot connect quartz property ' + str(prop))

    def mul(a, b):
        n = node(u.MaterialExpressionMultiply)
        wire(a, n, 'A')
        wire(b, n, 'B')
        return n

    def add(a, b):
        n = node(u.MaterialExpressionAdd)
        wire(a, n, 'A')
        wire(b, n, 'B')
        return n

    def channel(a, c):
        n = node(u.MaterialExpressionComponentMask, r=c == 'R', g=c == 'G', b=c == 'B', a=False)
        wire(a, n, 'Input')
        return n

    def ramp(a, low, high):
        return add(mul(a, scalar(high - low)), scalar(low))

    def clamp(a, low, high):
        n = node(u.MaterialExpressionClamp, min_default=low, max_default=high)
        wire(a, n, 'Input')
        return n

    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT if preview else u.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
    material.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    material.set_editor_property('two_sided', False)
    if preview:
        material.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    textures = {}
    for suffix, sampler in (('Normal', u.MaterialSamplerType.SAMPLERTYPE_NORMAL), ('Masks', u.MaterialSamplerType.SAMPLERTYPE_MASKS)):
        texture = u.load_asset(DEST + '/Textures/T_QuartzSurface_' + suffix + '_V35')
        if not texture:
            raise RuntimeError('Missing quartz surface texture ' + suffix)
        textures[suffix] = node(u.MaterialExpressionTextureSample, texture=texture, sampler_type=sampler)
    vertex = node(u.MaterialExpressionVertexColor)
    roughness = ramp(channel(vertex, 'R'), P['roughness_min'], P['roughness_max'])
    for signal, amount in ((channel(textures['Masks'], 'R'), P['roughness_growth_add']),
                           (channel(textures['Masks'], 'G'), P['roughness_pit_add']),
                           (channel(vertex, 'G'), P['roughness_bevel_add'])):
        roughness = add(roughness, mul(signal, scalar(amount)))
    output(clamp(roughness, P['roughness_min'], .25), u.MaterialProperty.MP_ROUGHNESS)
    output(textures['Normal'], u.MaterialProperty.MP_NORMAL, 'RGB')
    output(scalar(P['specular']), u.MaterialProperty.MP_SPECULAR)
    output(scalar(0), u.MaterialProperty.MP_METALLIC)
    output(color(P['base_color']), u.MaterialProperty.MP_BASE_COLOR)

    # Root clouding stays a restrained surface signal in stage 1. It never
    # drives roughness: a cloudy patch can still have a polished surface.
    world = node(u.MaterialExpressionWorldPosition)
    local = node(u.MaterialExpressionTransformPosition,
                 transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                 transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(world, local, 'Input')
    z = channel(local, 'B')
    root = clamp(ramp(z, 1 + P['root_z_cm'] / P['root_fade_cm'],
                      1 + (P['root_z_cm'] - 1) / P['root_fade_cm']), 0., 1.)
    root_power = node(u.MaterialExpressionPower, const_exponent=2.)
    wire(root, root_power, 'Base')
    frequency = mul(local, color(P['root_noise_frequency']))
    noise_type = next(getattr(u.NoiseFunction, name) for name in dir(u.NoiseFunction)
                      if 'GRADIENT' in name and 'TEX' in name and '3' in name)
    noise = node(u.MaterialExpressionNoise, scale=1., quality=1, levels=1,
                 noise_function=noise_type, output_min=0., output_max=1.)
    wire(frequency, noise, 'Input')
    sparse = clamp(ramp(noise, -1.4, 2.6), 0., 1.)
    density = mul(root_power, sparse)
    fresnel = node(u.MaterialExpressionFresnel, exponent=P['edge_exponent'], base_reflect_fraction=0.)
    opacity = add(scalar(P['opacity_clear']), mul(fresnel, scalar(P['opacity_edge_add'])))
    opacity = add(opacity, mul(density, scalar(P['opacity_root_add'])))
    output(clamp(opacity, 0., .42), u.MaterialProperty.MP_OPACITY)
    if not preview:
        tint = node(u.MaterialExpressionLinearInterpolate)
        wire(color(P['transmittance_clear']), tint, 'A')
        wire(color(P['transmittance_root']), tint, 'B')
        wire(density, tint, 'Alpha')
        thin = node(u.MaterialExpressionThinTranslucentMaterialOutput)
        wire(tint, thin, 'Input')
        runpy.run_path(str(ROOT.parent / 'CrystalLightV31/material_emission.py'))['add_light_control'](material)
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Quartz material compile failed: ' + str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save quartz material ' + path)
    return material
