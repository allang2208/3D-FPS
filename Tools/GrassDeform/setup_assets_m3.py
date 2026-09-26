"""Create the M3 assets of the GPU grass interaction system (footstep feedback).

Run headless through Tools/GrassDeform/run_asset_setup_m3.ps1, or through the MCP batch bridge while
an editor holds the project. The script is idempotent: every step checks for the existing asset or
property and only authors what is missing, so it can be re-run after a partial failure. Re-running
after a *contract* change is handled by the version tags below, which rebuild a stale graph instead
of silently keeping it.

Creates under /Game/WorldGeneration/GrassDeform/:
  NS_GrassFootstepPuff     one-shot sprite puff: grass bits + a little dust, <=64 live particles,
                           self-terminating (the C++ component relies on the system finishing so
                           its puff budget is returned).
  M_GrassTrampleDecal      deferred decal that darkens the ground where a foot landed. One scalar
                           parameter, "Fade" (1 = fresh, 0 = gone), animated per decal instance by
                           UGrassFootstepFeedbackComponent.
  DA_GrassFootstepFeedback UGrassFootstepFeedbackConfig instance wired to the two assets above and
                           seeded with the grass-ish surface whitelist.

Design notes:
  - It does NOT touch the DynamicMesh hill ground material family
    (Docs/WorldGeneration/ground-material-layered-20260918.md). A deferred decal is composited over
    whatever the ground material draws, so the darkening is achieved without editing the layered
    family, its Wetness contract or its parallax. That is the whole reason the trail is a decal and
    not a material feature.
  - M_GrassTrampleDecal deliberately uses only built-in nodes: it must not depend on a texture that
    the M1 grass library or the ground family could rename. The look is driven by a radial falloff
    and a soft noise break-up authored inline, so the asset stands alone.
  - The puff is CPU-sim: at <=64 particles the sim cost is negligible and, unlike a GPU sim, it
    needs no fixed bounds or data-interface plumbing to be correct under the project's bounded-pool
    rules (skills/ue5-fluid-vfx-workflow/references/runtime-budget.md). The C++ side caps
    concurrency at PuffMaxActive regardless of the sim target.

Headless notes (the API shapes this script depends on, all verified against the 5.8 engine source):
  * UMaterial has no 'description' property (Material.h declares none; only UMaterialFunction does,
    MaterialFunction.h:57), so the decal-material version tag rides on asset metadata under
    VERSION_TAG_KEY instead. This is the bug that killed the first run at
    set_editor_property('description', ...) with "Failed to find property 'description'".
  * MaterialEditingLibrary.create_material_expression() is typed to UMaterial only
    (MaterialEditingLibrary.h / .cpp:634). This script creates no material *function*, so every
    graph it authors is a UMaterial and the plain entry point is correct here; new_expression()
    below still routes a function graph through create_material_expression_in_function() so the
    helper stays correct if a function node is ever added.
  * A TextureSample node's UV input pin is addressed as 'UVs', not 'UV' or 'Coordinates'.
  * CustomMaterialOutputType members are upper-cased in Python: CMOT_FLOAT1 .. CMOT_FLOAT4. A bare
    CMOT_FLOAT does not exist.
  * Niagara authoring goes through the UNiagaraToolset_System endpoints (AddEmitter / AddModule /
    RemoveModule / set_*_data). Every one of those calls reports failure through
    UKismetSystemLibrary::RaiseScriptError, i.e. a Python RuntimeError, and every one of them lives
    in NiagaraToolsets -- an *Experimental* plugin outside the project's control. The whole Niagara
    section is therefore best-effort: a failure is recorded in REPORT['manual'] with the exact
    emitter specification and the script carries on, because the decal material and the DataAsset
    (the two assets the C++ component actually needs to be functional) must still be created.

Plan: Docs/WorldGeneration/grass-interaction-gpu-20260925.md section 5 (and section 7 for budgets).
Consumers: Source/FPSGAME/WorldGeneration/GrassDeform/GrassFootstepFeedbackComponent.{h,cpp}
"""
import json
import traceback
from datetime import datetime

import unreal as u

DEST = '/Game/WorldGeneration/GrassDeform'

EAL = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary

# ---------------------------------------------------------------------------------------------
# Version tags. Same discipline as setup_assets_m1.py: an asset whose tag does not carry the current
# version is rebuilt from scratch, which is what makes a re-run converge after the contract
# (parameter names, particle budget, decal blend) changes instead of keeping a stale graph.
#
# Where each tag lives: asset metadata, for ALL THREE assets.
#   * M_GrassTrampleDecal      -> UMaterial has no description (M1's finding; Material.h declares
#                                 none -- only UMaterialFunction does, MaterialFunction.h:57).
#   * NS_GrassFootstepPuff     -> UNiagaraSystem has no description either (measured headless
#                                 2026-09-26: "NiagaraSystem: Failed to find property 'description'").
#                                 Same bug class, same fix.
#   * DA_GrassFootstepFeedback -> UGrassFootstepFeedbackConfig is a plain UDataAsset with no version
#                                 UPROPERTY.
# The asset registry tag is serialised with the asset, so it survives save/reload and is what makes
# the rebuild-on-contract-change path converge.
# ---------------------------------------------------------------------------------------------

