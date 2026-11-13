"""Private Damascus V2 surface layer, preserving native rune and finish graphs."""
import json
import runpy
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
REV = 'ZhanmadaoDamascus20261111V2'
ART_REV = 'ZhanmadaoDamascusReference20261111V3'
BATCH = P/'ReferenceRefinementV3'
D = '/Game/Weapons/Zhanmadao20261018/Damascus20261111'
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
PROFILES = json.loads((P/'profiles.json').read_text(encoding='utf-8'))
LONGITUDINAL = runpy.run_path(str(P.parent/'DaoLongitudinal20261110/rune_material.py'))
FIELDS = {'BASE_COLOR': ('BaseColor', 3), 'ROUGHNESS': ('Roughness', 1),
          'NORMAL': ('Normal', 3), 'METALLIC': ('Metallic', 1),
          'ANISOTROPY': ('Anisotropy', 1), 'TANGENT': ('Tangent', 3)}


def nodes(material):
    return list(L.get_material_expressions(material))


def node(material, cls, label, **properties):
    value = next((n for n in nodes(material) if str(n.get_editor_property('desc')) == REV+' '+label), None)
    if value is None:
        value = L.create_material_expression(material, cls)
    value.set_editor_properties(dict(desc=REV+' '+label, **properties))
    return value


def wire(source, output, target, pin):
    available = [str(n) for n in L.get_material_expression_input_names(target)]
    normalize = lambda s: s.replace(' ', '').replace('_', '').lower()
    actual = next((n for n in available if normalize(n) == normalize(pin)), pin)
    if pin == 'Input' and len(available) == 1:
        actual = available[0]
    if not L.connect_material_expressions(source, output, target, actual):
        raise RuntimeError('Cannot connect '+str(target)+' '+pin)


