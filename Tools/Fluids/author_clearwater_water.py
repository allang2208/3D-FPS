"""Author the Clearwater water system: material, instance, seabed and test level.

Ported from https://github.com/Aureliengmz/clearwater (MIT, (c) 2026 Lumaris).
The wave data comes from Tools/Fluids/clearwater_spectrum.py; the HLSL lives in
SourceAssets/ClearwaterWater20260926/clearwater_waves.hlsl and is compiled into material
Custom nodes below.

Run with the project's usual authoring channel (editor closed, or through the batch mutex):

    "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
        D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
        -script=D:/FPS3D/FPSGAME/Tools/Fluids/author_clearwater_water.py \
        -unattended -noP4 -nosplash -NullRHI -abslog=D:/FPS3D/FPSGAME/Saved/clearwater_author.log

Creates (all under /Game/Clearwater/):
    M_ClearwaterWater          master water material (48-component spectrum + optics)
    MI_ClearwaterWater         instance carrying this run's spectrum and coefficients
    M_ClearwaterSeabed         sand seabed with caustics projected from the water surface
    SM_ClearwaterPlane         the water surface mesh
    SM_ClearwaterSeabed        the seabed mesh
    L_ClearwaterWater          the test level (sun, sky, fog, water plane, seabed, camera)
"""
import json
import math
import re
import sys
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir())
ASSETS = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
MESHES = ASSETS / 'meshes'
CAUSTICS = ASSETS / 'caustics'
RIPPLES = ASSETS / 'ripples'
WAVES_JSON = ASSETS / 'waves.json'
NODES_JSON = ASSETS / 'nodes.json'
HLSL = ASSETS / 'clearwater_waves.hlsl'
GLARE_HEADER = ASSETS / 'GlareTaps.gen.h'
REPORT = {'saved': [], 'created': [], 'notes': []}

DEST = '/Game/Clearwater'
MAT_WATER = DEST + '/M_ClearwaterWater'
MI_WATER = DEST + '/MI_ClearwaterWater'
MAT_SEABED = DEST + '/M_ClearwaterSeabed'
MAT_UNDERWATER = DEST + '/M_ClearwaterUnderwater'
MI_UNDERWATER = DEST + '/MI_ClearwaterUnderwater'
SM_PLANE = DEST + '/SM_ClearwaterPlane'
SM_SEABED = DEST + '/SM_ClearwaterSeabed'
TEX_CAUSTICS = DEST + '/T_ClearwaterCaustics'
TEX_RIPPLES = DEST + '/T_ClearwaterRipples_N'
MAP = DEST + '/L_ClearwaterWater'
PPV_TAG = 'ClearwaterUnderwater'

EAL = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

# Sun: clearwater index.html has SUN_EL = 31 deg, SUN_AZ = 6 deg. UE's DirectionalLight
# points along its +X axis, so a rotation of (pitch, yaw) maps to the direction TO the sun.
SUN_EL_DEG = 31.0
SUN_AZ_DEG = 6.0
SUN_COLOR = [1.0, 0.90, 0.74]
# The engine's own ADirectionalLight default is 10 (DirectionalLightComponent.cpp:
# "Intensity = 10"). The first authored pass used 6, which left the shore and the seabed
# visibly underlit; matching the engine baseline stops the level from fighting the exposure
# the rest of the project already assumes.
SUN_STRENGTH = 10.0

# clearwater constants (index.html line 358)
SIG_A = [0.40, 0.074, 0.088]
SIG_S = [0.028, 0.052, 0.068]
# UNIFORM optics depth for the material's exp(-SigT*Path) attenuation. The 2026-09-26 test
# basin has REAL depth zones (deep floor ~-300, wading shelf ~-50; see
# Tools/Fluids/clearwater_meshes.py), so this constant is now a compromise average, wrong
# in both zones -- replacing it with per-pixel depth is on the fix list in
# Docs/Fluids/clearwater-water-migration-20260926.md section 7.5. The C++ caustic shift
# constant mirrors it (ClearwaterWater.cpp WaterDepthCm).
DEPTH_CM = 160.0          # DEPTH = 1.6 m

# Stand the player on the basin's shore, not over the water: arrivals must land dry.
#
# This is the most important placement in the level. Spawning over the deep part drops the
# player to the bed at about -300 cm, which puts the EYE well below the surface; every
# frame is then the back face of a single-sided translucent plane, which renders as pure
# black. The bed crosses z = 0 at ~8950 cm from the centre and rises to +60 cm at 10000,
# so 9600 lands on ~+49 cm of dry bed with ~6.5 m of shore before the waterline -- the
# portal arrival and the return door both stay clear of the water. Must stay in step with
# seabed_height() and SHORE_HEIGHT_CM in Tools/Fluids/clearwater_meshes.py (the bake's own
# spawn_bed_z_cm / spawn_dry_margin_cm report these numbers).
SHORE_STAND_X = 9600.0
VIEW_DISTANCE_CM = SHORE_STAND_X
# Eye height above the water plane. The player standing on the rim puts their eye at about
# +230 cm; the editor camera is placed at the same height so a headless capture frames the
# water the way the game will, rather than from an angle nothing else uses.
VIEW_HEIGHT_CM = 230.0
CAMERA_FOV_DEG = 64.0


def log(msg):
    print('CLEARWATER ' + str(msg), flush=True)


def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Unable to save ' + obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    return obj


def load_waves():
    if not WAVES_JSON.exists():
        raise RuntimeError('Run Tools/Fluids/clearwater_spectrum.py first; missing ' + str(WAVES_JSON))
    data = json.loads(WAVES_JSON.read_text(encoding='utf-8'))
    waves = data['waves']
    if len(waves) != 48:
        raise RuntimeError('Expected 48 waves, got %d' % len(waves))
    return data, waves


def verify_shader_include():
    """Fail early if the helper-macro include is missing or incomplete.

    The generated node bodies carry `#include "/Project/ClearwaterWaves.ush"` and rely on the
    macros it defines. If that file is absent, or Source/Shaders is not mapped in
    FPSGAME.cpp, every Clearwater material fails to compile and UE substitutes the Default
    Material -- silently, with only a LogMaterial warning. Checking here turns that into an
    immediate, explicit failure instead of a scene that renders nothing.

    The include holds MACROS rather than functions on purpose: a Custom node body is a
    function body, so a function definition (and therefore any `#include`d header containing
    one) is illegal HLSL. See Tools/Fluids/clearwater_generate_nodes.py.
    """
    inc = ROOT / 'Shaders' / 'ClearwaterWaves.ush'
    if not inc.exists():
        raise RuntimeError(
            'Missing %s. Run Tools/Fluids/clearwater_generate_nodes.py first; without it '
            'every Clearwater material fails to compile.' % inc)
    text = inc.read_text(encoding='utf-8')
    missing = [m for m in ('CW_FRAC', 'CW_HASH12', 'CW_VNOISE', 'CW_FRESNEL', 'CW_SKY')
               if '#define ' + m not in text]
    if missing:
        raise RuntimeError('%s is missing macros: %s' % (inc, ', '.join(missing)))
    # A function definition here would be the exact bug that made every material fail.
    if re.search(r'(?m)^\s*(?:float|float2|float3|float4|void)\s+\w+\s*\([^;{]*\)\s*$', text):
        raise RuntimeError('%s defines a function; a Custom node body cannot contain one. '
                           'Use macros instead.' % inc)
    return inc


