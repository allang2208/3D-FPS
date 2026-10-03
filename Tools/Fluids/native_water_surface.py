"""Install the accepted Clearwater optics on the three existing water masters.

Only named nodes owned by this layer are updated. Existing geometry, authored fountain
displacement, puddle drips, and the shared hit/wake node remain available on reruns.
No map loading, gameplay, capture or tests. Asset authoring and compilation only.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/NativeWaterAll20260926'
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
PREFIX = 'NativeWater20260926.'
TARGETS = {
    '/Game/Fluids/RiverPilot20260923/M_RiverPilot': 'river',
    '/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3': 'fountain',
    '/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle': 'puddle',
}
ATLAS = '/Game/Clearwater/T_ClearwaterCausticsAtlas'


def apply_native_water(mat, profile):
    nodes = list(L.get_material_expressions(mat))

    def node(cls, key):
        tag = PREFIX + key
        existing = next((n for n in nodes if str(n.get_editor_property('desc')) == tag), None)
        if existing:
            if not isinstance(existing, cls):
                raise RuntimeError('Unexpected native water node type: ' + tag)
            return existing
        n = L.create_material_expression(mat, cls)
        n.set_editor_property('desc', tag)
        nodes.append(n)
        return n

    def wire(source, target, pin):
        n, output = source if isinstance(source, tuple) else (source, '')
        if not L.connect_material_expressions(n, output, target, pin):
            raise RuntimeError('Cannot connect native water input: ' + pin)

    def prop(source, name):
        n, output = source if isinstance(source, tuple) else (source, '')
        if not L.connect_material_property(n, output, getattr(u.MaterialProperty, 'MP_' + name)):
            raise RuntimeError('Cannot connect native water property: ' + name)

    def scalar(name, default):
        n = node(u.MaterialExpressionScalarParameter, name)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', default)
        return n

    def vector(name, default):
        n = node(u.MaterialExpressionVectorParameter, name)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', u.LinearColor(*default))
        return n

    def custom(key, code, inputs, count=1, existing=None):
        n = existing or node(u.MaterialExpressionCustom, key)
        n.set_editor_property('code', code)
        n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(count)))
        pins = []
        for name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        n.set_editor_property('inputs', pins)
        for name, source in inputs.items():
            wire(source, n, name)
        return n

    river, puddle = profile == 'river', profile == 'puddle'
    # Preserve the original static-water normal under a named anchor. Unwrap the old
    # hit overlay once, since the same shared field is combined below.
    anchor = next((n for n in nodes if str(n.get_editor_property('desc')) == PREFIX + 'AuthoredNormal'), None)
    if not river and not anchor:
        baseline = L.get_material_property_input_node(mat, u.MaterialProperty.MP_NORMAL)
        if not baseline:
            raise RuntimeError('Missing authored static-water normal: ' + mat.get_path_name())
        names = list(L.get_material_expression_input_names(baseline))
        sources = list(L.get_inputs_for_material_expression(mat, baseline))
        if 'Base' in names:
            baseline = sources[names.index('Base')]
        if mat.get_editor_property('tangent_space_normal'):
            world_normal = node(u.MaterialExpressionTransform, 'AuthoredNormalToWorld')
            world_normal.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT)
            world_normal.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
            wire(baseline, world_normal, 'Input')
            baseline = world_normal
        anchor = custom('AuthoredNormal', 'return Legacy;', {'Legacy': baseline}, 3)

    pos = node(u.MaterialExpressionWorldPosition, 'Position')
    pos.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    surface_pos = node(u.MaterialExpressionWorldPosition, 'DisplacedPosition')
    clock = node(u.MaterialExpressionTime, 'Clock')
    vertex = node(u.MaterialExpressionVertexColor, 'VertexData')
    rgba = custom('VertexRGBA', 'return float4(RGB,Alpha);', {'RGB': vertex, 'Alpha': (vertex, 'A')}, 4)
    camera = node(u.MaterialExpressionCameraPositionWS, 'Camera')
    pixel_depth = node(u.MaterialExpressionPixelDepth, 'PixelDepth')
    behind = node(u.MaterialExpressionSceneDepthWithoutWater, 'ReceiverDepth')
    coverage = custom('Coverage', 'return ' + ('smoothstep(0,.65,V.r);' if puddle else
                      'smoothstep(0,.06,V.a);' if river else '1;'), {'V': rgba})
    depth = custom('InteractionDepth', 'return max(3,V.a*100);' if river else 'return 12;',
                   {'V': rgba})
    flow = rgba if river else (vector('WaterImpactFlow', (.5,.5,0,1)), 'RGBA')
    fields = [n for n in nodes if isinstance(n, u.MaterialExpressionCustom) and
              str(n.get_editor_property('description')) in ('River pilot bullet ripples', 'All water impact field')]
    if len(fields) != 1:
        raise RuntimeError('Expected one existing shared impact field on ' + mat.get_path_name())
    inputs = {'Position': pos, 'Clock': clock, 'Depth': depth, 'Flow': flow,
              'Pilot': scalar('WaterImpactEnabled', 1)}
    for i in range(8):
        for pin, parameter, value in [('Hit', 'WaterHit', (0,0,-10000,0)), ('Meta', 'WaterHitMeta', (0,1,1,0))]:
            name = parameter + str(i)
            n = next((n for n in nodes if isinstance(n, u.MaterialExpressionVectorParameter)
                      and str(n.get_editor_property('parameter_name')) == name), None)
            inputs[pin + str(i)] = (n or vector(name, value), 'RGBA')
    for i in range(4):
        for pin, value in [('Wake', (0,0,0,0)), ('WakeMotion', (1,0,0,-10000))]:
            name = 'Water' + pin + str(i)
            n = next((n for n in nodes if isinstance(n, u.MaterialExpressionVectorParameter)
                      and str(n.get_editor_property('parameter_name')) == name), None)
            inputs[pin + str(i)] = (n or vector(name, value), 'RGBA')
    field = custom('SharedField', (ROOT/'SourceAssets/RiverPilot20260923/RippleField.hlsl').read_text(),
                   inputs, 3, fields[0])
    # Use the accepted spectrum only for normals on the coarser river and thin puddles.
    # Fountain geometry keeps its authored basin/jet-driven displacement.
    wave_pos = custom('WavePosition', 'float2 d=normalize(Flow.rg*2-1+float2(.00001,0));'
                      'return P-float3(d*T*Flow.b*160,0);', {'P': pos, 'T': clock, 'Flow': flow}, 3)
    wave = custom('Spectrum', (ROOT/'SourceAssets/ClearwaterNative20260926/WaveField.hlsl').read_text(),
                  {'Position': wave_pos, 'Clock': clock,
                   'WaveHeightScale': scalar('NativeWaveScale', .65 if river else .18 if not puddle else .045)}, 3)
    base = vector('NativeFlatNormal', (0,0,1,0)) if river else anchor
    normal = custom('Normal', 'return normalize(float3(Base.xy + (-Wave.yz + Field.xy)*Coverage, max(.2,Base.z)));',
                    {'Base': base, 'Wave': wave, 'Field': field, 'Coverage': coverage}, 3)
    if river:
        foam_tex = node(u.MaterialExpressionTextureObject, 'ShoreFoamTexture')
        foam_tex.set_editor_property('texture', u.load_asset('/Game/WaterMaterials/Textures/T_Ocean_Foam'))
        foam = custom('Foam', (ROOT/'SourceAssets/RiverPilot20260923/ShoreFoam.hlsl').read_text(),
                      {'Position': pos, 'Flow': flow, 'Clock': clock,
                       'Depth': custom('ShoreDepth', 'return V.a*100;', {'V': rgba}),
                       'Ripple': field, 'FoamTexture': foam_tex})
    else:
        foam = custom('Foam', 'return saturate(Field.z*Coverage*Scale);',
                      {'Field': field, 'Coverage': coverage, 'Scale': scalar('NativeFoamScale', .12 if puddle else .26)})
    prop(normal, 'NORMAL')
    prop(custom('Albedo', 'return float3(.55,.63,.60)*Foam;', {'Foam': foam}, 3), 'BASE_COLOR')
    prop(custom('BRDF', 'return saturate(.02+Foam*.85)*Coverage;', {'Foam': foam, 'Coverage': coverage}), 'OPACITY')
    prop(custom('Roughness', 'float r=.075+.055*smoothstep(1500,14000,length(P-Cam));'
                'return lerp(lerp(.27,r,Coverage),.34,Foam);',
                {'P': pos, 'Cam': camera, 'Coverage': coverage, 'Foam': foam}), 'ROUGHNESS')
    prop(custom('Specular', 'return .255*Coverage;', {'Coverage': coverage}), 'SPECULAR')
    zero = scalar('NativeZero', 0)
    prop(zero, 'EMISSIVE_COLOR')
    prop(zero, 'METALLIC')
    if river or puddle:
        prop(zero, 'WORLD_POSITION_OFFSET')
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED if puddle else u.BlendMode.BLEND_OPAQUE)
    if puddle:
        prop((vertex, 'R'), 'OPACITY_MASK')
        mat.set_editor_property('opacity_mask_clip_value', .025)
    mat.set_editor_property('tangent_space_normal', False)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    volume = node(u.MaterialExpressionSingleLayerWaterMaterialOutput, 'Volume')
    wire(vector('NativeScatteringPerCm', (.00028,.00052,.00068,0)), volume, 'ScatteringCoefficients')
    wire(vector('NativeAbsorptionPerCm', (.004,.00074,.00088,0)), volume, 'AbsorptionCoefficients')
    wire(scalar('NativePhaseG', .8), volume, 'PhaseG')
    atlas = node(u.MaterialExpressionTextureObject, 'CausticAtlas')
    atlas_asset = u.load_asset(ATLAS)
    if not atlas_asset:
        raise RuntimeError('Install the accepted Clearwater atlas first')
    atlas.set_editor_property('texture', atlas_asset)
    atlas.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    caustics = custom('Caustics', (OUT/'CausticsBehindWater.hlsl').read_text(),
                      {'Position': surface_pos, 'Camera': camera, 'BehindDepth': behind,
                       'PixelDepth': pixel_depth, 'Clock': clock, 'Atlas': atlas, 'Coverage': coverage,
                       'SunDirection': vector('NativeSunDirection', (.8525,.0896,.515,0)),
                       'PatchCm': scalar('NativeCausticPatchCm', 460),
                       'Strength': scalar('NativeCausticStrength', .5 if river else .35 if not puddle else .05),
                       'Daylight': scalar('NativeCausticDaylight', 0)}, 3)
    wire(caustics, volume, 'ColorScaleBehindWater')
    E.set_metadata_tag(mat, 'NativeWater.Profile', profile)
    E.set_metadata_tag(mat, 'NativeWater.Revision', '20260926')


def author():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
            raise RuntimeError('Preserve active PIE; stop play before water material production')
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(TARGETS):
        raise RuntimeError('Preserve unsaved water masters: ' + str(dirty.intersection(TARGETS)))
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    saved = []
    for path, profile in TARGETS.items():
        mat = u.load_asset(path)
        if not mat:
            raise RuntimeError('Missing active water master: ' + path)
        relative = Path(path.removeprefix('/Game/') + '.uasset')
        backup = OUT / ('BeforeNative_' + stamp) / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/'Content'/relative, backup)
        apply_native_water(mat, profile)
        errors = L.recompile_material(mat)
        if errors:
            raise RuntimeError('Native water compilation failed: ' + path + ' ' + str(errors))
        if not u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()], False):
            raise RuntimeError('Native water save failed: ' + path)
        saved.append(dict(path=path, profile=profile, compiled=True, saved=True))
    receipt = dict(revision='native-all-water-20260926', materials=saved, atlas=ATLAS,
                   caustic_frames=32, shader_samples_per_caustic=2,
                   splash_pool=12, hit_slots=8, wake_slots=4, runtime_tested=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/('assets-saved-'+stamp+'.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('NATIVE_ALL_WATER_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    author()