PUFF_VERSION_TAG = 'puff-v1'
DECAL_VERSION_TAG = 'decal-v1'
CONFIG_VERSION_TAG = 'cfg-v1'

# Asset-registry metadata key carrying a version tag for assets that expose no description field.
# Must match setup_assets_m1.py so the two scripts read/write the same tag.
VERSION_TAG_KEY = 'GrassDeformVersion'

# Decal material scalar parameter. Must match GrassFootstepFeedbackComponent.cpp
# (GrassFootstepAssets::DecalFadeParameter).
DECAL_FADE_PARAMETER = 'Fade'

# Live-particle ceiling documented for M3 (plan section 5 / section 7: "particles <= 64").
PUFF_MAX_PARTICLES = 64

# Puff lifetime, seconds. Kept below GrassFootstepFeedbackComponent's PuffFallbackLifeSeconds (2.5s),
# which is the component-side backstop if this system ever fails to report that it finished.
PUFF_LIFETIME_SECONDS = 1.4

# Particle count per footstep. One step is a small scuff, not a burst; the concurrency cap in C++
# (PuffMaxActive) bounds the total, this bounds each individual step.
PUFF_SPAWN_COUNT = 18

# Input pin name of a TextureSample node's UV slot. The graph editor *labels* this pin "UV" and the
# engine's name for the input is "Coordinates", but ConnectMaterialExpressions() matches the
# *shortened* pin name, which is 'UVs' (MaterialGraphNode.cpp:602-605). 'UV' and 'Coordinates' both
# fail to resolve. Same constant as setup_assets_m1.py.
TEX_COORD_INPUT = 'UVs'

REPORT = {'created': [], 'patched': [], 'skipped': [], 'manual': [], 'errors': []}

# Set only by main() once every asset step has run to completion. The RESULT line is printed when
# (and only when) this is true, so an all-empty REPORT can never masquerade as a success: a run that
# dies early prints a GRASS_DEFORM_M3_ABORTED line instead of a RESULT block.
_COMPLETED = False


def log(message):
    print('[GrassDeform M3] ' + str(message), flush=True)


def note_manual(message, error=None):
    """Record a non-fatal follow-up for the user, with the exception text when there is one."""
    text = str(message)
    if error is not None:
        text = '%s (%s: %s)' % (text, type(error).__name__, error)
    REPORT['manual'].append(text)
    log('MANUAL: ' + text)


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


def connect(source, source_output, target, target_input):
    if not MEL.connect_material_expressions(source, source_output, target, target_input):
        raise RuntimeError('Could not connect %s.%s -> %s.%s'
                           % (source.get_name(), source_output, target.get_name(), target_input))


def connect_property(source, source_output, prop):
    if not MEL.connect_material_property(source, source_output, prop):
        raise RuntimeError('Could not connect %s to %s' % (source.get_name(), prop))