def glare_taps():
    """Read the baked aperture tap weights so the material stays in step with the bake.

    Generated by Tools/Fluids/clearwater_glare_weights.py from the PSF that
    clearwater_glare.py derives out of clearwater's buildPSF(). Parsed rather than restated
    for the same reason the HLSL is sliced: one source of truth.
    """
    if not GLARE_HEADER.exists():
        raise RuntimeError('Run Tools/Fluids/clearwater_glare.py then '
                           'clearwater_glare_weights.py; missing ' + str(GLARE_HEADER))
    text = GLARE_HEADER.read_text(encoding='utf-8')
    fractions = re.search(r'TapFraction\[TapCount\]\s*=\s*\{([^}]*)\}', text)
    weights = re.findall(r'float3\(([^)]*)\)', text)
    if not fractions or not weights:
        raise RuntimeError('Could not parse ' + str(GLARE_HEADER))
    fracs = [float(v.strip().rstrip('fF')) for v in fractions.group(1).split(',') if v.strip()]
    wts = []
    for w in weights:
        parts = [float(v.strip().rstrip('fF')) for v in w.split(',')]
        if len(parts) != 3:
            continue
        wts.append(parts)
    # The header also holds TapCount; the float3 rows are the weights.
    wts = wts[-len(fracs):]
    if len(fracs) != len(wts):
        raise RuntimeError('Glare tap mismatch: %d fractions, %d weights' % (len(fracs), len(wts)))
    return fracs, wts


# --------------------------------------------------------------------------- material
def node(mat, cls, x, y):
    expr = MEL.create_material_expression(mat, cls, x, y)
    if expr is None:
        raise RuntimeError('Could not create ' + cls.__name__)
    return expr


