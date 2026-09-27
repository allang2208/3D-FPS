"""Produce mf-v14/pass-v7 grass assets with real shader compilation.
No map, play session, capture or audit. Update owned nodes without deleting rooted expressions.
Paused candidate: v14 instance bounds are not fully saved and visuals are rejected.
Resume only when requested; see Docs/WorldGeneration/grass-paused-publication-20260927.md.
"""
import json
import shutil
import importlib.util
from datetime import datetime
from pathlib import Path
import unreal as u

L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
DEST = '/Game/WorldGeneration/GrassDeform'
COLLECTION = '/Game/PN_GrassLibrary/Materials/PN_WindParameters'
MASTERS = ('/Game/PN_GrassLibrary/Materials/grassMaterials/MA_Grass',
           '/Game/WorldGeneration/TemperateHills/Grass/M_TemperateMeadow')
FUNCTION_VERSION, PASS_VERSION = 'mf-v14', 'pass-v7'
TAG = 'GrassDeformVersion'
ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/GrassDeform20260927'
SETTINGS = None
_spec = importlib.util.spec_from_file_location('grass_rest_bounds', ROOT / 'Tools/GrassDeform/rest_bounds.py')
REST_BOUNDS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(REST_BOUNDS)

def setting(name):
    # Config-only UObject classes can use the generic Python Object wrapper. Read the
    # native reflected name; snake_case aliases are not generated for that wrapper.
    native_name = ''.join(part.capitalize() for part in name.split('_'))
    return float(SETTINGS.get_editor_property(native_name))


REPORT = {'function': FUNCTION_VERSION, 'passes': PASS_VERSION, 'saved': [],
          'shader_errors': {}, 'scope': 'Asset production only; no gameplay or visual testing'}


def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing grass asset: ' + path)
    return obj


def asset(path, cls, factory):
    if E.does_asset_exist(path):
        return load(path)
    folder, name = path.rsplit('/', 1)
    E.make_directory(folder)
    obj = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, cls, factory)
    if obj is None:
        raise RuntimeError('Cannot create ' + path)
    return obj


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Cannot save ' + obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())


def compile_material(mat):
    # UE 5.8 returns TArray<FString>, not bool. Empty = compilation completed.
    errors = [str(e) for e in L.recompile_material(mat)]
    REPORT['shader_errors'][mat.get_path_name()] = errors
    if errors:
        raise RuntimeError('Shader compilation failed for %s: %s' % (mat.get_name(), errors))


class Graph:
    def __init__(self, graph):
        self.graph = graph
        self.function = isinstance(graph, u.MaterialFunction)
        self.nodes = list(L.get_material_function_expressions(graph) if self.function
                          else L.get_material_expressions(graph))

    def node(self, cls, key):
        desc = 'GrassV10.' + key
        found = next((n for n in self.nodes if str(n.get_editor_property('desc')) == desc), None)
        if found:
            if not isinstance(found, cls):
                raise RuntimeError('Grass node type changed: ' + desc)
            return found
        obj = (L.create_material_expression_in_function(self.graph, cls) if self.function
               else L.create_material_expression(self.graph, cls))
        obj.set_editor_property('desc', desc)
        self.nodes.append(obj)
        return obj

    def wire(self, source, target, pin):
        node, output = source if isinstance(source, tuple) else (source, '')
        if not L.connect_material_expressions(node, output, target, pin):
            raise RuntimeError('Cannot connect %s.%s -> %s.%s' % (node.get_name(), output, target.get_name(), pin))

    def custom(self, key, code, width, inputs):
        n = self.node(u.MaterialExpressionCustom, key)
        n.set_editor_property('code', code)
        n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
        pins = []
        for name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        n.set_editor_property('inputs', pins)
        for name, source in inputs.items():
            self.wire(source, n, name)
        return n

    def scalar(self, name, value):
        n = self.node(u.MaterialExpressionScalarParameter, name)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', value)
        return n

    def vector(self, name, value):
        n = self.node(u.MaterialExpressionVectorParameter, name)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', u.LinearColor(*value))
        return n

    def collection(self, mpc, name):
        n = self.node(u.MaterialExpressionCollectionParameter, 'MPC.' + name)
        n.set_editor_property('collection', mpc)
        n.set_editor_property('parameter_name', name)
        return n

    def texture(self, name, target):
        n = self.node(u.MaterialExpressionTextureObjectParameter, name)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('texture', target)
        n.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return n

    def output(self, name, source, priority):
        # Preserve FunctionOutput GUIDs: existing callers serialize these identities.
        outputs = [n for n in self.nodes if isinstance(n, u.MaterialExpressionFunctionOutput)
                   and str(n.get_editor_property('output_name')) == name]
        if not outputs:
            outputs = [self.node(u.MaterialExpressionFunctionOutput, 'Output.' + name)]
        # Historical delete/recreate runs can leave more than one same-named output.
        # Keep every serialized identity valid and bind each to the current implementation.
        for n in outputs:
            n.set_editor_property('output_name', name)
            n.set_editor_property('sort_priority', priority)
        for n in outputs:
            self.wire(source, n, '')


