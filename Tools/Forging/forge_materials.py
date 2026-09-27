"""Rebuildable forge steel, scale sparks, Mantaflow wisps and optical heat veil."""
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
DEST = '/Game/Props/ForgeInteraction20260927'
SOURCE = ROOT / 'SourceAssets/ForgeHeat20260927'
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
from furnace_material_graph import node, wire, prop, custom, scalar


def vector(material, name, value):
    result = node(material, u.MaterialExpressionVectorParameter)
    result.set_editor_property('parameter_name', name)
    result.set_editor_property('default_value', u.LinearColor(*value, 1))
    return result


def surface(material, inputs):
    slab = node(material, u.MaterialExpressionSubstrateShadingModels)
    pins = {'BASE_COLOR': 'BaseColor', 'ROUGHNESS': 'Roughness', 'METALLIC': 'Metallic',
            'EMISSIVE_COLOR': 'Emissive Color', 'NORMAL': 'Normal', 'OPACITY': 'Opacity', 'SPECULAR': 'Specular'}
    for channel, expression in inputs.items():
        wire(expression, slab, pins[channel])
        prop(material, expression, channel)
    prop(material, slab, 'FRONT_MATERIAL')


def instance_data(material, index, default=0):
    value = node(material, u.MaterialExpressionPerInstanceCustomData)
    value.set_editor_property('data_index', index)
    value.set_editor_property('const_default_value', default)
    interpolator = node(material, u.MaterialExpressionVertexInterpolator)
    wire(value, interpolator, str(u.MaterialEditingLibrary.get_material_expression_input_names(interpolator)[0]))
    return interpolator


def fresh_material(name, translucent=False):
    library = u.MaterialEditingLibrary
    material = u.load_asset(DEST + '/' + name)
    if material is None:
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    library.delete_all_material_expressions(material)
    material.set_editor_property('used_with_instanced_static_meshes', True)
    material.set_editor_property('two_sided', translucent)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT if translucent else u.BlendMode.BLEND_OPAQUE)
    if translucent:
        material.set_editor_property('disable_depth_test', False)
        material.set_editor_property('allow_front_layer_translucency', False)
        material.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        material.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    return material


