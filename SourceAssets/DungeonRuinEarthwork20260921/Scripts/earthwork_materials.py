"""Shared Earthwork graphs. Samplers follow texture storage, not channel intent."""
import unreal as u

L = u.MaterialEditingLibrary


def sampler_for(texture):
    """UE 5.8 MaterialExpressionUtils::GetSamplerTypeForTexture, for these 2D maps."""
    compression = texture.get_editor_property('compression_settings')
    srgb = texture.get_editor_property('srgb')
    kinds = {
        u.TextureCompressionSettings.TC_NORMALMAP: 'NORMAL',
        u.TextureCompressionSettings.TC_MASKS: 'MASKS',
        u.TextureCompressionSettings.TC_ALPHA: 'ALPHA',
        u.TextureCompressionSettings.TC_GRAYSCALE: 'GRAYSCALE' if srgb else 'LINEARGRAYSCALE',
    }
    kind = kinds.get(compression, 'COLOR' if srgb else 'LINEARCOLOR')
    key = 'SAMPLERTYPE' + ('VIRTUAL' if texture.get_editor_property('virtual_texture_streaming') else '') + kind
    return getattr(u.MaterialSamplerType, next(n for n in dir(u.MaterialSamplerType) if n.replace('_', '') == key))


def build_graph(material, name, recipe, recipes):
    paths = dict(recipe['textures'])
    if name in ('Ridge', 'Gravel'):
        paths['contact'] = recipes['Soil']['textures']['base']
    textures = {key: u.load_asset(path) for key, path in paths.items()}
    if any(tex is None for tex in textures.values()):
        raise RuntimeError('Missing source texture for ' + name)
    samplers = {key: sampler_for(tex) for key, tex in textures.items()}
    L.delete_all_material_expressions(material)

    def node(cls):
        return L.create_material_expression(material, cls)

    def wire(a, b, pin='', out=''):
        if not L.connect_material_expressions(a, out, b, pin):
            raise RuntimeError('Cannot connect ' + pin)

    def output(a, prop):
        if not L.connect_material_property(a, '', getattr(u.MaterialProperty, 'MP_' + prop)):
            raise RuntimeError('Cannot connect output ' + prop)

    def scalar(value):
        n = node(u.MaterialExpressionConstant)
        n.r = value
        return n

    def vector(parameter, values):
        n = node(u.MaterialExpressionVectorParameter)
        n.set_editor_property('parameter_name', parameter)
        n.set_editor_property('default_value', u.LinearColor(*values, 1))
        return n

    def multiply(a, b):
        n = node(u.MaterialExpressionMultiply)
        wire(a, n, 'A')
        wire(b, n, 'B')
        return n

    def sample(key, parameter, uv=None):
        n = node(u.MaterialExpressionTextureSampleParameter2D)
        n.set_editor_property('parameter_name', parameter)
        n.set_editor_property('texture', textures[key])
        n.set_editor_property('sampler_type', samplers[key])
        if uv:
            wire(uv, n, 'UVs')
        return n

    base = sample('base', 'BaseColor')
    normal = sample('normal', 'Normal')
    if textures['normal'].get_editor_property('compression_settings') != u.TextureCompressionSettings.TC_NORMALMAP:
        # Packed linear RGB normals have not been decoded by a Normal sampler.
        # Keep the source pack's alpha channel/compression unchanged.
        decoded = node(u.MaterialExpressionSubtract)
        wire(multiply(normal, scalar(2)), decoded, 'A')
        decoded.set_editor_property('const_b', 1.0)
        normal = node(u.MaterialExpressionNormalize)
        wire(decoded, normal)
    color = multiply(base, vector('Tint', recipe['tint']))
    mask = sample('mask', 'SurfaceMasks') if 'mask' in textures else None
    rough = node(u.MaterialExpressionClamp)
    rough.set_editor_property('min_default', recipe['roughness_min'])
    rough.set_editor_property('max_default', recipe['roughness_max'])
    if recipe['roughness_channel'] == 'base_alpha':
        wire(base, rough, out='A')
    else:
        wire(mask, rough, out='G' if recipe['roughness_channel'] == 'orm_green' else 'R')
    if 'contact' in textures:
        uv = node(u.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('coordinate_index', 1)
        soil = sample('contact', 'ContactSoil', uv)
        soil_color = multiply(soil, vector('ContactSoilTint', recipes['Soil']['tint']))
        blend = node(u.MaterialExpressionLinearInterpolate)
        wire(color, blend, 'A')
        wire(soil_color, blend, 'B')
        wire(node(u.MaterialExpressionVertexColor), blend, 'Alpha', 'R')
        color = blend
    output(color, 'BASE_COLOR')
    output(normal, 'NORMAL')
    output(rough, 'ROUGHNESS')
    output(scalar(0), 'METALLIC')
    output(scalar(.24), 'SPECULAR')
    if mask:
        ao = node(u.MaterialExpressionClamp)
        ao.set_editor_property('min_default', .42)
        ao.set_editor_property('max_default', 1)
        wire(mask, ao, out='R' if recipe['roughness_channel'] == 'orm_green' else 'B')
        output(ao, 'AMBIENT_OCCLUSION')
    L.layout_material_expressions(material)
    L.recompile_material(material)
    return {key: str(value) for key, value in samplers.items()}