def build_collection():
    mpc = load(COLLECTION)
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    vectors = list(mpc.get_editor_property('vector_parameters'))
    for name, value in [('WindowSize', 4800.), ('WorldTime', 0.), ('RegrowthSeconds', setting('hold_seconds') + setting('recover_seconds')),
                        ('bEnabled', 0.), ('WaveSpeed', 1800.), ('ReadIsB', 0.),
                        ('GrassWaveStartTime', 0.), ('GrassWaveRadius', 0.), ('GrassWaveStrength', 0.),
                        ('GrassHoldSeconds', setting('hold_seconds')), ('GrassRecoverSeconds', setting('recover_seconds')),
                        ('GrassCoreFraction', setting('core_fraction')), ('GrassBendAngle', setting('bend_angle_degrees')),
                        ('GrassFlatWindScale', setting('flat_wind_scale')), ('GrassForwardBias', setting('forward_bias'))]:
        entry = next((s for s in scalars if str(s.get_editor_property('parameter_name')) == name), None)
        if entry is None:
            entry = u.CollectionScalarParameter()
            entry.set_editor_property('parameter_name', name)
            entry.set_editor_property('default_value', value)
            scalars.append(entry)
        else:
            entry.set_editor_property('default_value', value)
    for name in ('Center', 'WaveOrigin', 'GrassBodyContact', 'GrassBodyMotion'):
        if not any(str(v.get_editor_property('parameter_name')) == name for v in vectors):
            v = u.CollectionVectorParameter()
            v.set_editor_property('parameter_name', name)
            v.set_editor_property('default_value', u.LinearColor(0, 0, 0, 0))
            vectors.append(v)
    mpc.set_editor_property('scalar_parameters', scalars)
    mpc.set_editor_property('vector_parameters', vectors)
    save(mpc)
    return mpc


def build_targets():
    targets = []
    for suffix in ('A', 'B'):
        rt = asset(DEST + '/RT_GrassDeform' + suffix, u.TextureRenderTarget2D, u.TextureRenderTargetFactoryNew())
        rt.set_editor_property('size_x', 1024)
        rt.set_editor_property('size_y', 1024)
        rt.set_editor_property('render_target_format', u.TextureRenderTargetFormat.RTF_RGBA16F)
        rt.set_editor_property('clear_color', u.LinearColor(0, .5, .5, 0))
        rt.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
        rt.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
        rt.set_editor_property('srgb', False)
        E.set_metadata_tag(rt, TAG, 'rt-v2-rgb')
        save(rt)
        targets.append(rt)
    times = []
    for suffix in ('A', 'B'):
        rt = asset(DEST + '/RT_GrassContactTime' + suffix, u.TextureRenderTarget2D, u.TextureRenderTargetFactoryNew())
        rt.set_editor_property('size_x', 1024)
        rt.set_editor_property('size_y', 1024)
        rt.set_editor_property('render_target_format', u.TextureRenderTargetFormat.RTF_R32F)
        rt.set_editor_property('clear_color', u.LinearColor(0, 0, 0, 0))
        rt.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
        rt.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
        # Do not interpolate contact times with the empty background across footprint edges.
        rt.set_editor_property('filter', u.TextureFilter.TF_NEAREST)
        rt.set_editor_property('srgb', False)
        E.set_metadata_tag(rt, TAG, 'time-v1-r32f')
        save(rt)
        times.append(rt)
    return targets, times


