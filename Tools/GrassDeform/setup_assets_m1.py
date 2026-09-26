"""Create and patch the M1 assets of the GPU grass interaction system.

Run headless through Tools/GrassDeform/run_asset_setup_m1.ps1, or through the MCP batch bridge
while an editor holds the project. The script is idempotent: every step checks for the existing
asset or connection and only authors what is missing, so it can be re-run after a partial failure.

Creates under /Game/WorldGeneration/GrassDeform/:
  MPC_GrassDeform        Center, WaveOrigin, WindowSize, WorldTime, RegrowthSeconds, bEnabled,
                         WaveSpeed. A Material Parameter Collection holds scalars and vectors only,
                         so the render target cannot travel through it; MF_GrassDeform reads the RT
                         from a texture parameter on the grass material instead.
  MF_GrassDeform         material function: one RT sample behind a bEnabled static switch
  M_GrassDeformStamp     radial splat pass  (R = flatten, GB = bend dir, A = impulse timestamp)
  M_GrassDeformFade      regrowth pass      (R decays, A expires)
  M_GrassDeformRecenter  UV-offset copy     (window move)

All three pass materials read the previous contents through one texture parameter named "Old",
which the subsystem re-points at the read side of the ping-pong pair before every DrawMaterial.

Patches /Game/PN_GrassLibrary/Materials/grassMaterials/MA_Grass: adds MF_GrassDeform to the World
Position Offset chain after the existing wind. Only the WPO input is touched. If the existing WPO
chain cannot be inspected, the function is left unconnected and the manual step is printed in the
report instead of guessing.

Headless notes (the API shapes this script depends on, all verified against the 5.8 engine source):
  * A material-function graph cannot use MaterialEditingLibrary.create_material_expression(), which
    is typed to UMaterial only; use create_material_expression_in_function() instead. See
    new_expression() below for the source citations.
  * A function is recompiled with update_material_function(), not recompile_material(), which again
    only accepts a UMaterial.
  * A TextureSample node's UV input pin is addressed as 'UVs', not 'UV' or 'Coordinates'.
  * A FunctionOutput node's single input is addressed by the empty name '', not the label 'A'.
  * CustomMaterialOutputType members are upper-cased in Python (CMOT_FLOAT1 .. CMOT_FLOAT4).
  * UMaterial has no 'description' property, so the pass-material version tag is stored in asset
    metadata under VERSION_TAG_KEY.

Plan: Docs/WorldGeneration/grass-interaction-gpu-20260925.md sections 3.1, 3.2, 4 and the
"M1 手工接线（如脚本未连）" section at the end of that document.
Shared contract: Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformTuning.h
"""
import traceback
from datetime import datetime

import unreal as u

DEST = '/Game/WorldGeneration/GrassDeform'
GRASS_MASTER = '/Game/PN_GrassLibrary/Materials/grassMaterials/MA_Grass'

EAL = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary

WINDOW_SIZE_CM = 4800.0
REGROWTH_SECONDS = 18.0

# The two persistent RT assets MF_GrassDeform samples through TextureObjectParameter DEFAULTS.
# Material-side binding MUST be an asset default: a MaterialParameterCollection cannot carry
# textures, and a subsystem-owned runtime MID of MA_Grass never reaches the rendered foliage
# (that was the "grass does not react" bug). Must match GrassDeformSubsystem.cpp
# (GrassDeformAssets::RTAPath / RTBPath).
RTA_PARAMETER = 'GrassDeformRTA'
RTB_PARAMETER = 'GrassDeformRTB'
RT_SIZE = 1024
RT_VERSION_TAG = 'rt-v1'

# MPC scalar that selects which RT asset is the current read side inside MF_GrassDeform
# (0 = A, 1 = B). Published by the subsystem on every ping-pong flip.
READ_IS_B_PARAMETER = 'ReadIsB'

# Source-texture parameter of the three pass materials: the read side of the ping-pong pair.
# Must match GrassDeformSubsystem.cpp (GrassDeformParams::PassSource). The passes sample the
# target they do NOT write, so the subsystem re-points this parameter before every DrawMaterial.
PASS_SOURCE = 'Old'

# Input pin name of a TextureSample node's UV slot. The graph editor *labels* this pin "UV", and
# the engine's own name for the input is "Coordinates" (MaterialExpressions.cpp:2724-2727), but the
# name ConnectMaterialExpressions() actually matches against is the *shortened* pin name:
#   MaterialEditingLibrary.cpp:68-69   TestName = UMaterialGraphNode::GetShortenPinName(GetInputName(i))
#   MaterialGraphNode.cpp:602-605      Coordinates -> UVs
#   MaterialGraphNode.cpp:578-579      ("Coordinates" / "UVs")
# Neither 'UV' nor 'Coordinates' resolves; 'UVs' is the name that works.
TEX_COORD_INPUT = 'UVs'

# Asset-registry metadata key that carries the pass-material contract version. UMaterial exposes no
# Description field (Material.h declares none -- only UMaterialFunction does, MaterialFunction.h:57),
# so the version tag 搂10.5 requires rides on asset metadata instead, which is serialised with the
# asset and readable again on the next run.
VERSION_TAG_KEY = 'GrassDeformVersion'

# Input pin name of a MaterialExpressionFunctionOutput node. The node shows its single input as
# "A", but the engine exposes it with no name at all, so the empty string is the working selector.
FUNCTION_OUTPUT_INPUT = ''

REPORT = {'created': [], 'patched': [], 'skipped': [], 'manual': [], 'errors': []}

# Filled by build_render_targets() in main() before build_function() runs: the two RT assets that
# become the TextureObjectParameter defaults of MF_GrassDeform's samplers.
RT_ASSETS = []


def log(message):
    print('[GrassDeform M1] ' + str(message), flush=True)


def ensure_directory(path):
    if not EAL.does_directory_exist(path):
        EAL.make_directory(path)
        log('created directory ' + path)


