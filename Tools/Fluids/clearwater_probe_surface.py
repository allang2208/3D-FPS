"""Probe the Clearwater water surface by routing one intermediate quantity to Emissive.

WHY THIS EXISTS
---------------
The shipped surface degrades to a smooth vertical gradient with no recognisable water
structure (Docs/Fluids/clearwater-water-migration-20260926.md section 1.1). Static reading
of the graph narrows the suspects to five quantities -- wave height, surface normal,
SceneColor, the caustic scalar, the reflected sky -- but only a rendered image of each one
can say which is actually dead. Changing numbers and eyeballing the final composite after
a 60 s capture is one experiment per hypothesis; these probes are the same 60 s each, but
each answers exactly one question.

Each probe duplicates M_ClearwaterWater, patches ONE custom node's final `return`, and
reparents the real MI_ClearwaterWater at the duplicate, because AClearwaterWater loads
/Game/Clearwater/MI_ClearwaterWater by hard path (ClearwaterWater.cpp) -- that is the only
channel the -game capture sees. Everything is restored by CLEARWATER_PROBE=restore; a
pristine copy of the instance is kept under /Game/Clearwater/Probes the first time.

The pythonscript commandlet passes no argv, so the mode travels through the environment:

    CLEARWATER_PROBE=activate:H|NRM|SCN|CAUS|SKY   build + activate one probe
    CLEARWATER_PROBE=restore                       point the instance back at the master

Driven by Tools/Fluids/run_clearwater_probes.ps1; see it for the capture loop.
"""
import json
import os
import sys

import unreal as u

MODE = os.environ.get('CLEARWATER_PROBE', '')

EAL = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

DEST = '/Game/Clearwater'
PROBE_DEST = DEST + '/Probes'
MASTER = DEST + '/M_ClearwaterWater'
MI = DEST + '/MI_ClearwaterWater'
MI_BACKUP = PROBE_DEST + '/MI_ClearwaterWater_pristine'

# Exact final statements from Tools/Fluids/clearwater_generate_nodes.py -- the patch asserts
# on these strings, so a regenerated node body that drifts fails loudly instead of silently
# patching the wrong node.
NORM_RETURN = 'return normalize(N + float3(R.xy * RipScale, 0.0));'
OPTICS_RETURN = 'return C + G;'