def build_material(name, hot=False):
    material = fresh_material(name)
    material.set_editor_property('two_sided', not hot)
    material.set_editor_property('used_with_instanced_static_meshes', True)
    tint = node(material, u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', u.LinearColor(1, .045, .004, 1) if hot else u.LinearColor(.015, .65, 1, 1))
    heat = scalar(material, 'Heat', 1.2 if hot else 1.4)
    if hot:
        world = node(material, u.MaterialExpressionWorldPosition)
        position = node(material, u.MaterialExpressionTransformPosition)
        position.set_editor_property('transform_source_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
        position.set_editor_property('transform_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(world, position, str(u.MaterialEditingLibrary.get_material_expression_input_names(position)[0]))
        detail = custom(material, (SOURCE / 'SteelSurface.hlsl').read_text(), {'P': position}, 4)
        hit = vector(material, 'ImpactPoint', (0, 0, 0))
        age = scalar(material, 'ImpactAge', 100)
        energy = custom(material, (SOURCE / 'SteelIncandescence.hlsl').read_text(),
                        {'P': position, 'Surface': detail, 'Heat': heat, 'HitPoint': (hit, 'RGB'), 'HitAge': age}, 3)
        base = custom(material, 'return lerp(float3(.082,.071,.058),float3(.016,.019,.022),D.x)*lerp(.8,1.1,D.y);', {'D': detail}, 3)
        roughness = custom(material, 'return lerp(.54,.89,D.x)+.06*(D.y-.5);', {'D': detail})
        metallic = custom(material, 'return lerp(.87,.28,D.x);', {'D': detail})
        normal = custom(material, '''float3 N=normalize(Normal), dx=ddx(World), dy=ddy(World);
float3 a=cross(dy,N), b=cross(N,dx);float det=dot(dx,a);
return normalize(abs(det)*N-sign(det)*(ddx(D.z)*a+ddy(D.z)*b));''',
                        {'World': world, 'Normal': node(material, u.MaterialExpressionVertexNormalWS), 'D': detail}, 3)
        material.set_editor_property('tangent_space_normal', False)
        surface(material, {'BASE_COLOR': base, 'ROUGHNESS': roughness, 'METALLIC': metallic, 'EMISSIVE_COLOR': energy, 'NORMAL': normal})
    else:
        energy = custom(material, 'return Color * Heat * 3.0;', {'Color': (tint, 'RGB'), 'Heat': heat}, 3)
        base = custom(material, 'return Color;', {'Color': (tint, 'RGB')}, 3)
        surface(material, {'BASE_COLOR': base, 'ROUGHNESS': scalar(material, 'Roughness', .76),
                           'METALLIC': scalar(material, 'Metallic', 0), 'EMISSIVE_COLOR': energy})
    return material


def build_sparks():
    sparks = fresh_material('M_ForgeScaleSpark')
    life, scale = instance_data(sparks, 0), instance_data(sparks, 1)
    glow = custom(sparks, 'float h=saturate(Life); return lerp(float3(1,.055,.003),float3(1,.80,.42),pow(h,1.7))*pow(h,1.45)*lerp(55,8,Scale);',
                  {'Life': life, 'Scale': scale}, 3)
    surface(sparks, {'BASE_COLOR': vector(sparks, 'ScaleColor', (.019,.022,.026)),
                     'ROUGHNESS': scalar(sparks, 'Roughness', .8), 'METALLIC': scalar(sparks, 'Metallic', .5), 'EMISSIVE_COLOR': glow})
    return sparks


def build_effects():
    sparks = build_sparks()

    smoke = fresh_material('M_ForgeFume', True)
    uv = node(smoke, u.MaterialExpressionTextureCoordinate)
    atlas = node(smoke, u.MaterialExpressionTextureObjectParameter)
    atlas.set_editor_property('parameter_name', 'DensityAtlas')
    texture = u.load_asset('/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14')
    if not texture: raise RuntimeError('Forge requires the existing Mantaflow smoke atlas')
    atlas.set_editor_property('texture', texture)
    atlas.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    density_source = (ROOT / 'SourceAssets/ImpactSmokeCorrosion20260924/RollingSmoke.hlsl').read_text()
    density = custom(smoke, density_source, {'UV': uv, 'Atlas': atlas, 'Alpha': instance_data(smoke, 0),
                                            'Seed': instance_data(smoke, 1), 'Age': instance_data(smoke, 2)})
    depth = node(smoke, u.MaterialExpressionDepthFade)
    depth.set_editor_property('fade_distance_default', 2.0)
    wire(density, depth, str(u.MaterialEditingLibrary.get_material_expression_input_names(depth)[0]))
    color = custom(smoke, 'return lerp(float3(.13,.115,.10),float3(.52,.55,.57),Steam);', {'Steam': scalar(smoke, 'Steam', 0)}, 3)
    surface(smoke, {'BASE_COLOR': color, 'OPACITY': depth, 'ROUGHNESS': scalar(smoke, 'Roughness', 1), 'SPECULAR': scalar(smoke, 'Specular', 0)})

    veil = fresh_material('M_ForgeHeatVeil', True)
    veil.set_editor_property('refraction_method', u.RefractionMode.RM_INDEX_OF_REFRACTION)
    veil.set_editor_property('refraction_depth_bias', .5)
    uv, time = node(veil, u.MaterialExpressionTextureCoordinate), node(veil, u.MaterialExpressionTime)
    mask = custom(veil, (SOURCE / 'HeatVeil.hlsl').read_text(), {'UV': uv, 'Time': time, 'Heat': scalar(veil, 'Heat', 1)})
    depth = node(veil, u.MaterialExpressionDepthFade);depth.set_editor_property('fade_distance_default', 2.0)
    wire(mask, depth, str(u.MaterialEditingLibrary.get_material_expression_input_names(depth)[0]))
    noise_uv = custom(veil, 'return UV*float2(3.6,1.7)+float2(sin(Time*.7)*.08,-Time*.32);', {'UV': uv, 'Time': time}, 2)
    noise = node(veil, u.MaterialExpressionTextureSample)
    texture = u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A')
    if not texture: raise RuntimeError('Existing melee distortion normal is unavailable')
    noise.set_editor_property('texture', texture);noise.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    wire(noise_uv, noise, 'UVs')
    normal = custom(veil, 'return normalize(float3(N.xy*Mask*.48,1));', {'N': (noise, 'RGB'), 'Mask': depth}, 3)
    pulse = scalar(veil, 'ImpactPulse', 0)
    ior = custom(veil, 'return 1+Mask*(.024+.009*Pulse);', {'Mask': depth, 'Pulse': pulse})
    opacity = custom(veil, 'return Mask*.018;', {'Mask': depth})
    surface(veil, {'BASE_COLOR': vector(veil, 'AirTint', (.04,.025,.01)), 'NORMAL': normal, 'OPACITY': opacity,
                   'ROUGHNESS': scalar(veil, 'Roughness', 1), 'SPECULAR': scalar(veil, 'Specular', 0)})
    prop(veil, ior, 'REFRACTION')
    return [sparks, smoke, veil]