def load_optional(path):
    if not EAL.does_asset_exist(path):
        return None
    obj = EAL.load_asset(path)
    if obj is None:
        raise RuntimeError('Asset exists but could not be loaded: ' + path)
    return obj


def save(asset, key, bucket='created'):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    if key not in REPORT[bucket]:
        REPORT[bucket].append(key)
    log('saved ' + asset.get_path_name())
    return asset


def create_asset(name, asset_class, factory):
    asset_tools = u.AssetToolsHelpers.get_asset_tools()
    asset = asset_tools.create_asset(name, DEST, asset_class, factory)
    if asset is None:
        raise RuntimeError('Could not create ' + name)
    log('created asset ' + name)
    return asset


# ---------------------------------------------------------------------------------------------
# Expression authoring: materials vs material functions
#
# MaterialEditingLibrary only accepts a UMaterial for most of its graph API. The two entry points
# that take a graph are genuinely different functions in the engine:
#
#   MaterialEditingLibrary.cpp:634  CreateMaterialExpression(UMaterial*, ...)          -> UMaterial only
#   MaterialEditingLibrary.cpp:676  CreateMaterialExpressionInFunction(UMaterialFunction*, ...)
#
# and the Python binder enforces the declared parameter type, which is exactly why the first run
# died with "Cannot nativize 'MaterialFunction' as 'Object' (allowed Class type: 'Material')":
# MEL.create_material_expression() maps to the UMaterial-only overload. The in-function overload is
# the supported headless path and does the whole job itself -- MaterialEditingLibrary.cpp:676-679
# forwards to CreateMaterialExpressionEx(), which outers the new node to the function and registers
# it:
#
#   MaterialEditingLibrary.cpp:689-692   ExpressionOuter = MaterialFunction
#   MaterialEditingLibrary.cpp:694       NewObject<UMaterialExpression>(ExpressionOuter, ...)
#   MaterialEditingLibrary.cpp:702-705   MaterialFunction->GetExpressionCollection().AddExpression(...)
#   MaterialEditingLibrary.cpp:711       UpdateMaterialExpressionGuid(...)  (stable node id)
#   MaterialEditingLibrary.cpp:745-757   FunctionInput/FunctionOutput GetId + ValidateName
#   MaterialEditingLibrary.cpp:759-764   UpdateParameterGuid + ValidateParameterName
#
# So no raw unreal.new_object() + manual expression-collection poking is needed, and none is used.
#
# The connection writers are graph-agnostic on the *read* side and work for both graphs:
#   MaterialEditingLibrary.cpp:928-943  ConnectMaterialExpressions() -- resolves the input by name
#                                       through GetExpressionInputByName() (line 46) and the output
#                                       index through GetExpressionOutputIndexByName() (line 81);
#                                       it only casts GetOuter() to UMaterial for the editor
#                                       notification (line 939), which is null-safe.
#   MaterialEditingLibrary.cpp:905-926  ConnectMaterialProperty() -- this one *does* need a UMaterial
#                                       (it resolves the property through the graph's outer material,
#                                       line 911), so it is only ever called on pass materials.
# ---------------------------------------------------------------------------------------------


def connect(source, source_output, target, target_input):
    if not MEL.connect_material_expressions(source, source_output, target, target_input):
        raise RuntimeError('Could not connect %s.%s -> %s.%s'
                           % (source.get_name(), source_output, target.get_name(), target_input))


def connect_property(source, source_output, prop):
    if not MEL.connect_material_property(source, source_output, prop):
        raise RuntimeError('Could not connect %s to %s' % (source.get_name(), prop))


def new_expression(graph, expression_class):
    """Create one expression node in `graph`, which may be a UMaterial or a UMaterialFunction.

    A UMaterialFunction graph must go through CreateMaterialExpressionInFunction(); passing it to
    create_material_expression() raises TypeError from the Python binder (see the note above).
    """
    if isinstance(graph, u.MaterialFunction):
        expr = MEL.create_material_expression_in_function(graph, expression_class)
    else:
        expr = MEL.create_material_expression(graph, expression_class)
    if expr is None:
        raise RuntimeError('Could not create %s in %s'
                           % (getattr(expression_class, '__name__', expression_class),
                              graph.get_name()))
    return expr


def add_custom(graph, desc, code, output_type, pin_names):
    """Author a Custom HLSL node. Input pins are declared in `pin_names` order.

    `output_type` is the *Python* spelling of ECustomMaterialOutputType: CMOT_FLOAT1 / CMOT_FLOAT2 /
    CMOT_FLOAT3 / CMOT_FLOAT4. The Python binding upper-cases every enum member, so the C++ source
    spelling (CMOT_Float1 .. CMOT_Float4, MaterialExpressionCustom.h:16-24) does not resolve from
    Python, and a bare CMOT_FLOAT (no digit) does not exist either. A scalar output is CMOT_FLOAT1.

    Input order matters: the generated HLSL receives the pins in this order, and connections are
    resolved by input *name* (MaterialEditingLibrary.cpp:46-79), so the pin list must be authored
    before anything is connected to the node.
    """
    expr = new_expression(graph, u.MaterialExpressionCustom)
    expr.set_editor_property('desc', desc)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', output_type)
    pins = []
    for name in pin_names:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    expr.set_editor_property('inputs', pins)
    return expr