# node: which custom node to patch, marker: the return statement to replace,
# ret: the probe return, emissive_from_node: True rewires MP_EMISSIVE to the patched node
# (the normal node's output is not otherwise an output of the graph).
PROBES = {
    'H': {
        'node': 'normal', 'marker': NORM_RETURN,
        'ret': ('return float3(0.5 + H * AmpScale * 0.05, 0.5 + Gx * AmpScale * 4.0, '
                '0.5 + Gz * AmpScale * 4.0);'),
        'emissive_from_node': True,
        'question': 'does the 48-wave field evaluate to anything at all?',
    },
    'PINS': {
        'node': 'normal', 'marker': NORM_RETURN,
        # R: spatial bands iff world position reaches the node. G: same bands gated on the
        # wave amplitudes being delivered (step() -> 0 keeps black exposure-proof, the sky
        # anchors auto-exposure). B: a time-varying constant iff T and the waves are alive.
        # A uniform grey frame with no bands therefore separates "P dead" (R flat) from
        # "wave pins dead" (R banded, G black) from "T dead" (R,G banded, B black).
        'ret': ('float px = frac(P.x * 0.001);\n'
                'float amp = abs(W0.z) + abs(W16.z) + abs(W47.z);\n'
                'return float3(px, px * step(1e-6, amp), frac(T * 0.2) * step(1e-6, amp));'),
        'emissive_from_node': True,
        'question': 'which of P / wave pins / T is dead at runtime?',
    },
    'NRM': {
        'node': 'normal', 'marker': NORM_RETURN,
        'ret': 'return N * 0.5 + 0.5;',
        'emissive_from_node': True,
        'question': 'flat up-vector everywhere, or varying slope detail?',
    },
    'SCLR': {
        'node': 'normal', 'marker': NORM_RETURN,
        # R/G: P bands gated on the two scalar parameters (Chop, AmpScale) being delivered;
        # B: ungated P.y bands as the control channel.
        'ret': ('float px2 = frac(P.x * 0.001);\n'
                'return float3(px2 * step(0.1, Chop), px2 * step(0.1, AmpScale), '
                'frac(P.y * 0.001));'),
        'emissive_from_node': True,
        'question': 'are the scalar parameters (Chop/AmpScale) delivered?',
    },
    'SUNV': {
        'node': 'optics', 'marker': OPTICS_RETURN,
        # A vector parameter in the OPTICS node, gated the same way: separates "vector
        # parameters die everywhere" from "they die only in the 59-pin normal node".
        'ret': ('float px3 = frac(P.x * 0.001);\n'
                'return float3(px3 * step(0.05, length(SunColor.rgb)), 0.0, 0.0);'),
        'emissive_from_node': False,
        'question': 'does a vector parameter deliver in the optics node (21 pins)?',
    },
    'OPTP': {
        'node': 'optics', 'marker': OPTICS_RETURN,
        # Splits the SUNV ambiguity: R = optics-node P bands alone; G = same bands gated on
        # SunColor. Both black => optics P is dead; R banded + G black => the vector
        # parameter is dead with P confirmed alive inside the very same node.
        'ret': ('float px4 = frac(P.x * 0.001);\n'
                'return float3(px4, px4 * step(0.05, length(SunColor.rgb)), 0.0);'),
        'emissive_from_node': False,
        'question': 'inside the optics node: P alive, SunColor dead?',
    },
    'MINVEC': {
        'node': 'minimal', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'do vector parameters deliver in a minimal material at all?',
    },
    'MINOVR': {
        # Minimal material reading ONLY Wave01 (the real wave parameter name). The master
        # default amplitude is 1.05 (from the baked spectrum); the probe additionally writes
        # an instance override of 2.0 onto MI_ClearwaterWater before re-parenting.
        # R = bands iff ANY nonzero value reached the shader (0.5 gate);
        # G = bands iff the INSTANCE OVERRIDE reached it (1.5 gate, only 2.0 passes);
        # B = ungated world-position bands (control).
        # R banded + G banded  -> overrides land; the big graph is the problem.
        # R banded + G black   -> only defaults land; the MI override layer is the problem.
        # R black + B banded   -> vector parameters read zero even in a minimal material
        #                         through this instance chain.
        'node': 'minimal_override', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does the instance override, the master default, or nothing at all '
                    'reach a minimal material through MI_ClearwaterWater?',
    },
    'NOWPO': {
        'node': 'optics', 'marker': OPTICS_RETURN,
        # Same vector gate as SUNV, but the duplicate's World Position Offset is
        # disconnected first. If the gate now bands, the WPO/vertex-shader sharing of the
        # wave parameters is what zeroes them in the pixel shader.
        'ret': ('float px5 = frac(P.x * 0.001);'
                'return float3(px5, px5 * step(0.05, length(SunColor.rgb)), 0.0);'),
        'emissive_from_node': False,
        'disconnect_wpo': True,
        'question': 'do vector parameters come alive once WPO is disconnected?',
    },
    'CNT08': {
        'node': 'count8', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'do first and last of 8 vector parameters deliver?',
    },
    'CNT16': {
        'node': 'count16', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'do first and last of 16 vector parameters deliver?',
    },
    'CNT32': {
        'node': 'count32', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'do first and last of 32 vector parameters deliver?',
    },
    'CNT59': {
        'node': 'count59', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'do first and last of 59 vector parameters deliver?',
    },
    'FTINC': {
        'node': 'feature_include', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does the /Project include break parameter delivery?',
    },
    'FTTIME': {
        'node': 'feature_time', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does a Time input pin break parameter delivery?',
    },
    'FTSCN': {
        'node': 'feature_scenecolor', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does a SceneColor input connection break parameter delivery?',
    },
    'FTLOOP': {
        'node': 'feature_loop', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does the array-init + unroll-loop body break parameter delivery?',
    },
    'FTSHARE': {
        'node': 'feature_share', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'do shared params across TWO custom nodes break delivery?',
    },
    'FTWPO': {
        'node': 'feature_wpo', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does a WPO vertex node sharing the params break pixel delivery?',
    },
    'FTNAN': {
        'node': 'feature_nanite', 'marker': None, 'ret': None, 'emissive_from_node': False,
        'question': 'does the used_with_nanite flag break parameter delivery?',
    },
    'REBUILD': {
        'node': 'rebuild', 'marker': OPTICS_RETURN,
        'ret': ('float pxr = frac(P.x * 0.001); '
                'return float3(pxr, pxr * step(0.05, length(SunColor.rgb)), 0.0);'),
        'emissive_from_node': False,
        'question': 'is a freshly rebuilt full graph healthy?',
    },
    'SCN': {
        'node': 'optics', 'marker': OPTICS_RETURN,
        'ret': 'return max(SceneColor, 0.0);',
        'emissive_from_node': False,
        'question': 'does the translucent pass see the seabed behind the water?',
    },
    'CAUS': {
        'node': 'optics', 'marker': OPTICS_RETURN,
        'ret': 'return float3(max(Caustic, 0.0), 0.0, 0.0);',
        'emissive_from_node': False,
        'question': 'does the baked caustic web land as a non-constant scalar?',
    },
    'SKY': {
        'node': 'optics', 'marker': OPTICS_RETURN,
        'ret': 'return CW_SKY(Rr, SunDir);',
        'emissive_from_node': False,
        'question': 'is the reflected sky a vertical gradient, or the sideways/flat read?',
    },
}