def custom(material, label, code, count, inputs):
    value = node(material, u.MaterialExpressionCustom, label, code=code,
                 output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT'+str(count)))
    pins = []
    for name in inputs:
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    value.set_editor_property('inputs', pins)
    for name, (source, channel) in inputs.items():
        wire(source, channel, value, name)
    return value


def parameter(material, name, default):
    value = next((n for n in nodes(material) if isinstance(n, u.MaterialExpressionScalarParameter)
                  and str(n.get_editor_property('parameter_name')) == name), None)
    return value or node(material, u.MaterialExpressionScalarParameter, name,
                         parameter_name=name, default_value=default)


def geometry_code(profile):
    z, center, width, arc = [profile[key] for key in ['z', 'center', 'width', 'arc']]
    slopes = [(b-a)/(d-c) for a, b, c, d in zip(center, center[1:], z, z[1:])]
    smooth_slopes = [slopes[0]] + [(a+b)*.5 for a, b in zip(slopes, slopes[1:])] + [slopes[-1]]
    code = 'float c=0,w=1,a=0,slope=0;\n'
    for i in range(len(z)-1):
        condition = ('if' if i == 0 else 'else if') + ('(true)' if i == len(z)-2 else '(P.z<=%.9f)' % z[i+1])
        code += condition + '''{
float t=(P.z-%.9f)/%.9f;
c=lerp(%.9f,%.9f,t);w=max(lerp(%.9f,%.9f,t),.02);
a=lerp(%.9f,%.9f,t);slope=lerp(%.9f,%.9f,saturate(t));}
''' % (z[i], z[i+1]-z[i], center[i], center[i+1], width[i], width[i+1],
       arc[i], arc[i+1], smooth_slopes[i], smooth_slopes[i+1])
    return code+'return float4(P.x-c,a,.5+(P.x-c)/w,slope);'


def remove_old_damascus(code):
    marker = '// Damascus20261031V1'
    if marker in code:
        start = code.index(marker); opening = code.index('{', start)
        depth, end = 1, opening+1
        while depth:
            depth += (code[end] == '{')-(code[end] == '}'); end += 1
        code = code[:start]+code[end:]
    bypass = '// DamascusV2 native input\nif(Mode>3.5&&Mode<4.5)return Base;\n'
    return code if bypass in code else bypass+code


def apply(material, choice):
    profile = PROFILES[choice]
    texture_path = D+'/Textures/T_Damascus_'+profile['family']+'_Field'
    texture = u.load_asset(texture_path)
    if not texture:
        # The older blade makers run in isolated asset hosts. Stage the new
        # dependency there as part of rebuilding, instead of losing V2 on export.
        task = u.AssetImportTask()
        task.filename = str(P/'Textures'/('Damascus_'+profile['family']+'_Field.png'))
        task.destination_path, task.destination_name = texture_path.rsplit('/', 1)
        task.automated = True; task.save = False; task.factory = u.TextureFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = u.load_asset(texture_path)
        if not texture: raise RuntimeError('Cannot stage Damascus dependency '+texture_path)
        texture.set_editor_properties(dict(srgb=False, compression_settings=u.TextureCompressionSettings.TC_BC7,
            lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON, max_texture_size=4096, never_stream=False,
            address_x=u.TextureAddress.TA_WRAP, address_y=u.TextureAddress.TA_WRAP,
            mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE))
        E.set_metadata_tag(texture, 'ZhanmadaoDamascusRevision', ART_REV)
        if not E.save_loaded_asset(texture, False): raise RuntimeError('Cannot save Damascus dependency')
    # Keep the old finishes, but remove their superseded mode-4 branch rather
    # than computing two Damascus surfaces and mixing their roughness/normals.
    for value in nodes(material):
        desc = str(value.get_editor_property('desc'))
        if isinstance(value, u.MaterialExpressionCustom) and desc.startswith('SharedTwoHandFinish20261101V1 '):
            field = desc.removeprefix('SharedTwoHandFinish20261101V1 ')
            if field in FIELDS:
                value.set_editor_property('code', remove_old_damascus(str(value.get_editor_property('code'))))
    mode = parameter(material, 'BladeFinishMode', 0.)
    seed = parameter(material, 'DamascusSeed', 111120.)
    position = node(material, u.MaterialExpressionPreSkinnedPosition, 'local position')
    normal = node(material, u.MaterialExpressionPreSkinnedNormal, 'local normal')
    geom_vertex = custom(material, 'blade profile', geometry_code(profile), 4, {'P': (position, '')})
    geom = node(material, u.MaterialExpressionVertexInterpolator, 'profile interpolator')
    wire(geom_vertex, '', geom, 'Input')
    n = node(material, u.MaterialExpressionVertexInterpolator, 'normal interpolator')
    wire(normal, '', n, 'Input')
    uv_code = '''uint s=(uint)Seed;
uint h=s*1664525u+1013904223u;float a=float(h&65535u)/65535.;
h=h*1664525u+1013904223u;float b=float(h&65535u)/65535.;
h=h*1664525u+1013904223u;float c=float(h&65535u)/65535.;
float scale=lerp(.92,1.08,c);
float cross=G.x*scale+.10*sin(G.y*.065+a*6.283185);
float offset=OFFSET;
float along=G.y*lerp(.94,1.06,a)+.90*sin(G.y*.047+b*6.283185);
return float2(.5+cross/12.+offset,along/88.+b);
'''.replace('OFFSET', '(a-.5)*.075' if profile['family'] == 'Feather' else 'a')
    uv = custom(material, 'field coordinates', uv_code, 2, {'G': (geom, ''), 'Seed': (seed, '')})
    field = node(material, u.MaterialExpressionTextureSample, 'packed steel field', texture=texture,
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    wire(uv, '', field, 'UVs')
    mask = LONGITUDINAL['decoration_mask'](material, 'zhanmadao/'+choice)
    rune = next((v for v in nodes(material) if isinstance(v, u.MaterialExpressionCustom)
                 and 'RuneTexture' in str(v.get_editor_property('code'))), None)
    if rune is None:
        raise RuntimeError('Preserve the existing native rune graph: '+material.get_path_name())
    steel = custom(material, 'steel response', '''
float face=smoothstep(.30,.85,abs(normalize(N).y));
float edge=smoothstep(.91,.995,abs(G.z*2.-1.))*face;
float ink=1.-.22*saturate(Ink.a);
float layers=(Field.r-.5)*face*ink*(1.-edge*.35);
uint h=(uint)Seed*22695477u+1u;float variation=float(h&65535u)/65535.-.5;
float tone=.340+layers*.460+(Field.a-.5)*.008+variation*.008;
tone=lerp(tone,.46,edge*.45);
float rough=.270-layers*.135+(Field.a-.5)*.014+variation*.010;
rough=lerp(.325,rough,face);rough=lerp(rough,.155,edge);
float aniso=lerp(.05,.13+(Field.a-.5)*.025,face)*(1.-edge*.30);
return float4(tone,rough,aniso,1.-saturate(Mask*3.));
''', 4, {'Field': (field, 'RGBA'), 'N': (n, ''), 'G': (geom, ''),
        'Ink': (rune, ''), 'Mask': (mask, ''), 'Seed': (seed, '')})
    delta = custom(material, 'etch gradient', '''
float3 along=normalize(float3(G.w,0,1)), across=normalize(float3(1,0,-G.w));
float2 slope=(Field.gb-.5)*.05;
float face=smoothstep(.30,.85,abs(normalize(N).y));
float edge=smoothstep(.91,.995,abs(G.z*2.-1.));
float3 d=-(across*slope.x+along*slope.y)*face*(1.-edge*.60);
return d-N*dot(d,N);
''', 3, {'Field': (field, 'RGBA'), 'N': (n, ''), 'G': (geom, '')})
    brush = custom(material, 'polish direction', '''
float3 v=float3(G.w,0,1);return normalize(v-N*dot(v,N)+float3(.00001,0,0));
''', 3, {'N': (n, ''), 'G': (geom, '')})
    tangent_space = bool(material.get_editor_property('tangent_space_normal'))
    transformed = []
    for label, value in [('normal delta space', delta), ('polish direction space', brush)]:
        transform = node(material, u.MaterialExpressionTransform, label,
            transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
            transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT if tangent_space else u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        wire(value, '', transform, 'Input'); transformed.append(transform)
    codes = {
        'BASE_COLOR': 'return lerp(Base,float3(.985,1.,1.018)*Steel.x,Steel.w);',
        'ROUGHNESS': 'return lerp(Base,Steel.y,Steel.w);',
        'NORMAL': 'return normalize(lerp(Base,normalize(Base+Detail),Steel.w));',
        'METALLIC': 'return lerp(Base,1.,Steel.w);',
        'ANISOTROPY': 'return lerp(Base,Steel.z,Steel.w);',
        'TANGENT': 'return normalize(lerp(Base,Brush,Steel.w));'}
    for name, (pin, channels) in FIELDS.items():
        prop = getattr(u.MaterialProperty, 'MP_'+name)
        source = L.get_material_property_input_node(material, prop)
        output = str(L.get_material_property_input_node_output_name(material, prop)) if source else ''
        owned = next((v for v in nodes(material) if str(v.get_editor_property('desc')) == REV+' '+name), None)
        # Updating an installed recipe keeps its original upstream input.
        has_rune_edge = source and str(source.get_editor_property('desc')).startswith('ZhanmadaoRuneEdgeV1 ')
        if owned is not None and (source == owned or has_rune_edge):
            for input_name, upstream in zip(L.get_material_expression_input_names(owned), L.get_inputs_for_material_expression(material, owned)):
                if str(input_name) == 'Base' and upstream:
                    source = upstream; output = str(L.get_input_node_output_name_for_material_expression(owned, upstream)); break
        if not source:
            if name == 'ANISOTROPY':
                source = node(material, u.MaterialExpressionConstant, 'native anisotropy', r=0.)
            elif name == 'TANGENT':
                source = node(material, u.MaterialExpressionConstant3Vector, 'native tangent', constant=u.LinearColor(1,0,0,1)) if tangent_space else node(material, u.MaterialExpressionVertexTangentWS, 'native tangent')
            else:
                raise RuntimeError('Missing native '+name+' '+material.get_path_name())
        inputs = {'Base': (source, output), 'Mode': (mode, ''), 'Steel': (steel, '')}
        if name == 'NORMAL': inputs['Detail'] = (transformed[0], '')
        if name == 'TANGENT': inputs['Brush'] = (transformed[1], '')
        value = custom(material, name, 'if(Mode<3.5||Mode>4.5)return Base;\n'+codes[name], channels, inputs)
        if not L.connect_material_property(value, '', prop):
            raise RuntimeError('Cannot connect surface '+name)
    slab = L.get_material_property_input_node(material, u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(slab, u.MaterialExpressionSubstrateShadingModels):
        raise RuntimeError('Preserve unexpected Substrate layout '+material.get_path_name())
    for name, (pin, _) in FIELDS.items():
        source = L.get_material_property_input_node(material, getattr(u.MaterialProperty, 'MP_'+name))
        wire(source, '', slab, pin)
    E.set_metadata_tag(material, 'ZhanmadaoDamascusRevision', ART_REV)
    E.set_metadata_tag(material, 'ZhanmadaoDamascusProfile', choice+'/'+profile['family'])
    if choice not in ('chixiao', 'zhufeng'):
        edge_recipe = P.parent/'Zhanmadao20261018/LegendaryRunesV1/edge_material.py'
        runpy.run_path(str(edge_recipe))['apply'](material, profile)
    return True


def apply_if_installed(material):
    receipt = P/'material-receipt.json'
    if not receipt.exists() or not json.loads(receipt.read_text(encoding='utf-8')).get('complete'):
        return False
    prefix = 'M_TangDaoBladeRuneSurface_Zhanmadao_'
    name = material.get_name().removesuffix('_Whirlwind')
    if name.startswith(prefix):
        suffix = name.removeprefix(prefix)
        for choice in PROFILES:
            if suffix.startswith(choice+'_'):
                return apply(material, choice)
    return False