# Custom expressions are function BODIES; nested function definitions are invalid HLSL.
SAMPLE_CODE = '''
if (Enabled < 0.5 || any(UV < 0.0) || any(UV > 1.0)) return float3(0,0.5,0.5);
float3 mask;
float lastContact;
[branch] if (ReadIsB > 0.5)
{
    mask = Texture2DSampleLevel(RTB, RTBSampler, UV, 0).rgb;
    lastContact = Texture2DSampleLevel(TimeB, TimeBSampler, UV, 0).r;
}
else
{
    mask = Texture2DSampleLevel(RTA, RTASampler, UV, 0).rgb;
    lastContact = Texture2DSampleLevel(TimeA, TimeASampler, UV, 0).r;
}
float recovery = saturate((WorldTime-lastContact-max(HoldSeconds,0.0))/max(RecoverSeconds,0.05));
float remaining = 1.0-recovery*recovery*(3.0-2.0*recovery);
return float3(mask.r*remaining, 0.5+(mask.gb-0.5)*remaining);
'''
BODY_CODE = '''
if (Enabled < 0.5 || Contact.a <= 0.0) return Mask;
float2 delta = RootWorld.xy-Contact.xy;
float distance = length(delta);
float radius = max(Contact.z,1.0);
float falloff = 1.0-saturate((distance/radius-CoreFraction)/max(1.0-CoreFraction,0.05));
float2 forward = Motion.xy / max(length(Motion.xy),0.001);
float along = dot(delta,forward);
float2 lateral = delta-forward*along;
float front = sqrt(max(radius*radius-dot(lateral,lateral),0.0));
float entry = Motion.z > 0.001 ? smoothstep(0.0,Motion.z,front-along) : 1.0;
float pressure = Contact.a*falloff*falloff*(3.0-2.0*falloff)*entry;
if (pressure <= Mask.r) return Mask;
float2 radial = distance > 0.001 ? delta/distance : forward;
float2 direction = normalize(lerp(radial,forward,ForwardBias));
return float3(pressure,0.5+0.5*pressure*direction);
'''
BEND_CODE = '''
if (Enabled < 0.5 || any(UV < 0.0) || any(UV > 1.0)) return float3(0,0,0);
float amount = saturate(Mask.r);
float2 direction = Mask.gb * 2.0 - 1.0;
// Evaluate the interaction once per blade, using its authored PivotPainter root.
float2 delta = RootWorld.xy - WaveOrigin.xy;
float distance = length(delta);
float age = WorldTime - WaveStart;
if (WaveStrength > 0.0 && age >= 0.0 && age * WaveSpeed <= WaveRadius + WaveWidth)
{
    float wave = (1.0 - saturate(abs(distance - age * WaveSpeed) / max(WaveWidth,1.0)))
               * (1.0 - saturate(distance / max(WaveRadius,1.0))) * WaveStrength;
    if (wave > amount) direction = delta / max(distance,0.001);
    amount = max(amount, wave);
}
if (amount < 0.0001) return float3(0,0,0);
float3 up = normalize(InstanceUp);
float3 bend = float3(direction,0);
bend -= up * dot(bend,up);
float bendLength = length(bend);
if (bendLength < 0.001) return float3(0,0,0);
// Fade out at opposing-direction boundaries instead of normalizing a near-zero vector.
amount *= saturate(bendLength / max(amount * 0.2, 0.001));
// Align the authored stem to a common low pose. Adding a fixed angle to an
// already tilted stem makes neighbouring blades overshoot or stay upright.
float targetAngle = radians(clamp(BendAngle,0.0,85.0));
float3 targetStem = up*cos(targetAngle) + (bend/bendLength)*sin(targetAngle);
float3 sourceStem = normalize(BladeAxisWorld);
float cosine = clamp(dot(sourceStem,targetStem),-1.0,1.0);
float3 rotationAxis = cross(sourceStem,targetStem);
float axisLength = length(rotationAxis);
float3 axis = axisLength > 0.0001 ? rotationAxis/axisLength : normalize(cross(up,bend/bendLength));
float angle = acos(cosine)*amount;
// One angle limit for the entire blade. Per-vertex clamps stretch its triangles.
angle = min(angle, 2.0 * asin(saturate(MaxOffset / max(2.0 * BladeBound, 0.001))));
float3 relative = WorldPos - RootWorld;
float3 p = relative + WindWPO * (1.0 - (1.0-FlatWindScale) * smoothstep(0.0,0.65,amount));
float s, c;
sincos(angle, s, c);
float3 rotated = p*c + cross(axis,p)*s + axis*dot(axis,p)*(1.0-c);
// Compose wind inside the bend. The parent Add still contributes the original wind.
return rotated - relative - WindWPO;
'''