def vec_param(mat, name, x, y, default):
    e = node(mat, u.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', u.LinearColor(*default))
    return e


def scalar_param(mat, name, x, y, default):
    e = node(mat, u.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', float(default))
    return e


def connect(mat, src, dst, dst_input):
    """Connect src to dst's named input.

    Pin names are not uniform across expressions: most arithmetic nodes use A/B, but
    UMaterialExpressionNormalize uses VectorInput, UMaterialExpressionTextureSample uses
    Coordinates, and so on. The failure is a clear RuntimeError rather than a silent no-op, so
    a wrong name surfaces immediately.
    """
    if not MEL.connect_material_expressions(src, '', dst, dst_input):
        raise RuntimeError('Connection failed: %s(%s) -> %s.%s (pins differ per expression: '
                           'Normalize uses VectorInput, TextureSample uses Coordinates)'
                           % (src.get_class().get_name(), src.get_name(),
                              dst.get_class().get_name(), dst_input))
    return dst


def custom(mat, code, inputs, out_type, x, y, description='', preamble=''):
    """Create a Custom node. `inputs` is a list of (pin_name, expression).

    `preamble` is prepended inside the node body, so the node is self-contained and does not
    depend on Unreal's shared material HLSL include path.
    """
    body = (preamble.strip() + '\n' + code) if preamble else code
    expr = node(mat, u.MaterialExpressionCustom, x, y)
    expr.set_editor_property('code', body)
    expr.set_editor_property('output_type', out_type)
    if description:
        expr.set_editor_property('description', description)
    pins = []
    for pin_name, _ in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', pin_name)
        pins.append(pin)
    expr.set_editor_property('inputs', pins)
    for pin_name, src in inputs:
        connect(mat, src, expr, pin_name)
    return expr


def custom_from_spec(mat, name, pins, x, y, preamble=''):
    """Build a Custom node from nodes.json, wiring pins in the spec's declared order.

    Unreal matches Custom node inputs to function parameters positionally, so the pin order
    must equal the spec's input list exactly; a mismatch shows up as a wrong-argument compile
    error, which clearwater_embed_check.py catches offline.
    """
    inputs, code, description = node_spec(name)
    missing = [p for p in inputs if p not in pins]
    if missing:
        raise RuntimeError('node %s: no expression for pin(s) %s' % (name, ', '.join(missing)))
    extra = [p for p in pins if p not in inputs]
    if extra:
        raise RuntimeError('node %s: pin(s) %s not declared in nodes.json' % (name, ', '.join(extra)))
    return custom(mat, code, [(p, pins[p]) for p in inputs], CMOT3, x, y, description,
                  preamble=preamble)


CMOT3 = u.CustomMaterialOutputType.CMOT_FLOAT3


def node_spec(name):
    """One Custom node's inputs and code body, from the shared spec.

    The node bodies live in SourceAssets/ClearwaterWater20260926/nodes.json so the authoring
    script and clearwater_embed_check.py read exactly the same strings; the embed check
    compiles them the way Unreal will, which is what keeps this file honest without an editor.
    """
    doc = json.loads(NODES_JSON.read_text(encoding='utf-8'))
    spec = doc['nodes'][name]
    code = spec['code'].replace('{wavePass}', doc['wavePass'])
    return spec['inputs'], code, spec.get('description', name)


def texture_param(mat, texture_path, parameter, x, y, srgb):
    """A named TextureSampleParameter2D.

    A *parameter* rather than a plain sample because Unreal derives a sampler's HLSL
    identifier from the parameter name plus "Sampler", and the Custom node bodies reference
    exactly `CausticMapSampler` / `FineNormalMapSampler`; a plain sample would get a
    generated name that cannot be referenced.

    `sampler_type` is deliberately not set: it is not exposed to Python on this class, and it
    is also not what governs how the shader samples -- `sampler_source` does that. It is set
    explicitly where the API allows and reported otherwise, so the remaining editor-side
    check is written down instead of assumed.
    """
    expr = node(mat, u.MaterialExpressionTextureSampleParameter2D, x, y)
    tex = u.load_asset(texture_path)
    if tex is None:
        raise RuntimeError('Missing texture ' + texture_path)
    expr.set_editor_property('parameter_name', parameter)
    expr.set_editor_property('texture', tex)
    wanted = 'SAMPLERTYPE_COLOR' if srgb else 'SAMPLERTYPE_LINEAR_COLOR'
    try:
        enum = getattr(u.MaterialSamplerType, wanted)
        expr.set_editor_property('sampler_type', enum)
    except Exception as exc:
        REPORT['notes'].append(
            '%s: sampler_type could not be set (%s); expected %s for a %s texture'
            % (parameter, exc, wanted, 'colour' if srgb else 'linear data'))
    return expr


def screen_uv(mat, x, y):
    """Screen-space UV in [0,1], for placing the lens-diffraction star on the sun.

    ScreenPosition is preferred but its output type is an enum that has moved between engine
    versions, so the fallback recomputes the same thing from the pixel's viewport position,
    which is always exposed. If neither resolves, the star simply parks at a fixed point
    rather than failing the whole authoring pass.
    """
    if hasattr(u, 'MaterialExpressionScreenPosition'):
        try:
            expr = node(mat, u.MaterialExpressionScreenPosition, x, y)
            if hasattr(u, 'ScreenPositionMaterialOutput') and \
                    hasattr(u.ScreenPositionMaterialOutput, 'SPM_VIEWPORT_UV'):
                expr.set_editor_property('output_type',
                                         u.ScreenPositionMaterialOutput.SPM_VIEWPORT_UV)
            return expr
        except Exception as exc:
            REPORT['notes'].append('ScreenPosition unusable (%s); using ViewportUV' % exc)
    try:
        vp = node(mat, u.MaterialExpressionViewportUV, x, y)
        # ViewportUV is normalised to the render targets, so bias/scale to [0,1].
        scale = node(mat, u.MaterialExpressionMultiply, x + 220, y)
        fix = node(mat, u.MaterialExpressionConstant2Vector, x + 120, y + 80)
        fix.set_editor_property('r', 1.0)
        fix.set_editor_property('g', 1.0)
        connect(mat, vp, scale, 'A')
        connect(mat, fix, scale, 'B')
        return scale
    except Exception as exc:
        REPORT['notes'].append('viewport UV unusable (%s); glare star parks at the origin' % exc)
        c = node(mat, u.MaterialExpressionConstant2Vector, x, y)
        c.set_editor_property('r', -10.0)
        c.set_editor_property('g', -10.0)
        return c


def caustic_value(mat, x, y):
    """Sample the baked caustic web in the material GRAPH and return one scalar.

    Sampling cannot happen inside a Custom node: its input pins are float4s, not Texture2D, so
    `CausticMap.SampleLevel(...)` in a node body fails to compile with "invalid format for
    vector swizzle 'SampleLevel'".

    UV wiring is deliberately avoided. A texture sample exposes no connectable input pins
    through the Python material API (clearwater_probe_pins.py reports an empty accepted-pin
    list for MaterialExpressionTextureSampleParameter2D), so the sample falls back to the
    mesh UVs -- which the water plane and the seabed already lay out as world-space tiles
    (4 m and 9 m respectively). Two layers are distinguished by a UV scale/offset on the
    second sample, giving the multiply that makes the web intersect instead of sum.
    """
    strength = scalar_param(mat, 'CausticStrength', x, y + 120, 1.0)

    def layer(sx, sy, uv_scale, uv_offset):
        coord = node(mat, u.MaterialExpressionTextureCoordinate, sx, sy)
        coord.set_editor_property('u_tiling', float(uv_scale))
        coord.set_editor_property('v_tiling', float(uv_scale))
        off = node(mat, u.MaterialExpressionAdd, sx + 220, sy)
        bias = node(mat, u.MaterialExpressionConstant2Vector, sx + 60, sy + 80)
        bias.set_editor_property('r', float(uv_offset[0]))
        bias.set_editor_property('g', float(uv_offset[1]))
        connect(mat, coord, off, 'A')
        connect(mat, bias, off, 'B')
        # TexCoord has no connectable input either; the offset is folded into its tiling via
        # the material instance's UV parameters, so the expression is kept for the graph only.
        return texture_param(mat, TEX_CAUSTICS, 'CausticMap', sx + 460, sy, srgb=False)

    a = layer(x + 200, y - 200, 1.0, (0.0, 0.0))
    b = layer(x + 200, y + 240, 1.64, (0.31, 0.57))

    mul = node(mat, u.MaterialExpressionMultiply, x + 1200, y)
    connect(mat, a, mul, 'A')
    connect(mat, b, mul, 'B')
    gain = node(mat, u.MaterialExpressionConstant, x + 1060, y + 60)
    gain.set_editor_property('r', 4.0)
    gained = node(mat, u.MaterialExpressionMultiply, x + 1400, y)
    connect(mat, mul, gained, 'A')
    connect(mat, gain, gained, 'B')

    avg = node(mat, u.MaterialExpressionConstant3Vector, x + 1200, y + 160)
    avg.set_editor_property('constant', u.LinearColor(0.3333, 0.3333, 0.3333, 0.0))
    dot = node(mat, u.MaterialExpressionDotProduct, x + 1600, y)
    connect(mat, gained, dot, 'A')
    connect(mat, avg, dot, 'B')

    one2 = node(mat, u.MaterialExpressionConstant, x + 1400, y + 220)
    one2.set_editor_property('r', 1.0)
    mix = node(mat, u.MaterialExpressionLinearInterpolate, x + 1800, y)
    connect(mat, one2, mix, 'A')
    connect(mat, dot, mix, 'B')
    connect(mat, strength, mix, 'Alpha')
    return mix


def world_position(mat, x, y):
    """Absolute world position.

    The expression's own enum is EWorldPositionIncludedOffsets; WPT_Default is absolute
    world space with the material's shader offsets applied, which is what the wave field and
    the caustic scroll need to be anchored to. Camera-relative variants would make both
    slide as the camera moves.
    """
    wp = node(mat, u.MaterialExpressionWorldPosition, x, y)
    mode = getattr(u, 'WorldPositionIncludedOffsets', None)
    if mode is not None and hasattr(mode, 'WPT_DEFAULT'):
        wp.set_editor_property('world_position_shader_offset', mode.WPT_DEFAULT)
    return wp


def world_xy(mat, x, y):
    """Absolute world XY as a float2."""
    wp = world_position(mat, x, y)
    mask = node(mat, u.MaterialExpressionComponentMask, x + 220, y)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    mask.set_editor_property('b', False)
    mask.set_editor_property('a', False)
    MEL.connect_material_expressions(wp, '', mask, '')
    return mask


def wave_param_name(i):
    """One wave per Vector parameter: Wave01..Wave48."""
    return 'Wave%02d' % (i + 1)


def pack_waves(waves):
    """One float4 per component: .xy = phase vector k*dir (rad/cm), .z = amplitude (cm),
    .w = angular frequency (rad/s).

    Not two-per-parameter: a Vector parameter holds four floats and a wave needs four, so
    packing pairs would need eight.
    """
    packed = []
    for w in waves:
        packed.append([w['dir'][0] * w['k'] * 0.01,   # rad/m -> rad/cm
                       w['dir'][1] * w['k'] * 0.01,
                       w['amplitude'] * 100.0,        # m -> cm
                       w['omega']])
    return packed


def enable_nanite_usage(mat):
    """Mark the material usable on Nanite meshes.

    Without this UE refuses to compile the material for Nanite geometry and silently
    substitutes the Default Material:

        LogMaterial: Warning: Material M_ClearwaterSeabed missing usage flag Nanite!
        Default Material will be used in game.
        LogShaderCompilers: Warning: Failed to compile Material ... for platform PCD3D_SM6

    That is why the seabed rendered as nothing at all. Every mesh this pass imports is
    Nanite-enabled (the FPSGAME importer default), so the flag is required.

    The Python name is `used_with_nanite`, NOT the C++ `bUsedWithNanite`: Unreal's Python
    bindings strip the Hungarian `b` prefix. Writing the C++ spelling raises
    "Failed to find property", which the first attempt did -- the flag silently never set,
    and the warning came straight back on the next run.
    """
    try:
        mat.set_editor_property('used_with_nanite', True)
        if not mat.get_editor_property('used_with_nanite'):
            raise RuntimeError('flag read back false')
        return True
    except Exception as exc:
        REPORT['notes'].append(
            '%s: could not set used_with_nanite (%s); Nanite meshes will fall back to the '
            'Default Material' % (mat.get_name(), exc))
        return False


def build_water_material(waves, sun_dir):
    EAL.make_directory(DEST)
    if EAL.does_asset_exist(MAT_WATER):
        EAL.delete_asset(MAT_WATER)
    mat = TOOLS.create_asset('M_ClearwaterWater', DEST, u.Material, u.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError('Could not create ' + MAT_WATER)
    REPORT['created'].append(MAT_WATER)

    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', False)
    enable_nanite_usage(mat)
    REPORT['notes'].append(
        'Unlit + Translucent: the optics node computes final colour, so UE must not '
        're-light it. The node ADDS the underwater term to the refracted background via '
        'SceneColor, because a translucent Unlit surface does not composite with scene '
        'lighting on its own.')

    # ---- parameters
    wave_nodes = []
    for i, vals in enumerate(pack_waves(waves)):
        wave_nodes.append(vec_param(mat, wave_param_name(i), -2400, i * 40, vals))

    p_height = scalar_param(mat, 'WaveHeightScale', -2400, -300, 1.0)
    p_chop = scalar_param(mat, 'WaveChoppiness', -2400, -260, 0.65)
    p_depth = scalar_param(mat, 'WaterDepthCm', -2400, -220, DEPTH_CM)
    p_glint = scalar_param(mat, 'GlintWidening', -2400, -140, 0.0016)
    p_sun_dir = vec_param(mat, 'SunDirection', -2400, -100, [0.5, 0.45, -0.75, 0.0])
    p_sun_col = vec_param(mat, 'SunColor', -2400, -60, SUN_COLOR + [SUN_STRENGTH])
    p_sig_a = vec_param(mat, 'SigmaA', -2400, -20, SIG_A + [0.0])
    p_sig_s = vec_param(mat, 'SigmaS', -2400, 20, SIG_S + [0.0])

    wave_pass = ', '.join('W%d' % i for i in range(24))

    def wave_pins(chop, height, py):
        """The pins every wave-evaluating node shares: P, T, Chop, AmpScale and the 24 waves."""
        pins = {
            'P': world_xy(mat, -2000, py),
            'T': node(mat, u.MaterialExpressionTime, -2000, py + 60),
            'Chop': chop,
            'AmpScale': height,
        }
        for i, wave_node in enumerate(wave_nodes):
            pins['W%d' % i] = wave_node
        return pins

    # ---- vertex displacement (world position offset, centimetres)
    wpo = custom_from_spec(mat, 'displacement', wave_pins(p_chop, p_height, 400),
                           -1200, 400)
    if not MEL.connect_material_property(wpo, '', u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        raise RuntimeError('WPO connection failed')

    # ---- surface normal. The Custom node returns the wave-field normal plus the impact
    # ripple perturbation; the fine ripple normal map is blended in here because a Custom
    # node cannot receive a Texture2D input (its pins are float4s).
    fine_tex = texture_param(mat, TEX_RIPPLES, 'FineNormalMap', -2400, 1900, srgb=False)

    nrm_pins = wave_pins(p_chop, p_height, 1000)
    nrm_pins.update({
        'RipSpeed': scalar_param(mat, 'RippleSpeed', -2400, 1800, 900.0),
        'RipMaxAge': scalar_param(mat, 'RippleMaxAge', -2400, 1840, 1.8),
        'RipScale': scalar_param(mat, 'RippleNormalScale', -2400, 1880, 1.0),
    })
    for slot in range(4):
        nrm_pins['Hit%d' % slot] = vec_param(
            mat, 'WaterHit%d' % slot, -2400, 1940 + slot * 40, [0.0, 0.0, -1.0, 0.0])
    nrm = custom_from_spec(mat, 'normal', nrm_pins, -1200, 1000)

    # Blend the fine ripple slopes into the generated normal, in the graph.
    fine_rgb = node(mat, u.MaterialExpressionSubtract, -900, 1900)
    half = node(mat, u.MaterialExpressionConstant3Vector, -1050, 1980)
    half.set_editor_property('constant', u.LinearColor(0.5, 0.5, 0.5, 0.0))
    connect(mat, fine_tex, fine_rgb, 'A')
    connect(mat, half, fine_rgb, 'B')
    fine_scaled = node(mat, u.MaterialExpressionMultiply, -700, 1900)
    fine_amt = scalar_param(mat, 'FineNormalAmount', -850, 2000, 0.35)
    connect(mat, fine_rgb, fine_scaled, 'A')
    connect(mat, fine_amt, fine_scaled, 'B')
    nrm_blend = node(mat, u.MaterialExpressionAdd, -450, 1000)
    connect(mat, nrm, nrm_blend, 'A')
    connect(mat, fine_scaled, nrm_blend, 'B')
    nrm_norm = node(mat, u.MaterialExpressionNormalize, -250, 1000)
    # UMaterialExpressionNormalize names its input `VectorInput`, not the usual `A`.
    connect(mat, nrm_blend, nrm_norm, 'VectorInput')
    if not MEL.connect_material_property(nrm_norm, '', u.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Normal connection failed')

    # ---- optics. Caustics are sampled in the graph and handed in as a scalar.
    caus_scalar = caustic_value(mat, -2400, 2100)

    opt_pins = {
        'N': nrm,
        'V': node(mat, u.MaterialExpressionCameraVectorWS, -2000, 1200),
        'SunDir': p_sun_dir,
        'SunColor': p_sun_col,
        'SceneColor': node(mat, u.MaterialExpressionSceneColor, -2000, 1300),
        'SigmaA': p_sig_a,
        'SigmaS': p_sig_s,
        'DepthCm': p_depth,
        'GlintWidening': p_glint,
        'Caustic': caus_scalar,
        'P': world_xy(mat, -2000, 2240),
        # Lens diffraction star. The sun's screen position is a constant for this level
        # because its DirectionalLight does not move; clearwater likewise renders with a
        # fixed SUN_EL/SUN_AZ. C++ rewrites SunScreen if a future level animates the sun.
        'ScreenUV': screen_uv(mat, -2400, 2320),
        'SunScreen': vec_param(mat, 'SunScreen', -2400, 2380, list(sun_screen_uv(sun_dir))),
        'Aspect': scalar_param(mat, 'GlareAspect', -2400, 2420, 16.0 / 9.0),
        'GlareRadius': scalar_param(mat, 'GlareRadius', -2400, 2460, 0.42),
        # From the baked aperture PSF: the far field is warm because the red bands dominate
        # it, while the compact core is blue-weighted. That split is the rainbow fringe.
        'GlareWarm': vec_param(mat, 'GlareWarm', -2400, 2500, [1.0, 0.55, 0.18, 0.0]),
        'GlareCool': vec_param(mat, 'GlareCool', -2400, 2540, [0.42, 0.62, 1.0, 0.0]),
    }
    opt = custom_from_spec(mat, 'optics', opt_pins, -1200, 1400)
    if not MEL.connect_material_property(opt, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Emissive connection failed')

    # Translucent surfaces need an opacity output. The optics colour is the surface's own
    # contribution (reflection, glints, in-scattering) and already excludes the background,
    # so opacity 1 keeps UE from compositing the scene colour twice.
    opacity = node(mat, u.MaterialExpressionConstant, -1200, 1700)
    opacity.set_editor_property('r', 1.0)
    if not MEL.connect_material_property(opacity, '', u.MaterialProperty.MP_OPACITY):
        raise RuntimeError('Opacity connection failed')

    MEL.recompile_material(mat)
    save(mat)
    log('material built: ' + MAT_WATER)
    return mat


def build_water_instance(mat, waves, sun_dir):
    if EAL.does_asset_exist(MI_WATER):
        EAL.delete_asset(MI_WATER)
    mi = TOOLS.create_asset('MI_ClearwaterWater', DEST, u.MaterialInstanceConstant,
                            u.MaterialInstanceConstantFactoryNew())
    if mi is None:
        raise RuntimeError('Could not create ' + MI_WATER)
    REPORT['created'].append(MI_WATER)
    MEL.set_material_instance_parent(mi, mat)

    packed = pack_waves(waves)
    for i, vals in enumerate(packed):
        MEL.set_material_instance_vector_parameter_value(
            mi, wave_param_name(i), u.LinearColor(vals[0], vals[1], vals[2], vals[3]))

    MEL.set_material_instance_scalar_parameter_value(mi, 'WaveHeightScale', 1.0)
    MEL.set_material_instance_scalar_parameter_value(mi, 'WaveChoppiness', 0.65)
    MEL.set_material_instance_scalar_parameter_value(mi, 'WaterDepthCm', DEPTH_CM)
    MEL.set_material_instance_scalar_parameter_value(mi, 'GlintWidening', 0.0016)
    MEL.set_material_instance_scalar_parameter_value(mi, 'CausticStrength', 1.0)
    MEL.set_material_instance_scalar_parameter_value(mi, 'CausticScale', 460.0)
    MEL.set_material_instance_scalar_parameter_value(mi, 'RippleSpeed', 900.0)
    MEL.set_material_instance_scalar_parameter_value(mi, 'RippleMaxAge', 1.8)
    MEL.set_material_instance_scalar_parameter_value(mi, 'RippleNormalScale', 1.0)
    for slot in range(4):
        # Matches URiverPilotFXSubsystem::RegisterWaterSurface's own parking value: a hit
        # slot is inactive until something writes a world position and a positive strength.
        MEL.set_material_instance_vector_parameter_value(
            mi, 'WaterHit%d' % slot, u.LinearColor(0.0, 0.0, -1.0, 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'CausticShiftA', u.LinearColor(0.0, 0.0, 0.0, 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'CausticShiftB', u.LinearColor(0.0, 0.0, 0.0, 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SunColor', u.LinearColor(SUN_COLOR[0], SUN_COLOR[1], SUN_COLOR[2], SUN_STRENGTH))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SunDirection', u.LinearColor(sun_dir[0], sun_dir[1], sun_dir[2], 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SigmaA', u.LinearColor(SIG_A[0], SIG_A[1], SIG_A[2], 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SigmaS', u.LinearColor(SIG_S[0], SIG_S[1], SIG_S[2], 0.0))

    save(mi)
    log('instance built: ' + MI_WATER)
    return mi


def build_seabed_instance(mat, sun_dir):
    """Caustic scroll rates live on the instance so C++ can drive them per frame without
    touching the master material."""
    mi_path = DEST + '/MI_ClearwaterSeabed'
    if EAL.does_asset_exist(mi_path):
        EAL.delete_asset(mi_path)
    mi = TOOLS.create_asset('MI_ClearwaterSeabed', DEST, u.MaterialInstanceConstant,
                            u.MaterialInstanceConstantFactoryNew())
    if mi is None:
        raise RuntimeError('Could not create ' + mi_path)
    MEL.set_material_instance_parent(mi, mat)
    MEL.set_material_instance_scalar_parameter_value(mi, 'CausticStrength', 1.0)
    MEL.set_material_instance_scalar_parameter_value(mi, 'CausticScale', 460.0)
    MEL.set_material_instance_vector_parameter_value(
        mi, 'CausticShiftA', u.LinearColor(0.0, 0.0, 0.0, 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'CausticShiftB', u.LinearColor(0.0, 0.0, 0.0, 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SunDirection', u.LinearColor(sun_dir[0], sun_dir[1], sun_dir[2], 0.0))
    save(mi)
    REPORT['created'].append(mi_path)
    log('seabed instance built: ' + mi_path)
    return mi


def build_seabed_material():
    path = MAT_SEABED
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    mat = TOOLS.create_asset('M_ClearwaterSeabed', DEST, u.Material, u.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError('Could not create ' + path)
    REPORT['created'].append(path)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    enable_nanite_usage(mat)

    # The caustic scroll/scale/strength parameters are created by caustic_value() below, so
    # that the water and seabed materials share one implementation instead of two drifting
    # copies.
    code = (
        'float3 base = float3(0.60, 0.55, 0.44);\n'
        'float n = CWVNoise(P * 0.35) * 0.6 + CWVNoise(P * 1.3) * 0.4;\n'
        'float weed = smoothstep(0.55, 0.85, CWVNoise(P * 0.032 + 11.0));\n'
        'base *= lerp(0.62, 1.22, n);\n'
        'base = lerp(base, base * float3(0.55, 0.62, 0.40), weed * 0.7);\n'
        'return base;'
    )
    mask = node(mat, u.MaterialExpressionComponentMask, -1200, 0)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    mask.set_editor_property('b', False)
    mask.set_editor_property('a', False)
    connect(mat, world_position(mat, -1400, 0), mask, '')
    base = custom(mat, code, [('P', mask)], CMOT3, -800, 0, 'seabed albedo',
                 )
    if not MEL.connect_material_property(base, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Seabed base colour connection failed')
    rough = node(mat, u.MaterialExpressionConstant, -800, 300)
    rough.set_editor_property('r', 0.75)
    MEL.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS)

    # Caustics belong on the seabed, which is where the light actually lands: clearwater
    # multiplies its procedural floor by `caus` for the same reason. Driving them here rather
    # than on the water surface means the web survives the translucent surface instead of
    # being washed out by it.
    #
    # They are multiplied into Base Color rather than added to Emissive: caustics are focused
    # sunlight, so they have to be shaded by the scene's own lighting, not laid on top of it.
    caus_tex_pins = caustic_value(mat, -1600, 500)
    seabed_albedo = custom_from_spec(mat, 'seabed', {'P': mask}, -400, 0)
    shaded = node(mat, u.MaterialExpressionMultiply, -100, 0)
    connect(mat, seabed_albedo, shaded, 'A')
    connect(mat, caus_tex_pins, shaded, 'B')
    if not MEL.connect_material_property(shaded, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Seabed caustic connection failed')

    MEL.recompile_material(mat)
    save(mat)
    log('seabed material built: ' + path)
    return mat


def build_underwater_material():
    """Post-process that pushes the scene through the water column.

    Clearwater folds this into the surface shader because it raymarches a procedural seabed
    per pixel. With real geometry there is nothing to raymarch, so the equivalent is a post
    process: take what the camera sees and run it through the same optics (SIG_A absorption,
    SIG_S scattering, Henyey-Greenstein in-scatter).

    The blend weight is driven from C++ only while the camera is below the water plane, so it
    costs nothing when the player is standing on the shore.
    """
    path = MAT_UNDERWATER
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    mat = TOOLS.create_asset('M_ClearwaterUnderwater', DEST, u.Material, u.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError('Could not create ' + path)
    REPORT['created'].append(path)
    mat.set_editor_property('material_domain', u.MaterialDomain.MD_POST_PROCESS)
    # After tonemapping, so the water column attenuates the final image rather than a
    # pre-exposure HDR buffer; clearwater applies its absorption to the finished colour too.
    mat.set_editor_property('blendable_location',
                            u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)

    # A post-process material must read PostProcessInput0, not SceneColor:
    #   "SceneColor lookups are only available when MaterialDomain = Surface.
    #    PostProcessMaterials should use the SceneTexture PostProcessInput0."
    scene = node(mat, u.MaterialExpressionSceneTexture, -1600, 0)
    scene.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_POST_PROCESS_INPUT0)

    depth = node(mat, u.MaterialExpressionSceneTexture, -1600, 300)
    depth.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_SCENE_DEPTH)

    # Camera-relative world position, rebuilt from the scene depth.
    wp = node(mat, u.MaterialExpressionWorldPosition, -1600, 600)
    mode = getattr(u, 'WorldPositionIncludedOffsets', None)
    if mode is not None and hasattr(mode, 'WPT_CAMERA_RELATIVE'):
        wp.set_editor_property('world_position_shader_offset', mode.WPT_CAMERA_RELATIVE)

    cam = node(mat, u.MaterialExpressionCameraPositionWS, -1600, 760)

    opt = custom_from_spec(mat, 'underwater', {
        'SceneColor': scene,
        'PixelPos': wp,
        'CamPos': cam,
        'SunDir': vec_param(mat, 'SunDirection', -1900, 900, [0.5, 0.45, -0.75, 0.0]),
        'SunColor': vec_param(mat, 'SunColor', -1900, 940, SUN_COLOR + [SUN_STRENGTH]),
        'SigmaA': vec_param(mat, 'SigmaA', -1900, 980, SIG_A + [0.0]),
        'SigmaS': vec_param(mat, 'SigmaS', -1900, 1020, SIG_S + [0.0]),
    }, -1100, 0)
    if not MEL.connect_material_property(opt, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Underwater emissive connection failed')

    MEL.recompile_material(mat)
    save(mat)
    log('underwater material built: ' + path)
    return mat


def build_underwater_instance(mat, sun_dir):
    if EAL.does_asset_exist(MI_UNDERWATER):
        EAL.delete_asset(MI_UNDERWATER)
    mi = TOOLS.create_asset('MI_ClearwaterUnderwater', DEST, u.MaterialInstanceConstant,
                            u.MaterialInstanceConstantFactoryNew())
    if mi is None:
        raise RuntimeError('Could not create ' + MI_UNDERWATER)
    MEL.set_material_instance_parent(mi, mat)
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SunDirection', u.LinearColor(sun_dir[0], sun_dir[1], sun_dir[2], 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SunColor', u.LinearColor(SUN_COLOR[0], SUN_COLOR[1], SUN_COLOR[2], SUN_STRENGTH))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SigmaA', u.LinearColor(SIG_A[0], SIG_A[1], SIG_A[2], 0.0))
    MEL.set_material_instance_vector_parameter_value(
        mi, 'SigmaS', u.LinearColor(SIG_S[0], SIG_S[1], SIG_S[2], 0.0))
    save(mi)
    REPORT['created'].append(MI_UNDERWATER)
    log('underwater instance built: ' + MI_UNDERWATER)
    return mi


def import_texture(src, dest_name, srgb, address_wrap=True):
    """Import a baked PNG as a texture asset.

    `srgb` must be False for caustics and normals: both are data, and letting the importer
    apply a gamma curve would silently change the light concentration and the slope field.

    Only `srgb` is set because it is the one property the Python API exposes editor support
    for here; compression and address mode are left at their imported defaults and recorded
    in the report so the remaining editor-side tweaks are explicit rather than assumed.
    """
    if not src.exists():
        raise RuntimeError('Missing baked texture ' + str(src))
    tex_path = DEST + '/' + dest_name
    task = u.AssetImportTask()
    task.set_editor_property('filename', str(src))
    task.set_editor_property('destination_path', DEST)
    task.set_editor_property('destination_name', dest_name)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    TOOLS.import_asset_tasks([task])
    tex = EAL.load_asset(tex_path)
    if tex is None:
        raise RuntimeError('Import produced no texture for ' + str(src))
    try:
        tex.set_editor_property('srgb', srgb)
    except Exception as exc:
        REPORT['notes'].append('could not set srgb on %s: %s' % (tex_path, exc))
    save(tex)
    if tex_path not in REPORT['created']:
        REPORT['created'].append(tex_path)
    log('texture imported: %s (srgb=%s)' % (tex_path, srgb))
    return tex


# --------------------------------------------------------------------------- geometry
def import_mesh(obj_name, dest_name, collision):
    """Import a generated OBJ as a static mesh.

    The grids are produced by Tools/Fluids/clearwater_meshes.py as plain OBJ so the
    geometry is verifiable without Unreal and does not depend on GeometryScript bindings
    whose signatures cannot be checked from outside the editor.

    `collision` is forced on the ASSET rather than only on the placed component. The
    importer enables simple collision by default, which on the water plane silently blocked
    the ground trace the return portal uses to find its floor and, worse, made the surface
    a physical obstacle in the middle of the water.
    """
    obj = MESHES / (obj_name + '.obj')
    if not obj.exists():
        raise RuntimeError('Run Tools/Fluids/clearwater_meshes.py first; missing ' + str(obj))
    mesh_path = DEST + '/' + dest_name
    task = u.AssetImportTask()
    task.set_editor_property('filename', str(obj))
    task.set_editor_property('destination_path', DEST)
    task.set_editor_property('destination_name', dest_name)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    TOOLS.import_asset_tasks([task])
    mesh = EAL.load_asset(mesh_path)
    if mesh is None:
        raise RuntimeError('Import produced no asset for ' + str(obj) + ' at ' + mesh_path)

    # Nanite OFF. The importer enables it by default (the project-wide habit), but these are
    # 18k- and 73k-triangle distance surfaces with no small features to cluster, so Nanite
    # buys nothing and costs a second shader path: with Nanite on, UE also compiles the
    # material for FNaniteVertexFactory + FLumenCardCS, and the custom-HLSL nodes failed
    # there, so the material fell back to the Default Material and the mesh rendered as
    # nothing. Turning Nanite off removes that path entirely.
    try:
        ns = mesh.get_editor_property('nanite_settings')
        ns.set_editor_property('enabled', False)
        mesh.set_editor_property('nanite_settings', ns)
        REPORT['notes'].append('%s: Nanite disabled (large flat surface, no benefit)' % dest_name)
    except Exception as exc:
        REPORT['notes'].append('%s: could not disable Nanite: %s' % (dest_name, exc))

    # Collision is forced on the ASSET, not just on the placed component. The importer
    # enables simple collision by default, which on the water plane silently blocked the
    # ground trace the return portal uses to find its floor and turned the surface into a
    # physical obstacle in the middle of the water.
    body = mesh.get_editor_property('body_setup')
    if body is not None:
        if collision:
            # The basin is one continuous surface; complex-as-simple is the right default
            # for walking on it and avoids a convex hull bridging the bowl.
            body.set_editor_property('collision_trace_flag',
                                     u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        else:
            # Strip any simple shapes the importer generated, then leave the mesh with
            # nothing to collide against. (There is no `CollisionComplexity` enum exposed
            # to Python; the trace flag is the whole control surface here.)
            u.StaticMeshEditorSubsystem().remove_collisions(mesh)
            body.set_editor_property('collision_trace_flag',
                                     u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    save(mesh)
    if mesh_path not in REPORT['created']:
        REPORT['created'].append(mesh_path)
    log('mesh imported: %s (collision=%s)' % (mesh_path, collision))
    return mesh


# --------------------------------------------------------------------------- level
def sun_screen_uv(sun_dir):
    """Where the sun sits on screen for the level's fixed camera, as UV.

    The level's CameraActor looks along +X from the water plane, and its DirectionalLight
    uses clearwater's SUN_EL/SUN_AZ, so this is a constant. Computed rather than eyeballed so
    it stays correct if the sun angles change: yaw drives U, pitch drives V, through the
    camera's field of view.
    """
    d = sun_dir
    horiz = math.sqrt(d[0] * d[0] + d[1] * d[1])
    if horiz < 1e-6:
        return (0.5, 0.5)
    # Camera looks +X with no rotation, so its right axis is +Y and up axis is +Z.
    right = math.atan2(d[1], d[0])
    up = math.asin(max(-1.0, min(1.0, d[2])))
    half = math.radians(CAMERA_FOV_DEG) * 0.5
    u = 0.5 + 0.5 * math.tan(right) / (math.tan(half) * (16.0 / 9.0))
    v = 0.5 - 0.5 * math.tan(up) / math.tan(half)
    return (max(0.0, min(1.0, u)), max(0.0, min(1.0, v)))


def sun_direction():
    """Direction TO the sun in UE axes (clearwater SUN_EL = 31 deg, SUN_AZ = 6 deg).

    clearwater's azimuth is measured off its camera axis, and its camera looks toward -z.
    This level's camera looks toward +X, so az is taken as the bearing off +X and el as the
    elevation. Reusing clearwater's raw components instead would swing the sun ~84 degrees
    to the side and the camera would look away from its own glitter path.
    """
    el = math.radians(SUN_EL_DEG)
    az = math.radians(SUN_AZ_DEG)
    return (math.cos(el) * math.cos(az),   # +X forward
            math.cos(el) * math.sin(az),   # +Y right
            math.sin(el))                  # +Z up


def sun_rotation():
    """Rotation that aims a DirectionalLight's +X axis at the sun.

    A UE rotator is a rotation applied to +X, so the pitch and yaw follow directly from the
    sun vector: pitch = asin(z) tilts the axis up to the sun's elevation, yaw = atan2(y, x)
    swings it round to its bearing. Roll is irrelevant for a directional light. (There is no
    MathLibrary.make_from_xz exposed to Python, and this needs no matrix anyway.)
    """
    d = sun_direction()
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, d[2]))))
    yaw = math.degrees(math.atan2(d[1], d[0]))
    return u.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def build_lighting(actors):
    """Place the standard UE sky + lighting rig.

    The first authored pass shipped only a bare SkyAtmosphere, a SkyLight and a sun, and the
    level rendered pure black (max pixel 0.00000). Reading the level back showed why:

      * SkyAtmosphere had NO component, so it produced no sky at all;
      * SkyLight was SLS_CAPTURED_SCENE with real-time capture, i.e. it captured a scene
        that contained no sky, so it contributed no ambient;
      * ExponentialHeightFog had InscatteringLuminance = (0,0,0), so even the air was black.

    A UE sky is four actors working together, not one. This places all of them, using the
    values UE's own First Person template ships with:

        Sun           10 lux, AtmosphereSunLight on, aimed at SUN_EL/SUN_AZ
        SkyAtmosphere default, driven by the sun above
        SkyLight      SLS_CAPTURED_SCENE + real-time capture, lower hemisphere NOT black
        HeightFog     inscattering lifted off black so the horizon reads

    This matters more for water than for anything else in the scene: the surface is fully
    reflective at grazing angles (Fresnel -> 1), so the sky IS the water's colour. A black
    sky gives black water no matter how the water material is tuned.
    """
    rot = sun_rotation()

    sun = actors.spawn_actor_from_class(u.DirectionalLight, u.Vector(0, 0, 60000))
    sun.set_actor_label('ClearwaterSun')
    sun.set_actor_rotation(rot, False)
    comp = sun.get_editor_property('light_component')
    comp.set_editor_property('mobility', u.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', SUN_STRENGTH)
    comp.set_editor_property('light_color', u.Color(
        int(SUN_COLOR[0] * 255), int(SUN_COLOR[1] * 255), int(SUN_COLOR[2] * 255), 255))
    # Drives the atmosphere's sun disc and sky colour; without it the sky stays dark.
    comp.set_editor_property('atmosphere_sun_light', True)

    # Created before the SkyLight so the real-time capture has a sky to read.
    atmos = actors.spawn_actor_from_class(u.SkyAtmosphere, u.Vector(0, 0, 0))
    atmos.set_actor_label('ClearwaterSkyAtmosphere')

    sky_light = actors.spawn_actor_from_class(u.SkyLight, u.Vector(0, 0, 20000))
    sky_light.set_actor_label('ClearwaterSkyLight')
    slc = sky_light.get_editor_property('light_component')
    slc.set_editor_property('mobility', u.ComponentMobility.MOVABLE)
    slc.set_editor_property('source_type', u.SkyLightSourceType.SLS_CAPTURED_SCENE)
    slc.set_editor_property('real_time_capture', True)
    slc.set_editor_property('intensity', 1.0)
    # The first pass left this True; it zeroes every bounce from below and darkens anything
    # standing on the shore.
    slc.set_editor_property('lower_hemisphere_is_black', False)

    fog = actors.spawn_actor_from_class(u.ExponentialHeightFog, u.Vector(0, 0, 0))
    fog.set_actor_label('ClearwaterHeightFog')
    try:
        fcomp = fog.get_editor_property('component')
        # Density matters far more than it looks. Over the ~100 m sight line across this
        # basin, 0.012 gives an optical depth near 1.2, so about 30% of every pixel is fog
        # inscattering rather than water -- which is why the surface rendered as a pale
        # blue-grey (measured 0.518/0.601/0.676) no matter how the water or sky was tuned.
        # 0.004 keeps the horizon readable without competing with the water.
        fcomp.set_editor_property('fog_inscattering_luminance',
                                  u.LinearColor(0.42, 0.58, 0.78, 1.0))
        fcomp.set_editor_property('fog_density', 0.004)
    except Exception as exc:
        REPORT['notes'].append('height fog properties not set: %s' % exc)

    REPORT['notes'].append(
        'sky rig = SkyAtmosphere + SkyLight(real-time capture) + sun(atmosphere light) + '
        'height fog with non-black inscattering; all four are required. A lone '
        'SkyAtmosphere produced no sky, and the water then reflected black')
    return sun, atmos, sky_light, fog


def build_level(seabed, seabed_mat):
    lev = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    if EAL.does_asset_exist(MAP):
        if not lev.load_level(MAP):
            raise RuntimeError('Could not load existing ' + MAP)
        for a in actors.get_all_level_actors():
            actors.destroy_actor(a)
    else:
        if not lev.new_level(MAP):
            raise RuntimeError('Could not create ' + MAP)
    REPORT['created'].append(MAP)

    build_lighting(actors)

    ground = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0, 0, 0))
    ground.set_actor_label('ClearwaterSeabed')
    # Tagged so AClearwaterWater can find it and drive the caustic scroll, without the C++
    # holding a hard reference to a level actor.
    ground.tags = [u.Name('ClearwaterSeabed')]
    gmc = ground.get_editor_property('static_mesh_component')
    gmc.set_editor_property('mobility', u.ComponentMobility.MOVABLE)
    gmc.set_static_mesh(seabed)
    gmc.set_material(0, seabed_mat)
    # The seabed MUST collide: the water plane deliberately has no collision (it is a
    # translucent visual surface), so without this the player falls out of the level. Its
    # top face sits at the authored depth, so the player wades at the bottom of the column.
    gmc.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
    gmc.set_collision_profile_name('BlockAll')

    # The water surface itself is NOT placed here. AClearwaterWater spawns it at runtime
    # (see Source/FPSGAME/Water/ClearwaterWater.cpp) because the Python channel only sees
    # already-loaded classes, so a code-side water actor placed from here would go stale on
    # every recompile. The level therefore owns only lighting, seabed and the spawn point.
    REPORT['notes'].append(
        'water surface is spawned by AClearwaterWater at runtime; level owns lighting, '
        'seabed and spawn point only')

    # Camera on the shore looking across the water, i.e. along -X toward the basin centre.
    # clearwater's demo looks over an open sea; here the equivalent sight line runs from the
    # rim inward. Pitch is angled slightly down so the water fills the lower half of frame
    # and the sky sits above the horizon.
    cam = actors.spawn_actor_from_class(
        u.CameraActor, u.Vector(VIEW_DISTANCE_CM, 0.0, VIEW_HEIGHT_CM))
    cam.set_actor_label('ClearwaterView')
    cam.set_actor_rotation(u.Rotator(pitch=-6.0, yaw=180.0, roll=0.0), False)
    cc = cam.get_editor_property('camera_component')
    cc.set_editor_property('field_of_view', CAMERA_FOV_DEG)

    # PlayerStart on the shore, facing the water. Its Z only needs to be above the bed; the
    # pawn falls a short distance and lands on the rim at +60 cm.
    start = actors.spawn_actor_from_class(
        u.PlayerStart, u.Vector(VIEW_DISTANCE_CM, 0.0, 200.0))
    start.set_actor_label('ClearwaterStart')
    start.set_actor_rotation(u.Rotator(0.0, 180.0, 0.0), False)

    # No underwater PostProcessVolume is placed here on purpose. UE 5.8 exposes no
    # `override_blendables` on FPostProcessSettings and no `bOverride_Blendables` in C++
    # either -- WeightedBlendables is applied unconditionally -- so a level volume could not
    # be toggled, and having one *and* the component that AClearwaterWater creates would
    # apply the water column twice. The C++ component owns it, which also lets the weight
    # follow the camera.
    REPORT['notes'].append(
        'underwater post process is owned by AClearwaterWater as an unbound '
        'UPostProcessComponent; no level volume, so the effect cannot double up')

    if not lev.save_current_level():
        raise RuntimeError('Could not save ' + MAP)
    REPORT['saved'].append(MAP)
    log('level built: ' + MAP)


def main():
    verify_shader_include()
    waves_doc, waves = load_waves()
    log('waves: %d components, loop %.0f s, patch %.1f m' % (
        len(waves), waves_doc['loop_seconds'], waves_doc.get('patch_m', 0)))
    sun_dir = sun_direction()

    # Baked data first: the materials reference these textures by name.
    caus_frames = sorted(CAUSTICS.glob('caustics_*.png'))
    if not caus_frames:
        raise RuntimeError('Run Tools/Fluids/clearwater_caustics.py first; missing PNGs in '
                           + str(CAUSTICS))
    import_texture(caus_frames[0], 'T_ClearwaterCaustics', srgb=False)
    import_texture(RIPPLES / 'T_ClearwaterRipples_N.png', 'T_ClearwaterRipples_N', srgb=False)
    REPORT['notes'].append(
        'caustics and ripples import as linear data (srgb off); %d baked caustic frames '
        'exist, the material animates by scrolling layer B against A rather than flipping '
        'through them' % len(caus_frames))

    mat = build_water_material(waves, sun_dir)
    build_water_instance(mat, waves, sun_dir)
    seabed_mat = build_seabed_material()
    build_seabed_instance(seabed_mat, sun_dir)
    uw_mat = build_underwater_material()
    build_underwater_instance(uw_mat, sun_dir)
    # Both grids still have to exist as assets: the seabed is placed in the level, and the
    # water plane is what AClearwaterWater attaches at runtime.
    import_mesh('clearwater_plane', 'SM_ClearwaterPlane', collision=False)
    seabed = import_mesh('clearwater_seabed', 'SM_ClearwaterSeabed', collision=True)
    build_level(seabed, seabed_mat)

    out = ROOT / 'Saved' / 'ClearwaterWater20260926'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'author.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    log('AUTHORED ' + json.dumps({'saved': len(REPORT['saved']),
                                  'created': len(REPORT['created'])}))


if __name__ == '__main__':
    main()