def save_with_retry(obj, label, attempts=6, wait_s=4.0):
    """save_loaded_asset intermittently fails while the user's editor is open
    (LogSavePackage 'Failed to move ... to temp directory'); the file is only held
    for the moment the editor loads it, so retrying a few seconds later succeeds."""
    import time
    for i in range(attempts):
        if EAL.save_loaded_asset(obj, False):
            return
        print('CLEARWATER save retry %d/%d for %s' % (i + 1, attempts, label), flush=True)
        time.sleep(wait_s)
    fail('could not save ' + label + ' after %d attempts' % attempts)


def fail(msg):
    print('CLEARWATER PROBE FAILED: ' + msg, file=sys.stderr, flush=True)
    raise SystemExit(1)


def custom_nodes(mat):
    # `expressions` itself is protected and unreadable from Python; the editing library is
    # the sanctioned enumerator (clearwater_verify.py uses the same call).
    out = []
    for expr in MEL.get_material_expressions(mat):
        if not isinstance(expr, u.MaterialExpressionCustom):
            continue
        out.append(expr)
    return out


def build_minimal_probe(probe_master, name, variant=''):
    """From-scratch Unlit+Translucent material with ONE vector parameter.

    If this material delivers its vector parameter while the big Clearwater master does
    not, the failure is specific to that graph; if it also reads zero, vector parameters
    are dead engine-wide in this render path. The 'override' variant names its parameter
    Wave01 (the real spectrum parameter, master default amplitude 1.05) and splits the
    gates at 0.5 / 1.5 so instance-override vs default vs zero are told apart."""
    if EAL.does_asset_exist(probe_master):
        EAL.delete_asset(probe_master)
    mat = TOOLS.create_asset('M_Probe_%s' % name, PROBE_DEST, u.Material,
                             u.MaterialFactoryNew())
    if mat is None:
        fail('could not create ' + probe_master)

    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)

    wp = MEL.create_material_expression(mat, u.MaterialExpressionWorldPosition, -800, 0)
    mask = MEL.create_material_expression(mat, u.MaterialExpressionComponentMask, -600, 0)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    if not MEL.connect_material_expressions(wp, '', mask, ''):
        fail('minimal probe: world position mask failed')

    vec = MEL.create_material_expression(mat, u.MaterialExpressionVectorParameter, -600, 200)
    if variant == 'override':
        vec.set_editor_property('parameter_name', 'Wave01')
        vec.set_editor_property('default_value',
                                u.LinearColor(0.025952, 0.017757, 1.049779, 5.550147))
        code = ('float px = frac(P.x * 0.001);\n'
                'return float3(px * step(0.5, abs(Wave01.z)), '
                'px * step(1.5, abs(Wave01.z)), px);')
    else:
        vec.set_editor_property('parameter_name', 'OneVec')
        vec.set_editor_property('default_value', u.LinearColor(1.0, 1.0, 1.0, 1.0))
        code = ('float px = frac(P.x * 0.001);\n'
                'return float3(px, px * step(0.05, length(OneVec.rgb)), 0.0);')
    cust = MEL.create_material_expression(mat, u.MaterialExpressionCustom, -200, 0)
    cust.set_editor_property('code', code)
    cust.set_editor_property('output_type',
                             u.CustomMaterialOutputType.CMOT_FLOAT3)
    vec_pin = 'Wave01' if variant == 'override' else 'OneVec'
    inputs = []
    for pin_name in ('P', vec_pin):
        pin = u.CustomInput()
        pin.set_editor_property('input_name', pin_name)
        inputs.append(pin)
    cust.set_editor_property('inputs', inputs)
    for pin_name, src in (('P', mask), (vec_pin, vec)):
        if not MEL.connect_material_expressions(src, '', cust, pin_name):
            fail('minimal probe: connect %s failed' % pin_name)

    if not MEL.connect_material_property(cust, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        fail('minimal probe: emissive connect failed')
    opacity = MEL.create_material_expression(mat, u.MaterialExpressionConstant, -200, 300)
    opacity.set_editor_property('r', 1.0)
    if not MEL.connect_material_property(opacity, '', u.MaterialProperty.MP_OPACITY):
        fail('minimal probe: opacity connect failed')

    MEL.recompile_material(mat)
    if not EAL.save_loaded_asset(mat, False):
        fail('could not save ' + probe_master)
    return mat




def build_count_probe(probe_master, name, count):
    """One custom node fed by P + N vector parameters; R gates on the first, G on the last."""
    if EAL.does_asset_exist(probe_master):
        EAL.delete_asset(probe_master)
    mat = TOOLS.create_asset('M_Probe_%s' % name, PROBE_DEST, u.Material,
                             u.MaterialFactoryNew())
    if mat is None:
        fail('could not create ' + probe_master)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)

    wp = MEL.create_material_expression(mat, u.MaterialExpressionWorldPosition, -800, 0)
    mask = MEL.create_material_expression(mat, u.MaterialExpressionComponentMask, -600, 0)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    if not MEL.connect_material_expressions(wp, '', mask, ''):
        fail('count probe: world position mask failed')

    vecs = []
    for i in range(count):
        v = MEL.create_material_expression(mat, u.MaterialExpressionVectorParameter,
                                           -600, 200 + i * 30)
        v.set_editor_property('parameter_name', 'Vec%02d' % i)
        v.set_editor_property('default_value', u.LinearColor(0.0, 0.0, 1.0, 0.0))
        vecs.append(v)

    code = ('float px = frac(P.x * 0.001); '
            'return float3(px * step(0.5, abs(V0.z)), '
            'px * step(0.5, abs(V%d.z)), px);' % (count - 1))
    cust = MEL.create_material_expression(mat, u.MaterialExpressionCustom, -200, 0)
    cust.set_editor_property('code', code)
    cust.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    pin_names = ['P'] + ['V%d' % i for i in range(count)]
    for pin_name in pin_names:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', pin_name)
        inputs.append(pin)
    cust.set_editor_property('inputs', inputs)
    if not MEL.connect_material_expressions(mask, '', cust, 'P'):
        fail('count probe: P connect failed')
    for i, v in enumerate(vecs):
        if not MEL.connect_material_expressions(v, '', cust, 'V%d' % i):
            fail('count probe: V%d connect failed' % i)
    if not MEL.connect_material_property(cust, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        fail('count probe: emissive connect failed')
    opacity = MEL.create_material_expression(mat, u.MaterialExpressionConstant, -200, 400)
    opacity.set_editor_property('r', 1.0)
    if not MEL.connect_material_property(opacity, '', u.MaterialProperty.MP_OPACITY):
        fail('count probe: opacity connect failed')
    MEL.recompile_material(mat)
    if not EAL.save_loaded_asset(mat, False):
        fail('could not save ' + probe_master)
    return mat



def build_feature_probe(probe_master, name, feature):
    """CNT08 chassis plus ONE feature of the big material."""
    count = 8
    if EAL.does_asset_exist(probe_master):
        EAL.delete_asset(probe_master)
    mat = TOOLS.create_asset('M_Probe_%s' % name, PROBE_DEST, u.Material,
                             u.MaterialFactoryNew())
    if mat is None:
        fail('could not create ' + probe_master)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    wp = MEL.create_material_expression(mat, u.MaterialExpressionWorldPosition, -800, 0)
    mask = MEL.create_material_expression(mat, u.MaterialExpressionComponentMask, -600, 0)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    if not MEL.connect_material_expressions(wp, '', mask, ''):
        fail('feature probe: world position mask failed')
    vecs = []
    for i in range(count):
        v = MEL.create_material_expression(mat, u.MaterialExpressionVectorParameter,
                                           -600, 200 + i * 30)
        v.set_editor_property('parameter_name', 'Vec%02d' % i)
        v.set_editor_property('default_value', u.LinearColor(0.0, 0.0, 1.0, 0.0))
        vecs.append(v)

    prelude = ""
    pin_defs = [("P", mask)] + [("V%d" % i, vecs[i]) for i in range(count)]
    if feature == "include":
        prelude = '#include ' + chr(34) + '/Project/ClearwaterWaves.ush' + chr(34) + chr(10)
    if feature == "nanite":
        mat.set_editor_property('used_with_nanite', True)
    if feature == "nanite":
        mat.set_editor_property('used_with_nanite', True)
    if feature == "time":
        t = MEL.create_material_expression(mat, u.MaterialExpressionTime, -600, 500)
        pin_defs.append(("T", t))
    if feature == "scenecolor":
        sc = MEL.create_material_expression(mat, u.MaterialExpressionSceneColor, -600, 600)
        pin_defs.append(("SC", sc))

    frac_call = "CW_FRAC" if feature == "include" else "frac"
    code = (prelude +
            "float px = " + frac_call + "(P.x * 0.001); "
            "return float3(px * step(0.5, abs(V0.z)), "
            "px * step(0.5, abs(V7.z)), px);")
    cust = MEL.create_material_expression(mat, u.MaterialExpressionCustom, -200, 0)
    cust.set_editor_property('code', code)
    cust.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for pin_name, _ in pin_defs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', pin_name)
        inputs.append(pin)
    cust.set_editor_property('inputs', inputs)
    for pin_name, src in pin_defs:
        if not MEL.connect_material_expressions(src, '', cust, pin_name):
            fail('feature probe: connect %s failed' % pin_name)
    if not MEL.connect_material_property(cust, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        fail('feature probe: emissive connect failed')
    opacity = MEL.create_material_expression(mat, u.MaterialExpressionConstant, -200, 400)
    opacity.set_editor_property('r', 1.0)
    if not MEL.connect_material_property(opacity, '', u.MaterialProperty.MP_OPACITY):
        fail('feature probe: opacity connect failed')
    MEL.recompile_material(mat)
    if not EAL.save_loaded_asset(mat, False):
        fail('could not save ' + probe_master)
    return mat


def build_loop_share_probe(probe_master, name, feature):
    """CNT08 chassis with the loop-body or the two-node param sharing of the big material."""
    count = 8
    if EAL.does_asset_exist(probe_master):
        EAL.delete_asset(probe_master)
    mat = TOOLS.create_asset('M_Probe_%s' % name, PROBE_DEST, u.Material,
                             u.MaterialFactoryNew())
    if mat is None:
        fail('could not create ' + probe_master)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    wp = MEL.create_material_expression(mat, u.MaterialExpressionWorldPosition, -800, 0)
    mask = MEL.create_material_expression(mat, u.MaterialExpressionComponentMask, -600, 0)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    if not MEL.connect_material_expressions(wp, '', mask, ''):
        fail('loop/share probe: world position mask failed')
    vecs = []
    for i in range(count):
        v = MEL.create_material_expression(mat, u.MaterialExpressionVectorParameter,
                                           -600, 200 + i * 30)
        v.set_editor_property('parameter_name', 'Vec%02d' % i)
        v.set_editor_property('default_value', u.LinearColor(0.0, 0.0, 1.0, 0.0))
        vecs.append(v)

    def make_custom(code, x):
        cust = MEL.create_material_expression(mat, u.MaterialExpressionCustom, x, 0)
        cust.set_editor_property('code', code)
        cust.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs = []
        pin_defs = [('P', mask)] + [('V%d' % i, vecs[i]) for i in range(count)]
        for pin_name, _ in pin_defs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', pin_name)
            inputs.append(pin)
        cust.set_editor_property('inputs', inputs)
        for pin_name, src in pin_defs:
            if not MEL.connect_material_expressions(src, '', cust, pin_name):
                fail('loop/share probe: connect %s failed' % pin_name)
        return cust

    if feature == 'wpo':
        node_a = make_custom('return float3(0.0, 0.0, V0.z * 10.0);', -500)
        if not MEL.connect_material_property(
                node_a, '', u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
            fail('wpo probe: WPO connect failed')
        code = ('float px = frac(P.x * 0.001); '
                'return float3(px * step(0.5, abs(V0.z)), px * step(0.5, abs(V7.z)), px);')
        cust = make_custom(code, 200)
    elif feature == 'loop':
        nl = chr(10)
        code = ('float px = frac(P.x * 0.001);' + nl
                + 'float H = 0.0;' + nl
                + 'float4 W[8] = { V0, V1, V2, V3, V4, V5, V6, V7 };' + nl
                + '[unroll] for (int i = 0; i < 8; ++i)' + nl
                + '{' + nl
                + '    float2 k = W[i].xy; float A = W[i].z; float w = W[i].w;' + nl
                + '    H += A * sin(dot(k, P) - w * px);' + nl
                + '}' + nl
                + 'return float3(px * step(0.5, abs(W[0].z)), px * step(0.5, abs(W[7].z)), px);')
        cust = make_custom(code, -200)
    else:
        node_a = make_custom('return V0;', -500)
        code = ('float px = frac(P.x * 0.001); '
                'return float3(px * step(0.5, abs(V0.z)), px * step(0.5, abs(V7.z)), px);')
        cust = make_custom(code, 200)

    if not MEL.connect_material_property(cust, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        fail('loop/share probe: emissive connect failed')
    opacity = MEL.create_material_expression(mat, u.MaterialExpressionConstant, -200, 400)
    opacity.set_editor_property('r', 1.0)
    if not MEL.connect_material_property(opacity, '', u.MaterialProperty.MP_OPACITY):
        fail('loop/share probe: opacity connect failed')
    MEL.recompile_material(mat)
    if not EAL.save_loaded_asset(mat, False):
        fail('could not save ' + probe_master)
    return mat


import importlib.util as _ilu
from pathlib import Path as _Path

def _load_author_module():
    script = str(_Path(u.Paths.project_dir()) / 'Tools' / 'Fluids' / 'author_clearwater_water.py')
    modspec = _ilu.spec_from_file_location('author_cw_rebuild', script)
    mod = _ilu.module_from_spec(modspec)
    modspec.loader.exec_module(mod)
    return mod

def build_fresh_water_master():
    """Rebuild the FULL water material graph from scratch under /Probes via the author
    module, so a healthy result indicts the previously saved asset and a dead result
    gives a from-scratch reproduction."""
    mod = _load_author_module()
    mod.DEST = PROBE_DEST
    mod.MAT_WATER = PROBE_DEST + '/M_ClearwaterWater'
    data, waves = mod.load_waves()
    sun_dir = mod.sun_direction()
    return mod.build_water_material(waves, sun_dir)

def dup_optics_code(mat):
    for expr in custom_nodes(mat):
        code = expr.get_editor_property('code')
        if OPTICS_RETURN in code:
            return expr, code
    fail('fresh master has no optics node')

def dup_optics_patch(mat, found, ret):
    expr, code = found
    expr.set_editor_property('code', code.replace(OPTICS_RETURN, ret))
    MEL.recompile_material(mat)
    if not EAL.save_loaded_asset(mat, False):
        fail('could not save fresh master')


def patch_probe(name):
    spec = PROBES[name]
    probe_master = '%s/M_Probe_%s' % (PROBE_DEST, name)
    EAL.make_directory(PROBE_DEST)

    # Keep one pristine copy of the instance the first time anything is activated.
    if not EAL.does_asset_exist(MI_BACKUP):
        EAL.duplicate_asset(MI, MI_BACKUP)
        print('CLEARWATER backup: %s' % MI_BACKUP, flush=True)

    elif spec['node'] == 'rebuild':
        dup = build_fresh_water_master()
        code = dup_optics_code(dup)
        dup_optics_patch(dup, code, spec['ret'])
    if spec['node'] == 'minimal':
        dup = build_minimal_probe(probe_master, name)
    elif spec['node'].startswith('count'):
        dup = build_count_probe(probe_master, name, int(spec['node'][5:]))
    elif spec['node'] in ('feature_loop', 'feature_share', 'feature_wpo'):
        dup = build_loop_share_probe(probe_master, name, spec['node'][8:])
    elif spec['node'].startswith('feature_'):
        dup = build_feature_probe(probe_master, name, spec['node'][8:])
    elif spec['node'] == 'minimal_override':
        dup = build_minimal_probe(probe_master, name, variant='override')
    else:
        dup = duplicate_and_patch(spec, probe_master)

    mi = EAL.load_asset(MI)
    if mi is None:
        fail('could not load ' + MI)
    if spec['node'] == 'minimal_override':
        MEL.set_material_instance_vector_parameter_value(
            mi, 'Wave01', u.LinearColor(0.0, 0.0, 2.0, 0.0))
    MEL.set_material_instance_parent(mi, dup)
    save_with_retry(mi, MI)

    print('CLEARWATER PROBE OK ' + json.dumps({
        'probe': name,
        'question': spec['question'],
        'master': probe_master,
        'instance_parent': probe_master,
    }), flush=True)


def duplicate_and_patch(spec, probe_master):
    if EAL.does_asset_exist(probe_master):
        EAL.delete_asset(probe_master)
    dup = EAL.duplicate_asset(MASTER, probe_master)
    if dup is None:
        fail('could not duplicate %s -> %s' % (MASTER, probe_master))
    dup = EAL.load_asset(probe_master)

    patched = 0
    target = None
    # A unique comment forces the DDC content hash to change, so a -game run with
    # r.DumpShaderDebugInfo actually compiles (and dumps) this material instead of hitting
    # the shared cache from an identical earlier build.
    import time as _time
    unique = '// probe build %s\n' % _time.time()
    for expr in custom_nodes(dup):
        code = expr.get_editor_property('code')
        if spec['marker'] not in code:
            continue
        if patched:
            fail('marker %r matched more than one custom node' % spec['marker'])
        expr.set_editor_property('code', unique + code.replace(spec['marker'], spec['ret']))
        target = expr
        patched += 1
    if not patched:
        fail('no custom node carries the marker %r -- regenerate nodes.json?' % spec['marker'])

    if spec['emissive_from_node']:
        if not MEL.connect_material_property(
                target, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
            fail('could not rewire Emissive to the patched node')

    if spec.get('disconnect_wpo'):
        MEL.disconnect_material_property(dup, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    # The recompile can be skipped so the next -game run is the first compiler of the new
    # content hash: combined with r.DumpShaderDebugInfo=1 that run then dumps the real
    # translated HLSL. Recompiling here instead would park the shaders in the DDC and the
    # game would hit the cache without ever dumping.
    if os.environ.get('CLEARWATER_PROBE_NORECOMPILE') != '1':
        MEL.recompile_material(dup)
    if not EAL.save_loaded_asset(dup, False):
        fail('could not save ' + probe_master)
    return dup


def restore():
    master = EAL.load_asset(MASTER)
    if master is None:
        fail('could not load ' + MASTER)
    mi = EAL.load_asset(MI)
    if mi is None:
        fail('could not load ' + MI)
    MEL.set_material_instance_parent(mi, master)
    # Verify by reading the parent back: save_loaded_asset returns False for a package that
    # ended up not dirty (parent was already the master), which is success, not failure.
    parent = mi.get_editor_property('parent')
    parent_path = parent.get_path_name() if parent else '<none>'
    if 'M_Probe_' in parent_path:
        fail('parent is still a probe master: ' + parent_path)
    # Force the package dirty so the restore actually lands on disk even when the parent was
    # already correct (save_loaded_asset skips clean packages and returns False).
    mi.modify()
    save_with_retry(mi, MI)
    print('CLEARWATER PROBE OK {"restored": "%s", "parent": "%s"}' % (MI, parent_path),
          flush=True)


def main():
    if MODE.startswith('activate:'):
        name = MODE.split(':', 1)[1]
        if name not in PROBES:
            fail('unknown probe %r; known: %s' % (name, ', '.join(sorted(PROBES))))
        patch_probe(name)
    elif MODE == 'restore':
        restore()
    else:
        fail('set CLEARWATER_PROBE to activate:<name> or restore (got %r)' % MODE)


main()