def build_function(mpc, targets, times):
    fn = asset(DEST + '/MF_GrassDeform', u.MaterialFunction, u.MaterialFunctionFactoryNew())
    g = Graph(fn)
    world = g.node(u.MaterialExpressionWorldPosition, 'WorldPosition')
    world.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    blade_uv = g.node(u.MaterialExpressionTextureCoordinate, 'BladePivotUV')
    blade_uv.set_editor_property('coordinate_index', 1)
    pivot_texture = g.texture('Position and Index Texture', load(
        '/Engine/Functions/Engine_MaterialFunctions02/ExampleContent/PivotPainter2/SimpExPivPos'))
    root_local = g.custom('BladeRoot', 'return Texture2DSampleLevel(Pivots, PivotsSampler, BladeUV, 0).rgb;', 3,
                          {'Pivots': pivot_texture, 'BladeUV': blade_uv})
    root_world = g.node(u.MaterialExpressionTransformPosition, 'BladeRootWorld')
    root_world.set_editor_property('transform_source_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    root_world.set_editor_property('transform_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    g.wire(root_local, root_world, '')
    # Reuse the pack's actual per-instance VEC parameter and engine decoder. UV1
    # identifies one blade; axis and rotation remain identical across its triangles.
    axis_texture = g.texture('X-Vector And X-Extent Texture', load(
        '/Engine/Functions/Engine_MaterialFunctions02/ExampleContent/PivotPainter2/PP2_rgb_XVect_a_XExtent'))
    axis_encoded = g.custom('BladeAxisEncoded', 'return Texture2DSampleLevel(Axes, AxesSampler, BladeUV, 0).rgb;', 3,
                            {'Axes': axis_texture, 'BladeUV': blade_uv})
    axis_world = g.node(u.MaterialExpressionMaterialFunctionCall, 'BladeAxisWorld')
    axis_world.set_material_function(load(
        '/Engine/Functions/Engine_MaterialFunctions02/PivotPainter2/ms_PivotPainter2_DecodeAxisVector'))
    g.wire(axis_encoded, axis_world, 'Axis Vector RGB')
    # Renderer InstanceLocalBounds ALREADY contains MaxWPO padding. Feeding it
    # into our angle clamp creates feedback: increasing the renderer envelope
    # makes the physical bend weaker. Use saved, unpadded source-mesh dimensions.
    rest_min = g.vector(REST_BOUNDS.PARAM_MIN, (-40., -40., -10., 0.))
    rest_max = g.vector(REST_BOUNDS.PARAM_MAX, (40., 40., 100., 0.))
    up_local = g.custom('UpLocal', 'return float3(0,0,1);', 3, {})
    up_world = g.node(u.MaterialExpressionTransform, 'InstanceUpWorld')
    up_world.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE)
    up_world.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    g.wire(up_local, up_world, '')
    extent_local = g.custom('BladeBoundsLocal', 'return max(abs(Maximum-Root),abs(Minimum-Root));', 3,
                            {'Maximum': rest_max, 'Minimum': rest_min, 'Root': root_local})
    scale = g.node(u.MaterialExpressionMaterialFunctionCall, 'InstanceScale')
    scale.set_material_function(load('/Engine/Functions/Engine_MaterialFunctions02/WorldPositionOffset/ObjectScale'))
    blade_bound = g.custom('BladeBound', 'return length(Extent*Scale);', 1,
                           {'Extent': extent_local, 'Scale': (scale, 'Scale XYZ')})
    wind = g.node(u.MaterialExpressionFunctionInput, 'WindInput')
    wind.set_editor_property('input_name', 'WindWPO')
    wind.set_editor_property('input_type', u.FunctionInputType.FUNCTION_INPUT_VECTOR3)
    wind.set_editor_property('use_preview_value_as_default', True)
    uv = g.custom('UV', 'return (WorldPos.xy-Center.xy)/max(WindowSize,1.0)+0.5;', 2,
                  {'WorldPos': root_world, 'Center': g.collection(mpc, 'Center'), 'WindowSize': g.collection(mpc, 'WindowSize')})
    enabled = g.collection(mpc, 'bEnabled')
    mask = g.custom('Sample', SAMPLE_CODE, 3,
                    {'Enabled': enabled, 'ReadIsB': g.collection(mpc, 'ReadIsB'), 'UV': uv,
                     'RTA': g.texture('GrassDeformRTA', targets[0]), 'RTB': g.texture('GrassDeformRTB', targets[1]),
                     'TimeA': g.texture('GrassContactTimeA', times[0]), 'TimeB': g.texture('GrassContactTimeB', times[1]),
                     'WorldTime': g.collection(mpc, 'WorldTime'), 'HoldSeconds': g.collection(mpc, 'GrassHoldSeconds'),
                     'RecoverSeconds': g.collection(mpc, 'GrassRecoverSeconds')})
    mask = g.custom('BodyContact', BODY_CODE, 3,
                    {'Enabled': enabled, 'Mask': mask, 'RootWorld': root_world,
                     'Contact': g.collection(mpc, 'GrassBodyContact'), 'Motion': g.collection(mpc, 'GrassBodyMotion'),
                     'CoreFraction': g.collection(mpc, 'GrassCoreFraction'), 'ForwardBias': g.collection(mpc, 'GrassForwardBias')})
    bend = g.custom('Bend', BEND_CODE, 3,
                    {'Enabled': enabled, 'UV': uv, 'Mask': mask, 'WorldPos': world, 'RootWorld': root_world,
                     'InstanceUp': up_world, 'BladeAxisWorld': axis_world, 'BladeBound': blade_bound, 'WindWPO': wind,
                     'WaveOrigin': g.collection(mpc, 'WaveOrigin'), 'WorldTime': g.collection(mpc, 'WorldTime'),
                     'WaveStart': g.collection(mpc, 'GrassWaveStartTime'), 'WaveRadius': g.collection(mpc, 'GrassWaveRadius'),
                     'WaveStrength': g.collection(mpc, 'GrassWaveStrength'), 'WaveSpeed': g.collection(mpc, 'WaveSpeed'),
                     'WaveWidth': g.scalar('WaveWidth', 90.), 'BendAngle': g.collection(mpc, 'GrassBendAngle'), 'FlatWindScale': g.collection(mpc, 'GrassFlatWindScale'),
                     'MaxOffset': g.scalar('GrassDeformMaxOffset', 300.)})
    flatten = g.custom('Flatten', 'return Mask.r;', 1, {'Mask': mask})
    fn.set_editor_property('description', 'Unpadded rest-mesh rotation bounds, authored stem target and fast recovery; ' + FUNCTION_VERSION)
    E.set_metadata_tag(fn, TAG, FUNCTION_VERSION)
    g.output('Flatten', flatten, 1)
    g.output('WPO', bend, 0)
    L.update_material_function(fn, None)
    REPORT['function_outputs'] = [
        {'name': str(n.get_editor_property('output_name')), 'node': n.get_path_name(),
         'inputs': [{'path': s.get_path_name(), 'desc': str(s.get_editor_property('desc'))} if s else None
                    for s in L.get_inputs_for_material_function_expression(fn, n)]}
        for n in g.nodes if isinstance(n, u.MaterialExpressionFunctionOutput)]
    print('GRASS_FUNCTION_OUTPUTS ' + json.dumps(REPORT['function_outputs']), flush=True)
    save(fn)
    return fn