def new_expression(graph, expression_class):
    """Create one expression node in `graph`, which may be a UMaterial or a UMaterialFunction.

    MaterialEditingLibrary.create_material_expression() is typed to UMaterial only; a material
    *function* graph must go through create_material_expression_in_function(), a separate engine
    entry point (MaterialEditingLibrary.cpp:634 vs .cpp:676). Passing a UMaterialFunction to the
    UMaterial overload raises a binder TypeError. M3 authors no function, but routing here keeps the
    helper correct for either graph.
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


def add_custom(material, desc, code, output_type, pin_names):
    """Author a Custom HLSL node. Input pins are declared in `pin_names` order.

    `output_type` is the *Python* spelling of ECustomMaterialOutputType: CMOT_FLOAT1 / CMOT_FLOAT2 /
    CMOT_FLOAT3 / CMOT_FLOAT4. The binding upper-cases every enum member, so the C++ spelling
    (CMOT_Float1 .. CMOT_Float4) does not resolve from Python, and a bare CMOT_FLOAT does not exist.
    A scalar output is CMOT_FLOAT1.
    """
    expr = new_expression(material, u.MaterialExpressionCustom)
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


def scalar_param(material, name, default):
    expr = new_expression(material, u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', default)
    return expr


def version_tag(asset):
    """Read the version tag stored in asset metadata (see VERSION_TAG_KEY)."""
    try:
        return str(EAL.get_metadata_tag(asset, VERSION_TAG_KEY))
    except Exception:
        return ''


def set_version_tag(asset, tag):
    """Stamp a version tag into asset metadata.

    Used for every asset here that has no description field: UMaterial (M1's finding) and
    UGrassFootstepFeedbackConfig, which is a plain UDataAsset with no version UPROPERTY. The tag is
    serialised with the asset, so it survives a save/reload and the rebuild-on-change path converges.
    """
    return EAL.set_metadata_tag(asset, VERSION_TAG_KEY, tag)


# ---------------------------------------------------------------------------------------------
# M_GrassTrampleDecal
#
# Deferred decal: the renderer projects this along the decal component's local X axis onto whatever
# the ground draws, so it composites over the DynamicMesh hill terrain without the layered ground
# family being modified at all (plan section 5; the family's own doc forbids restructuring it).
#
# Opacity is a radial falloff broken up by a cheap 2D value hash, so the footprint does not read as
# a perfect circle, multiplied by the "Fade" scalar the component animates per decal instance.
# Emission is zero and the blend mode is translucent with a near-black base colour: a trampled
# footprint is a *darkening*, not a new surface.
# ---------------------------------------------------------------------------------------------

DECAL_CODE = '''
// UV is the decal's own 0..1 projection space. Radial mask with a squared shoulder so the footprint
// is soft at the rim instead of ending on a hard circle edge.
float2 Centered = UV - 0.5;
float Distance = length(Centered) * 2.0;
float Radial = 1.0 - saturate(Distance);
Radial = Radial * Radial * (3.0 - 2.0 * Radial);

// Cheap value noise: a hash on a coarse grid, enough to break the circle up into something that
// reads as disturbed grass rather than a stamp. Kept to a handful of ALU because this runs on every
// decal pixel in the pool.
float2 Grid = Centered * 6.0;
float2 Cell = floor(Grid);
float2 Frac = frac(Grid);
Frac = Frac * Frac * (3.0 - 2.0 * Frac);
float2 Hash = float2(dot(Cell, float2(127.1, 311.7)), dot(Cell, float2(269.5, 183.3)));
Hash = frac(sin(Hash) * 43758.5453);
float Noise = lerp(lerp(Hash.x, Hash.y, Frac.x), lerp(Hash.y, Hash.x, Frac.x), Frac.y);

// The rim of the footprint stays a little stronger than the middle, which is what a sole actually
// leaves behind; Noise carves irregular holes so overlapping steps do not stack into a blob.
float Density = Radial * lerp(0.55, 1.0, Noise);

return saturate(Density * Fade);
'''


def build_decal_material():
    path = DEST + '/M_GrassTrampleDecal'
    existing = load_optional(path)
    if existing is not None and DECAL_VERSION_TAG in version_tag(existing):
        MEL.recompile_material(existing)
        REPORT['skipped'].append('M_GrassTrampleDecal (exists, ' + DECAL_VERSION_TAG + ')')
        return existing

    if existing is not None:
        log('M_GrassTrampleDecal exists but is not ' + DECAL_VERSION_TAG + '; rebuilding its graph')
        MEL.delete_all_material_expressions(existing)
        material = existing
        set_version_tag(material, DECAL_VERSION_TAG)
        REPORT['patched'].append('M_GrassTrampleDecal rebuilt for ' + DECAL_VERSION_TAG)
    else:
        material = create_asset('M_GrassTrampleDecal', u.Material, u.MaterialFactoryNew())
        set_version_tag(material, DECAL_VERSION_TAG)

    # There is deliberately NO set_editor_property('description', ...) here: UMaterial has no such
    # property and the call raises "Failed to find property 'description'". The tag rides on asset
    # metadata instead (set_version_tag above).

    # Deferred decals must be translucent; the darkening is carried in Opacity, and BaseColor is
    # driven to near-black so the footprint reads as flattened shadowed grass rather than paint.
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', False)

    uv = new_expression(material, u.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('coordinate_index', 0)

    body = add_custom(material, 'GrassTrampleDecal', DECAL_CODE,
                      u.CustomMaterialOutputType.CMOT_FLOAT1, ['UV', 'Fade'])
    connect(uv, '', body, 'UV')
    # The one parameter the runtime animates: 1 for a fresh footprint, 0 when the slot retires.
    # Default 0 so a decal placed without a MID (fallback path) is invisible rather than a solid
    # black disc on the terrain.
    connect(scalar_param(material, DECAL_FADE_PARAMETER, 0.0), '', body, 'Fade')
    connect_property(body, '', u.MaterialProperty.MP_OPACITY)

    # Constant near-black base colour: trampled grass is darker, not a different hue.
    dark = new_expression(material, u.MaterialExpressionConstant3Vector)
    dark.set_editor_property('constant', u.LinearColor(0.035, 0.030, 0.022, 1.0))
    connect_property(dark, '', u.MaterialProperty.MP_BASE_COLOR)

    MEL.recompile_material(material)
    save(material, 'M_GrassTrampleDecal')
    return material


# ---------------------------------------------------------------------------------------------
# NS_GrassFootstepPuff
#
# One-shot sprite emitter: grass bits kicked up by the sole plus a little dust. Bounded by
# construction - a single instantaneous burst of PUFF_SPAWN_COUNT particles with a fixed lifetime
# and no looping emitter - so the only unbounded risk is concurrency, which the C++ component caps
# at PuffMaxActive (plan section 5; skill runtime-budget.md "define trigger rate, peak concurrency,
# max life, pool ceiling and reuse policy").
#
# AUTHORING POLICY: this whole section is best-effort. The Niagara endpoints live in
# NiagaraToolsets, an *Experimental* engine plugin whose Blueprint API is version-sensitive, and
# every endpoint reports failure by raising a Python-level script error. A failure here must not
# cost the run its decal material and DataAsset, so build_puff_system() converts any failure into a
# REPORT['manual'] entry carrying the exact emitter specification (see NIAGARA_SPEC below) and
# returns None; build_config() then leaves PuffSystem empty, which the C++ component treats as
# "puff unavailable" and falls back to decal+stamp only.
# ---------------------------------------------------------------------------------------------

# Template emitter, a project-content sprite emitter.
#
# NOT /Niagara/DefaultAssets/Templates/Emitters/SimpleSpriteBurst, which was the obvious choice and
# is wrong on this host: that folder is not served by the runtime mount. Measured headless (probe,
# 2026-09-26): does_asset_exist() is False for the template path, the asset registry serves exactly
# ONE asset under the whole of /Niagara/DefaultAssets, and there are ZERO NiagaraEmitter assets
# anywhere under /Niagara. /Niagara/Modules/... *does* resolve, but the emitter templates do not.
#
# All 29 reachable UNiagaraEmitter assets live under /Game, so the template has to come from there.
# NE_Heat is the project's own soft dust/ember sprite emitter (the Vefects pack) and is already a
# dependency of this project's fluid scripts (Tools/Fluids/author_river_pilot.py loads the same
# pack), so using it adds no new content dependency to the project.
EMITTER_TEMPLATE = '/Game/Vefects/Free_Fire/Shared/Particles/NE_Heat'

# Instantaneous spawn module. Added explicitly so the burst is an *instant* one-shot regardless of
# what the template happens to carry, which is what "spawn burst instant on footstep" requires.
# /Niagara/Modules/... IS served by the mount even though the DefaultAssets templates are not
# (verified headless 2026-09-26).
SPAWN_BURST_MODULE = '/Niagara/Modules/Emitter/SpawnBurst_Instantaneous'
# Module name as it appears in the stack, i.e. the last path segment of SPAWN_BURST_MODULE. Used to
# address its inputs and to avoid adding a second copy.
SPAWN_BURST_NAME = 'SpawnBurst_Instantaneous'

PUFF_EMITTER_NAME = 'GrassPuff'

# Modules kept from the template: everything else it brings in is removed so the puff does not
# silently inherit modules from a generic sprite-burst template. The keep-list is the shape the
# effect needs: "spawn N once, give them a lifetime, then die".
KEEP_EMITTER_UPDATE = ['EmitterState']
KEEP_PARTICLE_SPAWN = ['InitializeParticle']
KEEP_PARTICLE_UPDATE = ['ParticleState']

STACK_SCRIPTS = (
    ('EmitterUpdateScript', 'EmitterState', KEEP_EMITTER_UPDATE),
    ('ParticleSpawnScript', 'InitializeParticle', KEEP_PARTICLE_SPAWN),
    ('ParticleUpdateScript', 'ParticleState', KEEP_PARTICLE_UPDATE),
)

# Stack-input value structs. SetStackInputData takes an FNiagaraExt_StackInputValue, which is an
# instanced struct: the *type* selects interpretation and the wire format is UE's own ImportText
# syntax. The map below is what this script writes and is the part that is version-sensitive.
NIAGARA_FLOAT = '/Script/Niagara.NiagaraFloat'
NIAGARA_INT32 = '/Script/Niagara.NiagaraInt32'
NIAGARA_HLSL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'

# The exact emitter specification, printed verbatim into REPORT['manual'] when the API path fails.
# It is written so a human can build NS_GrassFootstepPuff in the editor in a couple of minutes
# without re-deriving anything from this file: every number matches the constants above and the
# C++ component's expectations.
NIAGARA_SPEC = (
    'NS_GrassFootstepPuff emitter specification (build by hand if this entry is present): '
    'asset = {dest}/NS_GrassFootstepPuff (Niagara System). '
    'Emitter: start from a one-shot sprite emitter template, name it "GrassPuff", Sim Target = '
    'CPUSim, Local Space = OFF (world-space: the component places the system at the contact point). '
    'Keep exactly EmitterState / InitializeParticle / ParticleState; remove every other module the '
    'template brings in. '
    'Emitter Update -> EmitterState: Loop Behavior = Once, Life Cycle Mode = Self (one-shot, '
    'self-terminating so the component gets its puff budget back). '
    'Emitter Update -> Spawn Burst Instantaneous: Spawn Count = {count}, Spawn Time = 0. '
    'Particle Spawn -> Initialize Particle: Lifetime = {life}s (uniform or range), Color/Size small. '
    'Particle Update -> Particle State: default is fine; drag/damping may be added. '
    'REQUIRED to satisfy the plan section 5 budget: <= {max} live particles (burst {count} x ~1s '
    'life), one sprite renderer only, and the system must FINISH (no infinite loop behavior). '
    'The C++ side sets ENCPoolMethod::AutoRelease on spawn, so nothing else is needed there. '
    'Visual: grass bits (small green-olive sprites) plus a little dust (2-3 larger, low-alpha, '
    'grey-brown) kicked up from the contact, biased along the travel direction - a scuff, not a '
    'confetti explosion. Then re-run Tools/GrassDeform/run_asset_setup_m3.ps1: it only wires the '
    'DA_GrassFootstepFeedback PuffSystem reference, and re-running it is idempotent.'
).format(dest=DEST, count=PUFF_SPAWN_COUNT, life='%.1f' % PUFF_LIFETIME_SECONDS,
         max=PUFF_MAX_PARTICLES)


def _niagara_toolset():
    """The Niagara editor-scripting toolset used by this project's other authoring scripts.

    UNiagaraToolset_System is a UBlueprintFunctionLibrary-style toolset object; get_default_object()
    returns its CDO, whose static BlueprintCallable functions are what call_method() invokes.
    """
    return u.get_default_object(u.NiagaraToolset_System)


def _niagara_ref(system, emitter, script='', module=''):
    """Build FNiagaraExt_StackItemReference via its exported properties.

    The struct's own UPROPERTY names are System / EmitterName / ScriptName / ModuleName (see
    NiagaraExternalSystemEditorUtilities.h:1000-1015); the script-name *values* are the stack script
    names 'EmitterUpdateScript' / 'ParticleSpawnScript' / 'ParticleUpdateScript'.

    NOTE: this deliberately does NOT use the 'property_values' JSON string. That is the custom
    TypeScript/JSON-schema binding path, not the Python property path; the sibling M1 script's
    proven headless pattern is to set the real reflected properties.
    """
    ref = u.NiagaraExt_StackItemReference()
    ref.set_editor_property('system', system)
    if emitter:
        ref.set_editor_property('emitter_name', emitter)
    if script:
        ref.set_editor_property('script_name', script)
    if module:
        ref.set_editor_property('module_name', module)
    return ref


def _niagara_emitter_data(b_local_space=False, sim_target='CPUSim'):
    """FNiagaraExt_EmitterData via its exported 'property_values' JSON blob.

    The emitter data struct's only exposed field is the JSON blob (documented on the toolset's
    GetEmitterData: "a single JSON-string blob in PropertyValues" whose fields use C++ PascalCase).
    """
    data = u.NiagaraExt_EmitterData()
    data.set_editor_property('property_values', json.dumps({
        'bLocalSpace': b_local_space,
        'SimTarget': sim_target,
        'bInterpolatedSpawning': False,
        'bDeterminism': False,
    }))
    return data


def _stack_module_names(api, system, script):
    """Module names currently in one script stack."""
    topology = api.call_method('GetEmitterTopology', (_niagara_ref(system, PUFF_EMITTER_NAME),))
    property_name = {'EmitterUpdateScript': 'emitter_update_script',
                     'ParticleSpawnScript': 'particle_spawn_script',
                     'ParticleUpdateScript': 'particle_update_script'}[script]
    return [str(m.get_editor_property('module_name'))
            for m in topology.get_editor_property(property_name).get_editor_property('modules')]


def _stack_input(api, system, script, module, input_name, value, struct_path):
    """Write one stack input and return True only when the write demonstrably took.

    `value` is already in the struct's ImportText form. The struct path selects how
    SetStackInputData interprets the payload: a plain number (NiagaraFloat/NiagaraInt32, e.g.
    '(Value=18)') or an HLSL expression, used for enum-style inputs (e.g. '(HlslExpression="Once")').

    VERIFICATION IS NOT OPTIONAL HERE. SetStackInputData does NOT raise when it cannot apply a
    write: it logs a LogScript *warning* through the toolset's error channel and returns normally.
    Measured headless (2026-09-26), with the caller believing it had succeeded:
      * "在堆栈引用中未找到模块 SpawnBurst_Instantaneous ..."  (module not in the stack at all)
      * "拒绝设置输入 Lifetime: 该输入被静态开关/条件逻辑隐藏 ..."  (input hidden behind a switch)
    Both returned without raising, so a try/except around call_method() proves nothing. The value is
    therefore read back and compared; a mismatch is a real failure and the caller decides whether it
    is fatal.
    """
    data = u.NiagaraExt_StackInputValue()
    data.import_text('(Value=(StructType="/Script/CoreUObject.ScriptStruct\'%s\'",'
                     'StructValue="%s"))' % (struct_path, value.replace('"', '\\"')))
    ref = _niagara_ref(system, PUFF_EMITTER_NAME, script, module)
    ref.set_editor_property('input_name_stack', [input_name])
    api.call_method('SetStackInputData', (ref, data))

    # Read back: the stored value's exported text must contain the literal we asked for.
    read_back = _niagara_ref(system, PUFF_EMITTER_NAME, script, module)
    read_back.set_editor_property('input_name_stack', [input_name])
    actual = api.call_method('GetStackInputData', (read_back,))
    try:
        text = actual.export_text()
    except Exception:
        text = str(actual)
    # '(Value=18)' -> '18';  '(HlslExpression="Once")' -> 'Once'
    expected = value.split('=', 1)[-1].strip().rstrip(')').strip('"')
    return expected in text


def build_puff_system():
    """Best-effort authoring of NS_GrassFootstepPuff. Returns the system, or None when the Niagara
    API path failed (in which case REPORT['manual'] carries NIAGARA_SPEC).

    Nothing raised in here is allowed to escape: see the authoring policy above.
    """
    path = DEST + '/NS_GrassFootstepPuff'
    try:
        existing = load_optional(path)
        if existing is not None:
            if PUFF_VERSION_TAG in version_tag(existing):
                REPORT['skipped'].append('NS_GrassFootstepPuff (exists, ' + PUFF_VERSION_TAG + ')')
                return existing
            log('NS_GrassFootstepPuff exists but is not ' + PUFF_VERSION_TAG + '; rebuilding it')
            EAL.delete_asset(path)

        if not EAL.does_asset_exist(EMITTER_TEMPLATE):
            note_manual('NS_GrassFootstepPuff could not be authored: emitter template %s is '
                        'missing, so there was nothing to build the emitter from. ' % EMITTER_TEMPLATE
                        + NIAGARA_SPEC)
            return None

        api = _niagara_toolset()
        template = u.load_asset(EMITTER_TEMPLATE)

        system = create_asset('NS_GrassFootstepPuff', u.NiagaraSystem, u.NiagaraSystemFactoryNew())
        # UNiagaraSystem has NO 'description' property either -- set_editor_property('description')
        # raises "NiagaraSystem: Failed to find property 'description'" (measured headless on this
        # build). This is the same bug class as UMaterial above, and it is the reason the version tag
        # goes through asset metadata for every asset in this script. Do not "restore" a description
        # write here.
        set_version_tag(system, PUFF_VERSION_TAG)

        # A one-shot world-space effect: each step should look slightly different, so determinism
        # stays off. The bounds box is a cull box only; the sim is CPU-side at this particle count.
        try:
            system.set_editor_property('determinism', False)
            system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-60.0, -60.0, -10.0),
                                                             max=u.Vector(60.0, 60.0, 90.0)))
        except Exception as error:
            log('system-level properties not settable (non-fatal): %s' % error)

        api.call_method('AddEmitter', (system, template, PUFF_EMITTER_NAME))
        log('added emitter %s from %s' % (PUFF_EMITTER_NAME, EMITTER_TEMPLATE))

        # Trim the template down to a plain burst: spawn module + lifetime + state. Removing the
        # rest keeps the puff budget honest (one emitter, one renderer, no extra spawn groups).
        topology = api.call_method('GetEmitterTopology', (_niagara_ref(system, PUFF_EMITTER_NAME),))
        for script, _module, keep in STACK_SCRIPTS:
            property_name = {'EmitterUpdateScript': 'emitter_update_script',
                             'ParticleSpawnScript': 'particle_spawn_script',
                             'ParticleUpdateScript': 'particle_update_script'}[script]
            modules = topology.get_editor_property(property_name).get_editor_property('modules')
            for module in modules:
                name = str(module.get_editor_property('module_name'))
                if name in keep:
                    continue
                api.call_method('RemoveModule',
                                (_niagara_ref(system, PUFF_EMITTER_NAME, script, name),))
                log('  - removed template module %s' % name)

        # The template's own spawn module (SpawnRate) was just removed, so the burst has to be added
        # explicitly or the emitter would spawn nothing at all. Belt-and-braces: only add it when it
        # is genuinely absent, so a template that already carries one cannot end up with two.
        if SPAWN_BURST_NAME not in _stack_module_names(api, system, 'EmitterUpdateScript'):
            if not EAL.does_asset_exist(SPAWN_BURST_MODULE):
                note_manual('NS_GrassFootstepPuff: the instantaneous spawn module %s is missing, so '
                            'the emitter cannot be given a footstep burst. ' % SPAWN_BURST_MODULE
                            + NIAGARA_SPEC)
                return None
            api.call_method('AddModule', (_niagara_ref(system, PUFF_EMITTER_NAME,
                                                       'EmitterUpdateScript'),
                                          u.load_asset(SPAWN_BURST_MODULE)))
            log('added module %s' % SPAWN_BURST_NAME)

        # World space: the component places the system at the contact point. CPUSim: at <=64
        # particles the sim cost is negligible and it needs no GPU data-interface plumbing.
        try:
            api.call_method('SetEmitterData', (_niagara_ref(system, PUFF_EMITTER_NAME),
                                               _niagara_emitter_data()))
        except Exception as error:
            log('emitter data not settable (non-fatal): %s' % error)

        # Pin the two inputs that ARE the documented budget: burst count and lifetime. Both are
        # verified by read-back, because SetStackInputData reports a rejected write only as a log
        # warning. A failure here is escalated to REPORT['manual'] rather than being reported as if
        # it had worked -- claiming "pinned to 18 particles" while the emitter actually spawns
        # something else is exactly the kind of silent divergence this script must not produce.
        applied = []
        rejected = []
        for script, module, input_name, value, struct_path, label in (
                ('ParticleSpawnScript', 'InitializeParticle', 'Lifetime',
                 '(Value=%.2f)' % PUFF_LIFETIME_SECONDS, NIAGARA_FLOAT, 'Lifetime'),
                ('EmitterUpdateScript', SPAWN_BURST_NAME, 'Spawn Count',
                 '(Value=%d)' % PUFF_SPAWN_COUNT, NIAGARA_INT32, 'Spawn Count')):
            try:
                ok = _stack_input(api, system, script, module, input_name, value, struct_path)
            except Exception as error:
                ok = False
                log('%s write raised: %s' % (label, error))
            (applied if ok else rejected).append(label)

        # Loop Behavior makes the "one-shot, self-terminating" contract explicit. It is an
        # enum-style input on EmitterState. If EmitterState hides it behind the Life Cycle Mode
        # switch, the write is refused; that is not fatal (an emitter with no spawn module that
        # loops forever is harmless, and the C++ component's fallback timer releases its puff
        # budget regardless), so it is logged rather than escalated.
        try:
            if _stack_input(api, system, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior',
                            '(HlslExpression="Once")', NIAGARA_HLSL):
                applied.append('Loop Behavior=Once')
            else:
                log('Loop Behavior not applied (input hidden behind a switch); left at template '
                    'value. The component releases its puff slot via PuffFallbackLifeSeconds '
                    'regardless, so this is not fatal.')
        except Exception as error:
            log('Loop Behavior not settable (non-fatal): %s' % error)

        save(system, 'NS_GrassFootstepPuff')

        if applied:
            REPORT['patched'].append('NS_GrassFootstepPuff: applied %s' % ', '.join(applied))
        if rejected:
            note_manual(
                'NS_GrassFootstepPuff was created and wired into the DataAsset, but these stack '
                'inputs could NOT be written through the Niagara toolset API: %s. The emitter '
                'therefore still carries its template defaults for them, so VERIFY the live particle '
                'count against the M3 budget (<= %d particles) in the Niagara editor before '
                'accepting the effect. %s' % (', '.join(rejected), PUFF_MAX_PARTICLES, NIAGARA_SPEC))
        return system
    except Exception as error:
        traceback.print_exc()
        REPORT['errors'].append('NS_GrassFootstepPuff authoring failed: %s' % error)
        note_manual('NS_GrassFootstepPuff could not be authored headless; the decal material and '
                    'the DataAsset were still created. ' + NIAGARA_SPEC, error)
        return None


# ---------------------------------------------------------------------------------------------
# DA_GrassFootstepFeedback
#
# The whitelist is the interesting part. UFPSFootstepAudioComponent plays ground steps through
# AutoFootstep with SurfaceType_Default (it classifies the bank by name and passes Default to the
# plugin - see Movement/FPSFootstepAudioComponent.cpp), while the animation notify path passes the
# hit's real physical surface. So a whitelist containing only SurfaceType_Grass would never fire in
# the actual game. This seeds BOTH: Default plus every surface type whose project name reads as
# grass / dirt / soil / gravel, and leaves the final narrowing to the user in the editor.
# ---------------------------------------------------------------------------------------------

# EPhysicalSurface is a plain (unnamespaced) UENUM -- ChaosEngineInterface.h:19-22 declares
# `UENUM(BlueprintType) enum EPhysicalSurface : int` at global scope. The Python binder exposes a
# global enum under its bare name with member names upper-cased, so the attribute is
# unreal.PhysicalSurface and the member is SURFACE_TYPE_DEFAULT. There is no unreal.EPhysicalSurface
# and no unreal.PhysicalSurface.SurfaceType_Default -- both spellings raise AttributeError (verified
# headless on this build). This is the same upper-casing rule as CustomMaterialOutputType above.
SURFACE_ENUM = u.PhysicalSurface
SURFACE_TYPE_DEFAULT = SURFACE_ENUM.SURFACE_TYPE_DEFAULT

# Project surface names that count as "the player walked on soft ground".
GRASS_SURFACE_NAME_HINTS = ('grass', 'dirt', 'soil', 'mud', 'gravel', 'sand')


def build_config(puff, decal):
    path = DEST + '/DA_GrassFootstepFeedback'
    config = load_optional(path)
    if config is None:
        # UDataAssetFactory defaults to the plain UDataAsset class, so the concrete class has to be
        # stated explicitly or the asset would not have the whitelist / asset-reference properties.
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.GrassFootstepFeedbackConfig)
        config = create_asset('DA_GrassFootstepFeedback', u.GrassFootstepFeedbackConfig, factory)
        set_version_tag(config, CONFIG_VERSION_TAG)
    else:
        REPORT['skipped'].append('DA_GrassFootstepFeedback (exists; re-wiring the asset refs)')
        set_version_tag(config, CONFIG_VERSION_TAG)

    # Wire the two assets. Always re-pointed: they are the whole reason this script and the class
    # exist together, and a stale path after a rename would silently disable the trail. The C++
    # properties are TSoftObjectPtr, and the Python binding accepts the UObject directly.
    if puff is not None:
        config.set_editor_property('puff_system', puff)
    else:
        note_manual('DA_GrassFootstepFeedback.PuffSystem was left EMPTY because '
                    'NS_GrassFootstepPuff could not be authored (see the Niagara manual entry). '
                    'The component then falls back to decal + stamp only: the footstep trail still '
                    'works, the particle puff does not.')

    if decal is not None:
        config.set_editor_property('decal_material', decal)
    else:
        note_manual('DA_GrassFootstepFeedback.DecalMaterial was left EMPTY because '
                    'M_GrassTrampleDecal could not be created; point it at the decal material '
                    'by hand or re-run this script.')

    # Seed the whitelist only when it is empty, so a user who narrowed it is never overridden by a
    # re-run of this script.
    existing_surfaces = config.get_editor_property('surfaces')
    if len(existing_surfaces) == 0:
        surfaces = set()
        # SurfaceType_Default is what the running game actually reports (see the note above), so it
        # is always seeded; without it the feature would be inert in the real game loop.
        surfaces.add(SURFACE_TYPE_DEFAULT)
        hinted = 0
        try:
            # UPhysicsSettings::PhysicalSurfaces is the same list UFPSFootstepAudioComponent reads
            # to name its own banks, so the two classifications stay consistent by construction.
            # NOTE: this list is EMPTY in the current project (measured headless 2026-09-26), so the
            # name-hint loop below adds nothing today and the whitelist is {Default}. That is not a
            # failure: Default alone is sufficient for the feature to fire, because the game's own
            # footstep path passes SurfaceType_Default. The loop is kept so that naming surfaces in
            # Project Settings > Physics later is picked up automatically on a re-run -- but only if
            # the whitelist is still empty, which is why the manual note below matters when it is
            # not. Do not narrow the whitelist to nothing: an empty whitelist disables the feature.
            settings = u.get_default_object(u.PhysicsSettings)
            for entry in settings.get_editor_property('physical_surfaces'):
                label = str(entry.get_editor_property('name')).lower()
                if any(hint in label for hint in GRASS_SURFACE_NAME_HINTS):
                    surfaces.add(entry.get_editor_property('type'))
                    hinted += 1
                    log('  + whitelisted surface %s' % label)
        except Exception as error:
            log('could not enumerate physical surfaces (%s); seeding Default only' % error)
        config.set_editor_property('surfaces', surfaces)
        REPORT['patched'].append('DA_GrassFootstepFeedback surface whitelist (%d entries)'
                                 % len(surfaces))
        if hinted == 0:
            note_manual(
                'DA_GrassFootstepFeedback surface whitelist was seeded with SurfaceType_Default '
                'only, because Project Settings > Physics > Physical Surface names are currently '
                'empty, so no surface name reads as grass/dirt/soil. The feature still works: the '
                'game reports SurfaceType_Default for ground steps. If you later name your surface '
                'slots (e.g. "Grass"), either add those types to the whitelist by hand or clear the '
                'Surfaces array and re-run this script, which will pick the names up.')
    else:
        log('surface whitelist already populated (%d entries); leaving it alone'
            % len(existing_surfaces))

    # Runtime budget. Seeded only when the property is still unset, so a user retune survives a
    # re-run. DecalPoolSize = 12 is the plan section 5 pool size (and matches the class default).
    if config.get_editor_property('decal_pool_size') <= 0:
        config.set_editor_property('decal_pool_size', 12)
    if config.get_editor_property('decal_life_seconds') <= 0.0:
        config.set_editor_property('decal_life_seconds', 6.0)
    if config.get_editor_property('puff_max_active') <= 0:
        config.set_editor_property('puff_max_active', PUFF_MAX_PARTICLES)

    save(config, 'DA_GrassFootstepFeedback')
    return config


# ---------------------------------------------------------------------------------------------

def main():
    global _COMPLETED

    log('start ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ensure_directory(DEST)

    # Decal first: it is the asset the C++ component needs to show anything at all, so it is
    # authored before the version-sensitive Niagara step.
    decal = build_decal_material()
    puff = build_puff_system()
    config = build_config(puff, decal)

    if config is not None and len(config.get_editor_property('surfaces')) == 0:
        note_manual(
            'DA_GrassFootstepFeedback has an EMPTY surface whitelist, so the component will stay '
            'inert. Add the physical surfaces that should trigger the grass feedback (and note that '
            'the running game reports SurfaceType_Default for ground steps, so that entry is '
            'normally required).')

    if config is not None:
        # Report the wiring that was actually written, so a reader does not have to trust that the
        # property writes above stuck.
        log('DA_GrassFootstepFeedback: surfaces=%s puff=%s decal=%s pool=%s'
            % (len(config.get_editor_property('surfaces')),
               config.get_editor_property('puff_system'),
               config.get_editor_property('decal_material'),
               config.get_editor_property('decal_pool_size')))

    log('done. created=%s patched=%s skipped=%d manual=%d errors=%d'
        % (REPORT['created'], REPORT['patched'], len(REPORT['skipped']), len(REPORT['manual']),
           len(REPORT['errors'])))

    # main() reached its end: the RESULT block below is now a genuine completion report.
    _COMPLETED = True
    print('GRASS_DEFORM_M3_RESULT ' + repr(REPORT), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        # Only a real, complete run prints the RESULT line. A crash prints an ABORTED line with the
        # partial report instead, so an empty-list RESULT can never read as success.
        if _COMPLETED:
            print('GRASS_DEFORM_M3_RESULT ' + repr(REPORT), flush=True)
        else:
            print('GRASS_DEFORM_M3_ABORTED ' + repr(REPORT), flush=True)
        raise SystemExit(1)