def scalar_param(graph, name, default):
    expr = new_expression(graph, u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', default)
    return expr


def vector_param(graph, name, rgba):
    expr = new_expression(graph, u.MaterialExpressionVectorParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', u.LinearColor(*rgba))
    return expr


def collection_param(graph, name, kind):
    expr = new_expression(graph, u.MaterialExpressionCollectionParameter)
    expr.set_editor_property('collection', MPC)
    expr.set_editor_property('parameter_name', name)
    # Binding by name only is enough; the collection resolves the id on load.
    del kind
    return expr


# ---------------------------------------------------------------------------------------------
# MPC_GrassDeform
# ---------------------------------------------------------------------------------------------

MPC_SCALARS = [
    ('WindowSize', WINDOW_SIZE_CM),
    ('WorldTime', 0.0),
    ('RegrowthSeconds', REGROWTH_SECONDS),
    ('bEnabled', 1.0),
    # Wavefront speed (cm/s) for the impulse in channel A. Written by the subsystem when an
    # impulse is stamped and read by MF_GrassDeform at render time.
    ('WaveSpeed', 1800.0),
    # Selects the read side of the ping-pong RT asset pair inside MF_GrassDeform (0 = A, 1 = B).
    # Published by the subsystem on every flip; uniform across the frame, so the shader branch
    # that consumes it is coherent.
    (READ_IS_B_PARAMETER, 0.0),
]
MPC_VECTORS = [
    ('Center', (0.0, 0.0, 0.0, 0.0)),
    # Origin of the most recent impulse, in window UV (written by the subsystem once per impulse).
    # MF_GrassDeform measures the wavefront radius from this point, so the ring expands from the
    # impact rather than from the window centre.
    ('WaveOrigin', (0.5, 0.5, 0.0, 0.0)),
]


def build_mpc():
    existing = load_optional(DEST + '/MPC_GrassDeform')
    if existing is not None:
        log('MPC_GrassDeform exists; adding any missing parameters')
        mpc = existing
    else:
        mpc = create_asset('MPC_GrassDeform', u.MaterialParameterCollection,
                           u.MaterialParameterCollectionFactoryNew())

    scalars = list(mpc.get_editor_property('scalar_parameters'))
    vectors = list(mpc.get_editor_property('vector_parameters'))
    changed = False

    def present(entries, name):
        return any(e.get_editor_property('parameter_name') == name for e in entries)

    for name, default in MPC_SCALARS:
        if present(scalars, name):
            continue
        entry = u.CollectionScalarParameter()
        entry.set_editor_property('parameter_name', name)
        entry.set_editor_property('default_value', default)
        scalars.append(entry)
        changed = True
        log('  + MPC scalar ' + name)

    for name, rgba in MPC_VECTORS:
        if present(vectors, name):
            continue
        entry = u.CollectionVectorParameter()
        entry.set_editor_property('parameter_name', name)
        entry.set_editor_property('default_value', u.LinearColor(*rgba))
        vectors.append(entry)
        changed = True
        log('  + MPC vector ' + name)

    if changed:
        mpc.set_editor_property('scalar_parameters', scalars)
        mpc.set_editor_property('vector_parameters', vectors)
        save(mpc, 'MPC_GrassDeform')
    else:
        REPORT['skipped'].append('MPC_GrassDeform parameters (already complete)')
    return mpc


# ---------------------------------------------------------------------------------------------
# RT_GrassDeformA / RT_GrassDeformB
#
# The persistent ping-pong pair. These MUST be assets (not runtime-created transient targets):
# MF_GrassDeform reaches them through TextureObjectParameter defaults, which have to resolve at
# shader-compile time so every material instance derived from MA_Grass inherits the binding.
# The subsystem draws into them (pixels are never serialized, so drawing never dirties the
# package) and publishes which side is the read side through the MPC ReadIsB scalar.
# ---------------------------------------------------------------------------------------------

def build_render_targets():
    targets = []
    for name in ('RT_GrassDeformA', 'RT_GrassDeformB'):
        path = DEST + '/' + name
        rt = load_optional(path)
        if rt is not None and RT_VERSION_TAG in pass_version_tag(rt):
            # Save even on the skip path: a previous run may have created the asset in memory and
            # crashed before saving, leaving a phantom the registry knows but the disk does not.
            save(rt, name, bucket='skipped')
            targets.append(rt)
            continue

        if rt is None:
            # The factory class is UTextureRenderTargetFactoryNew (no "2D" in the name,
            # TextureRenderTargetFactoryNew.h:15); it creates a UTextureRenderTarget2D. Its
            # Width/Height/Format UPROPERTYs carry no Edit flag, so Python treats them as
            # protected and refuses set_editor_property - create with the factory defaults and
            # configure the asset itself below (SizeX/SizeY ARE EditAnywhere; update_resource()
            # at the end re-creates the render resource at the final size/format).
            rt = create_asset(name, u.TextureRenderTarget2D, u.TextureRenderTargetFactoryNew())

        rt.set_editor_property('size_x', RT_SIZE)
        rt.set_editor_property('size_y', RT_SIZE)
        # RGBA16F: channel A carries a world-time stamp; 8-bit would quantize the wavefront.
        rt.set_editor_property('render_target_format', u.TextureRenderTargetFormat.RTF_RGBA16F)
        rt.set_editor_property('clear_color', u.LinearColor(0.0, 0.0, 0.0, 0.0))
        rt.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
        rt.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
        # sRGB OFF: this is a data mask (flatten / direction / timestamp), not a color.
        for prop, value in (('srgb', False), ('b_auto_generate_mips', False)):
            try:
                rt.set_editor_property(prop, value)
            except Exception as error:
                log('%s: %s not settable (%s); verify in the editor if the mask looks wrong'
                    % (name, prop, error))
        set_pass_version_tag(rt, RT_VERSION_TAG)
        # UTextureRenderTarget2D exposes no update_resource() in 5.8 Python (that is the
        # UCanvasRenderTarget2D API); set_editor_property already fired PostEditChangeProperty,
        # which re-creates the render resource at the new size/format. Try anyway for forwards
        # compatibility and swallow the AttributeError.
        try:
            rt.update_resource()
        except AttributeError:
            pass
        save(rt, name)
        targets.append(rt)
    return targets


# ---------------------------------------------------------------------------------------------
# MF_GrassDeform
# ---------------------------------------------------------------------------------------------

# The whole per-vertex cost of the feature. One sample, a handful of ALU. The static switch is a
# compile-time branch, so the low-quality permutation performs zero samples.
FUNCTION_CODE = '''
float2 GrassDeform_WorldToUV(float3 WorldPos, float2 Center, float WindowSize)
{
    return (WorldPos.xy - Center) / WindowSize + 0.5;
}

float3 GrassDeform_Evaluate(
    float3 WorldPos,
    float  UpwardFactor,
    float  HeightMask,
    float2 SampleUV,
    float  WindowSize,
    float2 WaveOrigin,
    float  WorldTime,
    float  RegrowthSeconds,
    float  BendScale,
    float  WaveSpeed,
    float  WaveWidth,
    float  MaxOffset,
    float4 DeformSample,
    out float Flatten)
{
    Flatten = DeformSample.r;

    // Bend direction is stored as a 0..1 encoded -1..1 vector. A zero vector means "flatten in
    // place", which is what a direction-less trample stamp writes.
    float2 BendDir = DeformSample.gb * 2.0 - 1.0;

    // Height mask pivots the bend at the base of the blade, matching MA_Grass' existing convention.
    // UpwardFactor (the vertex normal's Z, 0..1) scales the response so blades already facing away
    // from up - and therefore already lying flat - are not bent twice.
    float Pivot = saturate(HeightMask) * saturate(UpwardFactor);

    // Persistent flatten plus an optional one-shot wavefront carried in channel A.
    // Channel A holds the world time at which this texel was stamped, and every texel inside one
    // impulse stamp shares that timestamp. The front is therefore the set of texels whose distance
    // from the impact origin equals Age * WaveSpeed. The origin travels in the MPC's WaveOrigin
    // vector (written once per impulse), so the ring sweeps outward from the explosion rather than
    // from the window centre or from each texel.
    float Wave = 0.0;
    if (DeformSample.a > 0.0)
    {
        float Age = WorldTime - DeformSample.a;
        if (Age >= 0.0 && Age < RegrowthSeconds)
        {
            float2 Delta = (SampleUV - WaveOrigin) * WindowSize;
            float Distance = length(Delta);
            float Front = Age * WaveSpeed;
            Wave = 1.0 - saturate(abs(Distance - Front) / WaveWidth);
            Wave *= 1.0 - saturate(Age / RegrowthSeconds);
        }
    }

    float Amount = saturate(Flatten + Wave);
    float3 Offset = float3(BendDir * BendScale * Amount * Pivot, 0.0);
    // A small downward component keeps a flattened blade from poking through the terrain.
    Offset.z = -MaxOffset * Amount * Pivot;
    Offset = clamp(Offset, -MaxOffset, MaxOffset);
    return Offset;
}
'''

# The function graph reads: world position, vertex normal Z, the MPC parameters, the RT sample and
# the art parameters, then runs GrassDeform_Evaluate (all wiring happens in build_function).


# Bumped whenever the MF graph contract changes (pins, MPC parameters, sample channels). An
# existing asset whose description does not carry the current tag is rebuilt from scratch instead
# of being kept, which is what makes re-running this script converge after a contract change.
FUNCTION_VERSION_TAG = 'mf-v4'

# Same idea for the three pass materials: the graph contract (source parameter name, sample
# channels, parameter names) is versioned so a re-run converges instead of keeping a stale graph.
PASS_VERSION_TAG = 'pass-v2'

FUNCTION_DESCRIPTION = (
    'GPU grass interaction: trample flatten and impulse wavefront, read from MPC_GrassDeform '
    '(Center/WindowSize/WorldTime/RegrowthSeconds/WaveSpeed/WaveOrigin/bEnabled/ReadIsB) and the '
    'persistent RT asset pair RT_GrassDeformA/B (texture-parameter defaults; ReadIsB picks the '
    'read side). Environment inputs (WorldPos/UpwardFactor/HeightMask) are sourced INSIDE the '
    'function, so a call node needs no input wiring. ' + FUNCTION_VERSION_TAG)


def recompile_function(function):
    """Recompile a UMaterialFunction after graph edits.

    MaterialEditingLibrary has no RecompileMaterial overload for functions -- recompile_material()
    takes a UMaterial (MaterialEditingLibrary.h:267) and calling it with a function raises the same
    binder TypeError as the expression API. The function-graph equivalent is
    UpdateMaterialFunction() (MaterialEditingLibrary.h:387-388), which runs
    ForceRecompileForRendering() on the function and on every in-memory function instance that
    depends on it (MaterialEditingLibrary.cpp:1368-1405), then recompiles the materials using it.
    """
    MEL.update_material_function(function, None)


def build_function():
    path = DEST + '/MF_GrassDeform'
    existing = load_optional(path)
    if existing is not None and FUNCTION_VERSION_TAG in str(existing.get_editor_property('description')):
        recompile_function(existing)
        REPORT['skipped'].append('MF_GrassDeform (exists, ' + FUNCTION_VERSION_TAG + ')')
        return existing

    if existing is not None:
        # Rebuild the graph so a stale layout cannot silently keep an old pin/param contract.
        log('MF_GrassDeform exists but is not ' + FUNCTION_VERSION_TAG + '; rebuilding its graph')
        MEL.delete_all_material_expressions_in_function(existing)
        function = existing
    else:
        function = create_asset('MF_GrassDeform', u.MaterialFunction, u.MaterialFunctionFactoryNew())

    function.set_editor_property('description', FUNCTION_DESCRIPTION)

    # A material function's signature is defined by its MaterialExpressionFunctionInput and
    # MaterialExpressionFunctionOutput nodes; the asset itself carries no separate table. The
    # inputs/outputs are authored with the graph below.

    # --- nodes --------------------------------------------------------------------------------
    # One Custom node holds the maths; the graph only supplies its pins. This keeps the function
    # to a single RT sample and a handful of ALU (plan section 3.2 / 7).
    evaluate = add_custom(function, 'GrassDeform_Evaluate', FUNCTION_CODE,
                          u.CustomMaterialOutputType.CMOT_FLOAT3,
                          ['WorldPos', 'UpwardFactor', 'HeightMask', 'SampleUV', 'WindowSize',
                           'WaveOrigin', 'WorldTime', 'RegrowthSeconds', 'BendScale', 'WaveSpeed',
                           'WaveWidth', 'MaxOffset', 'DeformSample'])

    # World position -> window UV -> sample of the deform RT. BOTH ping-pong RT assets are wired as
    # texture-parameter defaults, so every material instance derived from MA_Grass inherits the
    # binding with zero runtime work; the MPC scalar ReadIsB (published on every flip) selects the
    # current read side. A single runtime-bound parameter cannot work here: an MPC cannot carry
    # textures and a subsystem-owned MID never reaches the rendered foliage.
    uv_node = add_custom(function, 'GrassDeform_WorldToUV',
                         'return GrassDeform_WorldToUV(WorldPos, Center, WindowSize);',
                         u.CustomMaterialOutputType.CMOT_FLOAT2,
                         ['WorldPos', 'Center', 'WindowSize'])
    sampler_a = new_expression(function, u.MaterialExpressionTextureSampleParameter2D)
    sampler_a.set_editor_property('parameter_name', RTA_PARAMETER)
    sampler_a.set_editor_property('texture', RT_ASSETS[0])
    connect(uv_node, '', sampler_a, TEX_COORD_INPUT)
    sampler_b = new_expression(function, u.MaterialExpressionTextureSampleParameter2D)
    sampler_b.set_editor_property('parameter_name', RTB_PARAMETER)
    sampler_b.set_editor_property('texture', RT_ASSETS[1])
    connect(uv_node, '', sampler_b, TEX_COORD_INPUT)

    # Read-side select + bEnabled gate. ReadIsB and Enabled are uniform across the draw, so the
    # branch is coherent and only the selected side performs a real fetch; with r.GrassDeform off
    # the gate returns zero and the grass shader does no deform work.
    enabled = collection_param(function, 'bEnabled', 'scalar')
    read_is_b = collection_param(function, READ_IS_B_PARAMETER, 'scalar')
    gate = add_custom(function, 'GrassDeform_Gate',
                      'float4 S = ReadIsB > 0.5 ? SampleB : SampleA;'
                      ' return Enabled > 0.5 ? S : float4(0, 0, 0, 0);',
                      u.CustomMaterialOutputType.CMOT_FLOAT4,
                      ['Enabled', 'ReadIsB', 'SampleA', 'SampleB'])
    connect(enabled, '', gate, 'Enabled')
    connect(read_is_b, '', gate, 'ReadIsB')
    # RGBA, not RGB: channel A carries the impulse timestamp the wavefront maths needs. Feeding
    # only RGB would zero alpha and silently disable the wavefront.
    connect(sampler_a, 'RGBA', gate, 'SampleA')
    connect(sampler_b, 'RGBA', gate, 'SampleB')

    # --- wiring -------------------------------------------------------------------------------
    # mf-v4: the three environment inputs are sourced INSIDE the function (AbsoluteWorldPosition,
    # VertexNormalWS.z, TexCoord0.V + flip parameter). Two reasons: (1) a caller-supplied pin that
    # is never wired falls back to its preview default (0), and HeightMask=0 zeroes the whole WPO
    # output - that unwired call node was the "grass does not react at all" defect; (2) the call
    # node inside MA_Grass cannot be re-wired headlessly anyway, because UMaterial.Expressions is
    # protected from Python. The MA_Grass call node therefore needs no inputs at all; the art
    # knobs stay overridable scalar parameters.
    world_pos = new_expression(function, u.MaterialExpressionWorldPosition)
    connect(world_pos, '', uv_node, 'WorldPos')
    connect(world_pos, '', evaluate, 'WorldPos')

    normal_ws = new_expression(function, u.MaterialExpressionVertexNormalWS)
    upward = add_custom(function, 'GrassDeform_Upward', 'return saturate(N.z);',
                        u.CustomMaterialOutputType.CMOT_FLOAT1, ['N'])
    connect(normal_ws, '', upward, 'N')
    connect(upward, '', evaluate, 'UpwardFactor')

    texcoord = new_expression(function, u.MaterialExpressionTextureCoordinate)
    height_mask = add_custom(function, 'GrassDeform_HeightMask',
                             'return lerp(UV.y, 1.0 - UV.y, MaskFlip);',
                             u.CustomMaterialOutputType.CMOT_FLOAT1, ['UV', 'MaskFlip'])
    connect(texcoord, '', height_mask, 'UV')
    # GrassDeformMaskFlip is for packs whose card UVs put V=0 at the TIP instead of the ROOT:
    # flip it per material instance (0 = use V, 1 = use 1-V) without re-patching anything.
    connect(scalar_param(function, 'GrassDeformMaskFlip', 0.0), '', height_mask, 'MaskFlip')
    connect(height_mask, '', evaluate, 'HeightMask')

    # The UV mapping node needs the same window contract the subsystem uses to stamp: the MPC
    # centre and window size. SampleUV is then reused by the wavefront maths.
    connect(collection_param(function, 'Center', 'vector'), '', uv_node, 'Center')
    connect(collection_param(function, 'WindowSize', 'scalar'), '', uv_node, 'WindowSize')

    connect(uv_node, '', evaluate, 'SampleUV')
    connect(collection_param(function, 'WindowSize', 'scalar'), '', evaluate, 'WindowSize')
    connect(collection_param(function, 'WaveOrigin', 'vector'), '', evaluate, 'WaveOrigin')
    connect(collection_param(function, 'WorldTime', 'scalar'), '', evaluate, 'WorldTime')
    connect(collection_param(function, 'RegrowthSeconds', 'scalar'), '', evaluate, 'RegrowthSeconds')
    connect(collection_param(function, 'WaveSpeed', 'scalar'), '', evaluate, 'WaveSpeed')

    # Art-tuning parameters live on MF_GrassDeform so a material instance can override them.
    connect(scalar_param(function, 'BendScale', 28.0), '', evaluate, 'BendScale')
    connect(scalar_param(function, 'WaveWidth', 90.0), '', evaluate, 'WaveWidth')
    connect(scalar_param(function, 'MaxOffset', 34.0), '', evaluate, 'MaxOffset')
    connect(gate, '', evaluate, 'DeformSample')

    # --- outputs ------------------------------------------------------------------------------
    wpo_out = new_expression(function, u.MaterialExpressionFunctionOutput)
    wpo_out.set_editor_property('output_name', 'WPO')
    wpo_out.set_editor_property('sort_priority', 0)
    # FunctionOutput has exactly one input, the graph labels it "A", but the engine reports no name
    # for it -- UMaterialExpressionFunctionOutput::GetInputName() returns NAME_None
    # (MaterialExpressionFunctionOutput.h:61-64), and GetShortenPinName() passes NAME_None through
    # (MaterialGraphNode.cpp:597-599). Connecting by '' therefore selects input 0 through
    # GetExpressionInputByName()'s empty-name shortcut (MaterialEditingLibrary.cpp:52-55). Passing
    # the displayed label 'A' resolves to nothing and the connection is silently dropped.
    connect(evaluate, '', wpo_out, FUNCTION_OUTPUT_INPUT)

    flatten_out = new_expression(function, u.MaterialExpressionFunctionOutput)
    flatten_out.set_editor_property('output_name', 'Flatten')
    flatten_out.set_editor_property('sort_priority', 1)
    # Flatten rides on the gate's alpha, which is the raw R channel of the deform sample.
    flatten_split = add_custom(function, 'GrassDeform_FlattenOut', 'return Sample.r;',
                               u.CustomMaterialOutputType.CMOT_FLOAT1, ['Sample'])
    connect(gate, '', flatten_split, 'Sample')
    connect(flatten_split, '', flatten_out, FUNCTION_OUTPUT_INPUT)

    recompile_function(function)
    save(function, 'MF_GrassDeform')
    return function


# ---------------------------------------------------------------------------------------------
# Pass materials
#
# Each pass is a full-screen unlit quad drawn into the deform RT by
# UKismetRenderingLibrary::DrawMaterialToRenderTarget. The material reads the previous contents
# through the GrassDeformRT texture parameter (bound to the read side of the ping-pong pair) and
# writes the new state to Emissive. All three share the mask layout:
#   R = flatten 0..1, GB = bend dir encoded, A = impulse timestamp.
# ---------------------------------------------------------------------------------------------

# Radial falloff shared by the stamp passes: 1 at the centre, 0 at RadiusUV.
RADIAL_CODE = '''
float2 Delta = UV - Center;
float Distance = length(Delta);
float Falloff = 1.0 - saturate(Distance / max(Radius, 1e-5));
return Falloff * Falloff * (3.0 - 2.0 * Falloff);
'''

STAMP_CODE = '''
// R takes the max so a stamp can never erase an existing flatten value.
// A keeps the newer timestamp; GB only overwrite when the incoming event carries a direction.
float3 Previous = Old.rgb;
float  PreviousTime = Old.a;

float NewFlatten = Strength * Falloff;
float OutFlatten = max(Previous.r, NewFlatten);

float2 OutDir = Previous.gb;
if (DirStrength > 0.0)
{
    // BendDir arrives from the subsystem already encoded to 0..1 (the same encoding channels G
    // and B hold), so it is interpolated directly. Decoding it here would double-encode it.
    OutDir = lerp(Previous.gb, BendDir, saturate(DirStrength));
}

float OutTime = PreviousTime;
if (Timestamp > 0.0)
{
    OutTime = max(PreviousTime, Timestamp);
}

return float4(OutFlatten, OutDir, OutTime);
'''

FADE_CODE = '''
float Flatten = Old.r;
float2 Dir = Old.gb;
float Time = Old.a;

// Regrowth: R decays linearly, one step per fade pass. The subsystem sets FadeRate (the "Step"
// pin) to (1 / FadeHz) / RegrowthSeconds, so R reaches exactly 0 after RegrowthSeconds of wall
// time no matter what fade rate is selected. The rate is already folded in - do not scale here.
Flatten = max(0.0, Flatten - Step);
if (Flatten <= 0.0)
{
    Dir = float2(0.5, 0.5);
}

// An impulse older than the expiry window stops driving the wavefront at all.
if (Time > 0.0 && (WorldTime - Time) > ExpirySeconds)
{
    Time = 0.0;
}

return float4(Flatten, Dir, Time);
'''

RECENTER_CODE = '''
// UV-offset copy: the shifted source texture has already been sampled at (UV - Shift), so `Old`
// holds the texel that moves into this destination pixel.
// InRange is 1 when that source texel came from inside the previous window; outside it, the
// destination is written as "undisturbed grass" (zero flatten, neutral direction, no impulse)
// instead of clamping and smearing the border texel across the edge.
float4 Sampled = Old;
if (InRange < 0.5)
{
    Sampled = float4(0, 0.5, 0.5, 0);
}
return Sampled;
'''


def author_pass(material, kind):
    """Wire one pass material. `kind` is 'stamp', 'fade' or 'recenter'."""
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('two_sided', True)

    uv = MEL.create_material_expression(material, u.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('coordinate_index', 0)

    # Read side of the ping-pong pair, rebound by the subsystem before every DrawMaterial.
    previous = MEL.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D)
    previous.set_editor_property('parameter_name', PASS_SOURCE)
    connect(uv, '', previous, TEX_COORD_INPUT)

    if kind == 'stamp':
        falloff = add_custom(material, 'GrassDeform_StampFalloff', RADIAL_CODE,
                             u.CustomMaterialOutputType.CMOT_FLOAT1, ['UV', 'Center', 'Radius'])
        connect(uv, '', falloff, 'UV')
        # CenterUV is a vector parameter (set by the subsystem as (U, V, 0, 0)); the Custom node
        # pin is float2, so only the first two channels are consumed.
        connect(vector_param(material, 'CenterUV', (0.5, 0.5, 0.0, 0.0)), '', falloff, 'Center')
        connect(scalar_param(material, 'RadiusUV', 0.05), '', falloff, 'Radius')

        body = add_custom(material, 'GrassDeform_Stamp', STAMP_CODE,
                          u.CustomMaterialOutputType.CMOT_FLOAT4,
                          ['Old', 'Falloff', 'Strength', 'BendDir', 'DirStrength', 'Timestamp'])
        connect(previous, 'RGBA', body, 'Old')
        connect(falloff, '', body, 'Falloff')
        connect(scalar_param(material, 'Strength', 0.5), '', body, 'Strength')
        connect(vector_param(material, 'BendDir', (0.5, 0.5, 0.0, 0.0)), '', body, 'BendDir')
        connect(scalar_param(material, 'DirStrength', 0.0), '', body, 'DirStrength')
        connect(scalar_param(material, 'Timestamp', 0.0), '', body, 'Timestamp')
        connect_property(body, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
        return material

    if kind == 'fade':
        body = add_custom(material, 'GrassDeform_Fade', FADE_CODE,
                          u.CustomMaterialOutputType.CMOT_FLOAT4,
                          ['Old', 'Step', 'WorldTime', 'ExpirySeconds'])
        connect(previous, 'RGBA', body, 'Old')
        connect(scalar_param(material, 'FadeRate', 0.01), '', body, 'Step')
        connect(collection_param(material, 'WorldTime', 'scalar'), '', body, 'WorldTime')
        connect(scalar_param(material, 'ExpirySeconds', 30.0), '', body, 'ExpirySeconds')
        connect_property(body, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
        return material

    # recenter
    # ShiftUV is a *vector* parameter: the subsystem sets it as (dU, dV, 0, 0) because the window
    # can move on both axes. A single scalar would silently drop the Y component of the move.
    shift_node = add_custom(material, 'GrassDeform_RecenterUV',
                            'return UV - float2(ShiftUV);',
                            u.CustomMaterialOutputType.CMOT_FLOAT2, ['UV', 'ShiftUV'])
    connect(uv, '', shift_node, 'UV')
    connect(vector_param(material, 'ShiftUV', (0.0, 0.0, 0.0, 0.0)), '', shift_node, 'ShiftUV')

    shifted = MEL.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D)
    shifted.set_editor_property('parameter_name', PASS_SOURCE)
    connect(shift_node, '', shifted, TEX_COORD_INPUT)

    # Outside the source window the shifted sample would clamp and smear the border; mask it out.
    # The test runs on the *source* UV (the shifted one), because that is the texel actually being
    # read; an out-of-window read must be replaced by "undisturbed grass".
    in_range = add_custom(material, 'GrassDeform_RecenterMask',
                          'return (SourceUV.x >= 0.0 && SourceUV.x <= 1.0 && SourceUV.y >= 0.0 && SourceUV.y <= 1.0) ? 1.0 : 0.0;',
                          u.CustomMaterialOutputType.CMOT_FLOAT1, ['SourceUV'])
    connect(shift_node, '', in_range, 'SourceUV')
    body = add_custom(material, 'GrassDeform_Recenter', RECENTER_CODE,
                      u.CustomMaterialOutputType.CMOT_FLOAT4, ['Old', 'InRange'])
    connect(shifted, 'RGBA', body, 'Old')
    connect(in_range, '', body, 'InRange')
    connect_property(body, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    return material


def pass_version_tag(asset):
    """Read the version tag stamped on a pass material.

    UMaterial has no `Description` property (Material.h declares none; only UMaterialFunction does,
    MaterialFunction.h:57-58), so set_editor_property('description', ...) on a material raises.
    The tag therefore rides on the asset registry tag 'GrassDeformVersion', which survives a save
    and a reload and is what makes the rebuild-on-contract-change path converge.
    """
    try:
        return str(u.EditorAssetLibrary.get_metadata_tag(asset, VERSION_TAG_KEY))
    except Exception:
        return ''


def set_pass_version_tag(asset, tag):
    """Stamp the version tag onto a material asset (see pass_version_tag)."""
    return u.EditorAssetLibrary.set_metadata_tag(asset, VERSION_TAG_KEY, tag)


def build_passes():
    created = {}
    for name, kind in (('M_GrassDeformStamp', 'stamp'),
                       ('M_GrassDeformFade', 'fade'),
                       ('M_GrassDeformRecenter', 'recenter')):
        existing = load_optional(DEST + '/' + name)
        if existing is not None and PASS_VERSION_TAG in pass_version_tag(existing):
            REPORT['skipped'].append(name + ' (exists, ' + PASS_VERSION_TAG + ')')
            created[name] = existing
            continue

        if existing is not None:
            # Same reasoning as the function: rebuild rather than keep a graph authored against an
            # older parameter/channel contract (e.g. the "Old" source texture rename).
            log(name + ' exists but is not ' + PASS_VERSION_TAG + '; rebuilding its graph')
            MEL.delete_all_material_expressions(existing)
            material = existing
        else:
            material = create_asset(name, u.Material, u.MaterialFactoryNew())

        set_pass_version_tag(material, PASS_VERSION_TAG)
        author_pass(material, kind)
        MEL.recompile_material(material)
        save(material, name)
        created[name] = material
    return created


# ---------------------------------------------------------------------------------------------
# MA_Grass WPO patch
#
# mf-v4 note: the function sources WorldPos/UpwardFactor/HeightMask internally, so the call node
# installed here needs no input wiring. Enumerating MA_Grass expressions to re-wire an existing
# call node is impossible headlessly anyway: UMaterial.Expressions is protected from Python
# ("Property 'Expressions' ... is protected and cannot be read", measured 2026-09-26).
# ---------------------------------------------------------------------------------------------

def patch_grass_master(function):
    """Add MF_GrassDeform to MA_Grass' WPO chain after the existing wind, if that is safe.

    MaterialEditingLibrary's get_material_property_input_node/-output_name read from an *active
    material editor*. Under a headless commandlet there is no open editor, so the existing WPO
    chain usually cannot be inspected. When it cannot, the function is deliberately left
    unconnected rather than guessed at: a blind rewire of the shared grass master would drop the
    wind offset and break every grass instance in the project.
    """
    master = load_optional(GRASS_MASTER)
    if master is None:
        REPORT['manual'].append('MA_Grass not found at %s; MF_GrassDeform was left unconnected.'
                                % GRASS_MASTER)
        log('MA_Grass missing; skipping the WPO patch')
        return

    try:
        existing = MEL.get_material_property_input_node(master, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    except Exception as error:  # no active editor / API unavailable
        existing = None
        log('MA_Grass WPO input could not be read (%s)' % error)

    if existing is not None and existing.get_editor_property('desc') == 'GrassDeformWPOAdd':
        # The WPO add is already installed, and since mf-v4 the function sources
        # WorldPos/UpwardFactor/HeightMask INTERNALLY - the call node needs no input wiring (and
        # could not be re-wired headlessly anyway: UMaterial.Expressions is protected from
        # Python). The MF rebuild recompiled every referencing material through
        # UpdateMaterialFunction, so there is genuinely nothing to do here.
        REPORT['skipped'].append('MA_Grass WPO patch (already applied; mf-v4 inputs are internal to the function)')
        log('MA_Grass WPO patch present; nothing to do (inputs are sourced inside the MF)')
        return

    if existing is None:
        REPORT['manual'].append(
            'MA_Grass: the WPO input chain could not be inspected (MaterialEditingLibrary reads '
            'the property input from an active material editor, which a headless commandlet does '
            'not have). MF_GrassDeform was created but left UNCONNECTED so the existing wind WPO '
            'is untouched. Connect it by hand: see "M1 manual wiring" in '
            'Docs/WorldGeneration/grass-interaction-gpu-20260925.md.')
        log('MA_Grass WPO input could not be inspected; leaving MF_GrassDeform unconnected')
        return

    # The existing chain is readable: split it only after the MF call has been placed and its WPO
    # output confirmed, so a failure below cannot leave MA_Grass half-rewired. Everything that
    # mutates the master happens after this point, and any failure disconnects back to the
    # original chain.
    wpo_output = MEL.get_material_property_input_node_output_name(
        master, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    call = MEL.create_material_expression(master, u.MaterialExpressionMaterialFunctionCall)
    # Point the call node at MF_GrassDeform through the node's own BlueprintCallable setter.
    # MaterialEditingLibrary has no 'set_material_function_expression' (it does not exist in
    # MaterialEditingLibrary.h), but the node method itself is exposed:
    #   MaterialExpressionMaterialFunctionCall.h:157-158  UFUNCTION(BlueprintCallable) SetMaterialFunction
    # Assigning the 'material_function' property alone would not be enough: SetMaterialFunction()
    # routes through UpdateFromFunctionResource(), which rebuilds FunctionInputs/FunctionOutputs
    # (MaterialExpressionMaterialFunctionCall.h:160-164). Without that rebuild the node has no
    # 'WPO' output pin to connect, so the connection below would fail.
    if not call.set_material_function(function):
        REPORT['manual'].append('Could not place MF_GrassDeform inside MA_Grass; connect it manually.')
        log('Could not place MF_GrassDeform in MA_Grass')
        return

    add = MEL.create_material_expression(master, u.MaterialExpressionAdd)
    add.set_editor_property('desc', 'GrassDeformWPOAdd')

    if not MEL.connect_material_expressions(call, 'WPO', add, 'B'):
        # Nothing has been rewired yet, so just drop the two new nodes and keep the wind chain.
        MEL.delete_material_expression(master, add)
        MEL.delete_material_expression(master, call)
        REPORT['manual'].append(
            'MF_GrassDeform has no output named "WPO"; connect the WPO output to an Add node "B" '
            'manually. MA_Grass was left exactly as it was.')
        log('Could not connect the MF_GrassDeform WPO output; MA_Grass left untouched')
        return

    # existing wind stays exactly as authored; the deform offset is added after it.
    if not MEL.connect_material_expressions(existing, wpo_output, add, 'A'):
        MEL.delete_material_expression(master, add)
        MEL.delete_material_expression(master, call)
        REPORT['manual'].append('Could not re-attach the existing wind chain to the Add node; '
                                'MA_Grass was left exactly as it was.')
        log('Could not re-attach the existing wind chain; MA_Grass left untouched')
        return

    connect_property(add, '', u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    # mf-v4: the call node needs NO input wiring - WorldPos/UpwardFactor/HeightMask are sourced
    # inside the function itself.
    MEL.recompile_material(master)
    save(master, 'MA_Grass', bucket='patched')
    REPORT['patched'].append('MA_Grass WPO += MF_GrassDeform (added after the existing wind)')
    log('MA_Grass WPO patched: wind chain -> Add B=MF_GrassDeform.WPO')


# ---------------------------------------------------------------------------------------------

def main():
    global MPC, RT_ASSETS
    log('start ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ensure_directory(DEST)

    MPC = build_mpc()
    log('MPC_GrassDeform: %d scalars, %d vectors'
        % (len(MPC.get_editor_property('scalar_parameters')),
           len(MPC.get_editor_property('vector_parameters'))))

    # The RT asset pair must exist before the function is authored: its samplers take the two
    # assets as their texture-parameter defaults.
    RT_ASSETS = build_render_targets()

    function = build_function()
    passes = build_passes()
    log('pass materials present: ' + ', '.join(sorted(passes)))

    patch_grass_master(function)

    log('done. created=%s patched=%s skipped=%d manual=%d'
        % (REPORT['created'], REPORT['patched'], len(REPORT['skipped']), len(REPORT['manual'])))
    print('GRASS_DEFORM_M1_RESULT ' + repr(REPORT), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print('GRASS_DEFORM_M1_RESULT ' + repr(REPORT), flush=True)
        raise SystemExit(1)