# Shared contact coverage and time curve for both outputs of one stamp.
STAMP_COMMON = '''
float3 old = Texture2DSampleLevel(Old, OldSampler, UV, 0).rgb;
float oldTime = Texture2DSampleLevel(OldTime, OldTimeSampler, UV, 0).r;
float2 segment = Center.xy-Start.xy;
float t = saturate(dot(UV-Start.xy,segment)/max(dot(segment,segment),1e-10));
float2 closest = lerp(Center.xy,Start.xy+segment*t,IsSweep);
float2 delta = UV-closest;
float distance = length(delta);
float falloff = 1.0-saturate((distance/max(Radius,1e-5)-CoreFraction)/max(1.0-CoreFraction,0.05));
float2 forward = Travel.xy / max(length(Travel.xy),0.001);
float2 currentDelta = UV-Center.xy;
float along = dot(currentDelta,forward);
float2 lateral = currentDelta-forward*along;
float front = sqrt(max(Radius*Radius-dot(lateral,lateral),0.0));
float entry = PressDistance > 1e-7 ? smoothstep(0.0,PressDistance,front-along) : 1.0;
float pressure = Strength*falloff*falloff*(3.0-2.0*falloff)*entry;
float recovery = saturate((Now-oldTime-max(HoldSeconds,0.0))/max(RecoverSeconds,0.05));
float remaining = 1.0-recovery*recovery*(3.0-2.0*recovery);
float current = old.r*remaining;
'''
STAMP_CODE = STAMP_COMMON + '''
if (pressure <= 0.0001) return old;
float2 radial = distance > 1e-6 ? delta/distance : forward;
float2 direction = normalize(lerp(radial,forward,DirectionBias));
// Re-contact retains the current recovered value, never resurrects the historic maximum.
float result = max(current,pressure);
float2 encoded = pressure >= current ? direction*result*0.5+0.5 : 0.5+(old.gb-0.5)*remaining;
return float3(result,encoded);
'''
STAMP_TIME_CODE = STAMP_COMMON + '''
return float3(pressure > 0.0001 ? Now : oldTime,0,0);
'''
RECENTER_CODE = '''
float2 sourceUV = UV + Shift.xy;
if (any(sourceUV < 0.0) || any(sourceUV > 1.0)) return float3(0,0.5,0.5);
return Texture2DSampleLevel(Old, OldSampler, sourceUV, 0).rgb;
'''
RECENTER_TIME_CODE = '''
float2 sourceUV = UV + Shift.xy;
if (any(sourceUV < 0.0) || any(sourceUV > 1.0)) return float3(0,0,0);
return float3(Texture2DSampleLevel(Old, OldSampler, sourceUV, 0).r,0,0);
'''


