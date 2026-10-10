"""V41 polished facets; retained V36 finite optical thickness and UI alpha.

The optical chord is a bounded mesh-derived approximation. No screen distortion,
internal cards, volume textures, additional lights, or runtime CPU updates.
"""
import json

from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE + '/QuartzPolishV41'
WORLD = BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
L = u.MaterialEditingLibrary


def build_quartz_material(rebuild=False, preview=False, candidate=False):
    path = ((DEST + '/Materials/' + ('M_QuartzPolishPreview_V41' if preview else 'M_QuartzPolish_V41'))
            if candidate else PREVIEW if preview else WORLD)
    material = u.load_asset(path)
    if material and not rebuild:
        return material
    if not material:
        folder, name = path.rsplit('/', 1)
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot create quartz ' + path)
    # Leave the legacy ThinTranslucent shading mode while its output still
    # exists, before clearing the graph. Property edits can compile immediately.
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for expression in list(L.get_material_expressions(material)):
        L.delete_material_expression(material, expression)
    index = 0

    def node(cls, **props):
        nonlocal index
        result = L.create_material_expression(material, cls, -2000 + (index % 8)*230, (index//8)*210)
        index += 1
        for key, value in props.items():
            result.set_editor_property(key, value)
        return result

    def wire(source, target, pin, output=''):
        names = [str(n) for n in L.get_material_expression_input_names(target)]
        normal = lambda s: s.replace(' ', '').replace('_', '').lower()
        actual = next((n for n in names if normal(n) == normal(pin)), None)
        if actual is None and pin == 'Input' and len(names) == 1:
            actual = names[0]
        if actual is None or not L.connect_material_expressions(source, output, target, actual):
            raise RuntimeError('Quartz cannot wire ' + pin + ' on ' + str(target) + ': ' + repr(names))

    def output(source, prop, channel=''):
        if not L.connect_material_property(source, channel, getattr(u.MaterialProperty, 'MP_' + prop)):
            raise RuntimeError('Quartz cannot wire property ' + prop)

    def scalar(value):
        return node(u.MaterialExpressionConstant, r=float(value))

    def color(value):
        return node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*value, 1.))

    def parameter(name, value):
        return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(value))

    def vector_parameter(name, value):
        return node(u.MaterialExpressionVectorParameter, parameter_name=name, default_value=u.LinearColor(*value, 1.))

    def custom(label, code, inputs, width=1):
        result = node(u.MaterialExpressionCustom, description=label, code=code,
                      output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
        pins = []
        for name in inputs:
            item = u.CustomInput()
            item.set_editor_property('input_name', name)
            pins.append(item)
        result.set_editor_property('inputs', pins)
        for name, source in inputs.items():
            wire(source, result, name)
        return result

    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT if preview
                                 else u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
    material.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    material.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    material.set_editor_property('two_sided', False)
    material.set_editor_property('is_thin_surface', False)
    material.set_editor_property('refraction_method', u.RefractionMode.RM_NONE)
    # Existing deferred forward-lit translucency blends local captures. Enable
    # material-local SSR for gameplay and sky transitions; do not raise global
    # Lumen settings. Intermittent UI captures keep their studio reflections.
    material.set_editor_property('screen_space_reflections', P['preview_screen_space_reflections'] if preview else P['world_screen_space_reflections'])
    material.set_editor_property('forward_blends_sky_light_cubemaps', P['forward_blends_sky_light_cubemaps'])
    material.set_editor_property('allow_front_layer_translucency', True)

    world = node(u.MaterialExpressionWorldPosition)
    camera = node(u.MaterialExpressionCameraPositionWS)
    def to_local(source):
        result = node(u.MaterialExpressionTransformPosition,
                      transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                      transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(source, result, 'Input')
        return result
    local = to_local(world)
    local_camera = to_local(camera)
    geometric_normal = node(u.MaterialExpressionVertexNormalWS)
    local_normal = node(u.MaterialExpressionTransform,
                        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    wire(geometric_normal, local_normal, 'Input')
    ior = parameter('QuartzIOR', P['ior'])
    chord = custom('V36 finite crystal optical chord (cm)', (ROOT/'OpticalChord.hlsl').read_text(encoding='utf-8'),
                   dict(PositionLocal=local, CameraLocal=local_camera, NormalLocal=local_normal, IOR=ior), 3)
    extinction = vector_parameter('QuartzExtinctionPerCm', P['extinction_per_cm'])
    density = parameter('QuartzDensity', 1.)
    root_density = parameter('QuartzRootDensityAdd', P['root_density_add'])
    transmission = custom('V36 normal-incidence transmission',
        'return exp(-max(Extinction.rgb,0.0001)*max(Density,0.001)*Chord.x*(1+RootDensity*Chord.z));',
        dict(Extinction=extinction, Density=density, Chord=chord, RootDensity=root_density), 3)
    view_transmission = custom('V36 finite view transmission',
        'return exp(-max(Extinction.rgb,0.0001)*max(Density,0.001)*Chord.y*(1+RootDensity*Chord.z));',
        dict(Extinction=extinction, Density=density, Chord=chord, RootDensity=root_density), 3)

    vertex = node(u.MaterialExpressionVertexColor)
    roughness = custom('V41 coherent polished planes and narrow bevel highlights',
        'float face=saturate((Facet.r-0.15)/0.70);'
        'float polished=lerp(FacetMin,FacetMax,face);'
        'return clamp(lerp(polished,Bevel,saturate(Facet.g)),0.04,0.20);',
        dict(Facet=vertex, FacetMin=parameter('QuartzFacetRoughnessMin', P['roughness_min']),
             FacetMax=parameter('QuartzFacetRoughnessMax', P['roughness_max']),
             Bevel=parameter('QuartzBevelRoughness', P['bevel_roughness'])))
    # Use the existing flat large facets and smooth sub-mm bevels. No worn
    # tangent-space normal offsets, painted highlights, or fake glow.
    normal = color((0.,0.,1.))
    albedo = vector_parameter('QuartzMediumAlbedo', P['medium_albedo'])
    f0 = custom('V36 dielectric F0 from IOR', 'float x=(IOR-1)/(IOR+1);return x*x;', dict(IOR=ior))

    # Keep the existing runtime-only G switch and V32 exposure correction.
    # Absorption localizes the glow; it is zero everywhere with the switch off.
    amount = parameter('StaffLightAmount', 0.)
    exposure_inverse = node(u.MaterialExpressionEyeAdaptationInverse, desc='StaffLightExposureV32')
    emissive = custom('V36 localized lamp emission',
        'float absorbed=1-dot(Transmission.rgb,float3(.2126,.7152,.0722));'
        'float core=pow(saturate(absorbed),1.5)*(1-.32*Chord.z);'
        'return LightColor.rgb*Amount*ExposureInverse*Gain*core;',
        dict(Transmission=view_transmission, Chord=chord, LightColor=color(P['light_color']),
             Amount=amount, ExposureInverse=exposure_inverse, Gain=parameter('QuartzLampSurfaceGain',P['light_surface_gain'])), 3)

    if preview:
        # HDR inverse-coverage captures require ordinary alpha, not dual source.
        # Use the same extinction/chord/facet recipe; alpha is a capture adapter.
        facing = node(u.MaterialExpressionFresnel, exponent=5., base_reflect_fraction=0.)
        wire(geometric_normal, facing, 'Normal')
        alpha = custom('V36 UI absorption coverage',
            'float F=lerp(F0,1.0,Facing);return saturate(1-dot(T.rgb,float3(.2126,.7152,.0722))*(1-F));',
            dict(F0=f0, Facing=facing, T=view_transmission))
        output(alpha, 'OPACITY')
        output(albedo, 'BASE_COLOR', 'RGB')
        output(scalar(0), 'METALLIC')
        output(custom('V36 preview specular','return F0/.08;',dict(F0=f0)), 'SPECULAR')
        output(roughness, 'ROUGHNESS')
        output(normal, 'NORMAL')
        output(emissive, 'EMISSIVE_COLOR')
    else:
        slab = node(u.MaterialExpressionSubstrateSlabBSDF)
        simple = next(getattr(u.MaterialSubSurfaceType, n) for n in dir(u.MaterialSubSurfaceType)
                      if 'SIMPLE' in n and 'VOLUME' in n)
        slab.set_editor_property('sub_surface_type', simple)
        mfp = node(u.MaterialExpressionSubstrateTransmittanceToMFP)
        wire(transmission, mfp, 'TransmittanceColor')
        # Bottom slab uses UE's default 0.01 cm normalization. Actual cm chord
        # already determines Transmission above; don't multiply thickness twice.
        wire(scalar(.01), mfp, 'Thickness')
        wire(mfp, slab, 'SSS MFP', 'MFP')
        wire(albedo, slab, 'Diffuse Albedo', 'RGB')
        wire(f0, slab, 'F0')
        wire(scalar(1), slab, 'F90')
        wire(roughness, slab, 'Roughness')
        wire(normal, slab, 'Normal')
        wire(emissive, slab, 'Emissive Color')
        output(slab, 'FRONT_MATERIAL')
        output(scalar(1), 'OPACITY')
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Quartz V41 compile failed ' + path + ': ' + str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save quartz ' + path)
    return material