def build_passes(target, time_target):
    for kind, code in [('Stamp', STAMP_CODE), ('StampTime', STAMP_TIME_CODE),
                       ('Recenter', RECENTER_CODE), ('RecenterTime', RECENTER_TIME_CODE)]:
        mat = asset(DEST + '/M_GrassDeform' + kind, u.Material, u.MaterialFactoryNew())
        mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
        g = Graph(mat)
        uv = g.node(u.MaterialExpressionTextureCoordinate, 'UV')
        inputs = {'UV': uv, 'Old': g.texture('Old', time_target if kind == 'RecenterTime' else target)}
        if kind.startswith('Stamp'):
            inputs.update(Center=g.vector('CenterUV', (.5,.5,0,0)), Radius=g.scalar('RadiusUV', .05),
                          Strength=g.scalar('Strength', .5), Start=g.vector('StartUV', (.5,.5,0,0)),
                          IsSweep=g.scalar('IsSweep', 0.), Travel=g.vector('TravelDirection', (1,0,0,0)),
                          CoreFraction=g.scalar('CoreFraction', setting('core_fraction')),
                          DirectionBias=g.scalar('DirectionBias', setting('forward_bias')),
                          PressDistance=g.scalar('PressDistanceUV', 0.), Now=g.scalar('ContactNow', 0.),
                          HoldSeconds=g.scalar('HoldSeconds', setting('hold_seconds')),
                          RecoverSeconds=g.scalar('RecoverSeconds', setting('recover_seconds')),
                          OldTime=g.texture('OldTime', time_target))
        else:
            inputs['Shift'] = g.vector('ShiftUV', (0,0,0,0))
        body = g.custom('Pass.' + kind, code, 3, inputs)
        if not L.connect_material_property(body, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError('Cannot connect grass pass output: ' + kind)
        compile_material(mat)
        E.set_metadata_tag(mat, TAG, PASS_VERSION)
        save(mat)


def patch_master(path, fn):
    master = load(path)
    g = Graph(master)
    existing = L.get_material_property_input_node(master, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    if existing is None:
        raise RuntimeError('Grass master has no readable wind WPO: ' + path)
    calls = [n for n in g.nodes if isinstance(n, u.MaterialExpressionMaterialFunctionCall)
             and n.get_editor_property('material_function') == fn]
    call = calls[0] if calls else g.node(u.MaterialExpressionMaterialFunctionCall, 'Call')
    if not call.set_material_function(fn):
        raise RuntimeError('Cannot refresh grass function call in ' + path)
    if str(existing.get_editor_property('desc')) == 'GrassDeformWPOAdd':
        add = existing
    else:
        previous_output = L.get_material_property_input_node_output_name(master, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        add = g.node(u.MaterialExpressionAdd, 'WPOAdd')
        add.set_editor_property('desc', 'GrassDeformWPOAdd')
        g.wire((existing, previous_output), add, 'A')
    g.wire((call, 'WPO'), add, 'B')
    wind_node = L.get_inputs_for_material_expression(master, add)[0]
    wind_output = L.get_input_node_output_name_for_material_expression(add, wind_node)
    if wind_output is None:
        raise RuntimeError('Cannot preserve original wind output: ' + path)
    g.wire((wind_node, wind_output), call, 'WindWPO')
    if not L.connect_material_property(add, '', u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        raise RuntimeError('Cannot connect grass WPO: ' + path)
    master.set_editor_property('used_with_instanced_static_meshes', True)
    # A stem initially leaning against travel needs a larger arc than a vertical stem.
    # Keep the whole-blade 300cm bound inside a 320cm renderer envelope (including wind).
    master.set_editor_property('max_world_position_offset_displacement', 320.)
    E.set_metadata_tag(master, TAG, FUNCTION_VERSION)
    REPORT.setdefault('master_calls', {})[path] = [
        {'node': n.get_path_name(), 'function': str(n.get_editor_property('material_function'))}
        for n in g.nodes if isinstance(n, u.MaterialExpressionMaterialFunctionCall)]
    compile_material(master)
    return master


def main():
    global SETTINGS
    SETTINGS = u.get_default_object(u.load_class(None, '/Script/FPSGAME.GrassDeformSettings'))
    REPORT['settings'] = {name: setting(name) for name in (
        'body_radius_cm', 'core_fraction', 'body_strength', 'bend_angle_degrees', 'press_seconds',
        'hold_seconds', 'recover_seconds', 'flat_wind_scale', 'forward_bias',
        'footstep_radius_cm', 'footstep_strength', 'footstep_core_fraction')}
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Grass asset authoring waits for the current play session to end.')
    bound_groups = REST_BOUNDS.collect(MASTERS)
    backup = OUT / ('BeforeV14-' + stamp)
    paths = [COLLECTION, *MASTERS, DEST + '/MF_GrassDeform']
    paths += [DEST + '/M_GrassDeform' + k for k in ('Stamp', 'Fade', 'Recenter', 'StampTime', 'RecenterTime')]
    paths += [DEST + '/RT_GrassDeform' + k for k in ('A', 'B')]
    paths += [DEST + '/RT_GrassContactTime' + k for k in ('A', 'B')]
    paths += [path.split('.')[0] for path in bound_groups]
    for path in paths:
        source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        if source.exists():
            destination = backup / source.relative_to(ROOT / 'Content')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    REPORT['backup'] = str(backup)
    try:
        mpc = build_collection()
        targets, times = build_targets()
        fn = build_function(mpc, targets, times)
        build_passes(targets[0], times[0])
        masters = [patch_master(path, fn) for path in MASTERS]
        for master in masters:
            save(master)
        REPORT['rest_bounds'] = REST_BOUNDS.author(bound_groups, save)
    finally:
        (OUT / ('authoring-' + stamp + '.json')).write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    print('GRASS_DEFORM_M1_RESULT ' + json.dumps(REPORT), flush=True)


if __name__ == '__main__':
    main()
