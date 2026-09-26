"""Author NS_FurnaceBlackSmoke: continuous chimney soot plume for the working blast furnace.

Design contract (Docs/Fluids/furnace-black-smoke-20260924.md, v5 plan
Docs/Fluids/furnace-smoke-optimization-plan-20260925.md):
- Reuses the approved Mantaflow rolling smoke surface M_RollingImpactSmoke (T_MuzzleSmokeMantaflowV14,
  per-particle Seed rolling/mirroring; no new bake).
- Three emitters in this ONE system (component pool / <=6 plume cap unchanged):
  FurnaceSmoke   L0 main plume (v4, only gains a User.Heat gate)
  FurnaceSmokeCore  L1 inner roll layer (new, <=6/s, <=2.5s, alpha<=.18, gated by User.L1Gate)
  FurnaceSmokeEvent L2 mouth event layer (new, ignition steam tint + one-shot <=12 puff)
- All emitters CPU, local space, identity-rotated component: local axes == world axes (+Z up).
- Position is a pure function of age (proven impact pattern): buoyant rise, per-particle lateral
  meander (random spread) and integrated User.Wind drift (wind-following).
- Consumes the shared smoke contract: User.SpawnRate / DetailReduction / Wind / SmokePlane0..4 /
  WetImpact; contact approximation from fluid_contact_nodes.
- v5 identity anchor (zero regression): Rain=0 AND Heat=1 => L0 expressions reduce EXACTLY to v4.
Background authoring only: no PIE, preview, screenshot or acceptance run.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/FurnaceSmoke20260924'
DEST = '/Game/Fluids/FurnaceSmoke20260924'
NAME = 'NS_FurnaceBlackSmoke'
MAT = '/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke'
NE_CORE = '/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'
LIFECYCLE_SRC = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'
EMITTER = 'FurnaceSmoke'
CORE = 'FurnaceSmokeCore'      # L1 inner roll layer (v5)
EVENT = 'FurnaceSmokeEvent'    # L2 mouth event layer (v5)
TAG = 'FurnaceSmoke20260924'
TAG_V5 = 'FurnaceSmoke20260925'
# Retired on every run BEFORE re-authoring (known trap: trim() deletes the generated SetVariables
# modules but leaves their metadata tags naming removed instances, which makes the next pass fail
# with "module not found in stack reference"). Unconditional retirement = idempotent convergence.
RETIRED_TAGS = [
    'Fireball.Assignments.%s.ParticleSpawnScript', 'Fireball.Assignments.%s.ParticleUpdateScript',
    'Fireball.Assignments.%s.EmitterSpawnScript', 'Fireball.Assignments.%s.EmitterUpdateScript',
    'FluidContact.%s.ParticleSpawnScript.%d', 'FluidContact.%s.ParticleUpdateScript.%d']
RETIRED_EMITTERS = [EMITTER, CORE, EVENT]
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_slow_burn import smooth
from build_fireball_flight import user_parameter
from fluid_contact_nodes import contact_nodes

E = u.EditorAssetLibrary
INT = '/Script/Niagara.NiagaraInt32'
VEC4 = '/Script/CoreUObject.Vector4f'
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
SAVED = []

# --- plume model (cm, s). Throat geometry MEASURED from the source mesh in Blender
# (SourceAssets/FurnaceSmoke20260924/measure_throat.py -> Saved/furnace_throat.json):
# mouth = vertical cylinder r=18.4, bowl floor z=184, collar top z=220, centre mesh-local (-18,0).
# The runtime places the component at local (-18,0,208) via the Body transform (yaw-correct),
# so age-0 local space here == world-aligned with origin at the throat. ---
THROAT_R = 18.4         # measured opening radius
RATE = 16.0             # nominal particles/s at full detail (User.SpawnRate drives; C++ ramps)
JET = 150.0             # exit velocity at the throat (gas momentum, cm/s)
TERMINAL = 78.0         # buoyant terminal rise speed the jet decays to (cm/s)
JET_TAU = 0.7           # jet -> terminal decay constant (entrainment/drag)
LIFE = (2.6, 3.6)       # particle lifetime band
SIZE0 = 27.0            # birth sprite size — v4 softened up (was 24): larger+softer puffs kill the hard circular outline at the mouth; still under the 36.8cm throat so puffs squeeze out
MAX_AGE = LIFE[1]

# --- v5 L1 inner core layer: big, slow, dark, low-alpha cards filling the INSIDE of the column.
# Budget (plan §5/§9): <=6/s, life <=2.5s => <=15 particles; alpha cap .18; only <35m AND quality>=medium
# (User.L1Gate is written by C++), and always multiplied by the shared User.DetailReduction.
CORE_SIZE0 = 40.0       # birth size; grows 40 -> 110cm (large slow cards replace the fine fast muzzle grain)
CORE_SIZE1 = 110.0
CORE_RATE = 6.0
CORE_LIFE = (1.6, 2.5)
CORE_ALPHA = 0.18       # hard cap: inner layer must never build a second opaque silhouette
# --- v5 L2 mouth event layer: ignition steam (grey-white mixing to black over 4s, mirroring
# User.Ignition) plus a one-shot <=12 particle puff when User.Puff spikes at a batch boundary. ---
EVENT_PUFF_MAX = 12
EVENT_RATE = 8.0        # <=8/s while an event (ignition or puff) is live; gated to 0 otherwise
IGNITION_SECONDS = 4.0  # must match the C++ normalisation (UpdateFurnaceSmoke)


def save(asset):
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compile failed: ' + asset.get_path_name())
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    u.log('FURNACE_SMOKE_SAVED ' + asset.get_path_name())


def system_asset():
    path = DEST + '/' + NAME
    if E.does_asset_exist(path):
        return u.load_asset(path)
    made = u.AssetToolsHelpers.get_asset_tools().create_asset(
        NAME, DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    if not made:
        raise RuntimeError('Cannot create ' + path)
    return made


def declare(system):
    existing = str(API.call_method('GetUserVariables', (system,)).export_text())
    # v5 adds Heat / Ignition / Puff / L1Gate — all written by UFluidPresentationSubsystem::UpdateFurnaceSmoke
    # at 5Hz (parameter names are compile-time constants on the C++ side; nothing is concatenated per tick).
    for name, typ in [('SpawnRate', FLOAT), ('Wind', VEC3), ('DetailReduction', FLOAT),
                      ('WetImpact', FLOAT), ('Rainfall', FLOAT),
                      ('Heat', FLOAT), ('Ignition', FLOAT), ('Puff', FLOAT), ('L1Gate', FLOAT)]:
        if 'User.' + name not in existing:
            user_parameter(system, name, typ)


def lifecycle(system, emitter):
    src = u.load_asset(LIFECYCLE_SRC)
    mode = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    # ENiagaraEmitterLifeCycleMode: NewEnumerator1 == Self; ENiagara_EmitterStateOptions: NewEnumerator0 == Infinite.
    # 'Self' is mandatory here: NE_Core's default is System, which would kill the extra emitters as soon
    # as the system's own lifetime elapsed.
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)


def retire_tags(system):
    """Unconditionally drop last round's assignment/contact tags for EVERY furnace emitter.

    trim() removes the generated SetVariables_<guid> modules but leaves their metadata tags naming
    instances that no longer exist; on the next pass assignments()/contact_nodes() would look the tag
    up and try to write into a dead module ("在堆栈引用中未找到模块"). Retiring first makes the run
    idempotent: both helpers then recreate fresh modules in the correct order (assignments first,
    contact projections last). Covers the v4 (FurnaceSmoke20260924) and v5 (FurnaceSmoke20260925) tags.
    """
    for emitter in RETIRED_EMITTERS:
        for pattern in RETIRED_TAGS:
            if '%d' in pattern:
                for i in range(5):
                    E.remove_metadata_tag(system, pattern % (emitter, i))
            else:
                E.remove_metadata_tag(system, pattern % emitter)


def ensure_emitter(system, emitter):
    if emitter not in emitters(system):
        API.call_method('AddEmitter', (system, u.load_asset(NE_CORE), emitter))
        if emitter not in emitters(system):
            raise RuntimeError('Cannot add emitter ' + emitter)
    trim(system, emitter, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState']})
    # Continuous spawn via the project-proven SpawnRate module (handles dt + fractional accumulation
    # internally; its rate input binds User.* variables). NE_Core lacks it, so add. Never author a
    # custom spawn expression with Engine.Environment.DeltaTime — that binding is unavailable in
    # SetParameters and fails VectorVM compilation (learned on the v2 draft).
    stale = E.get_metadata_tag(system, 'Fireball.Assignments.' + emitter + '.EmitterSpawnScript')
    if stale:
        API.call_method('RemoveModule', (ref(system, emitter, 'EmitterSpawnScript', str(stale)),))
        E.remove_metadata_tag(system, 'Fireball.Assignments.' + emitter + '.EmitterSpawnScript')
    topo = API.call_method('GetEmitterTopology', (ref(system, emitter),))
    stack = topo.get_editor_property('emitter_update_script')
    if not any(str(m.get_editor_property('module_name')) == 'SpawnRate' for m in stack.get_editor_property('modules')):
        API.call_method('AddModule', (ref(system, emitter, 'EmitterUpdateScript'),
                                      u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter), {
        'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    lifecycle(system, emitter)


def renderer(system, emitter, subuv=(1, 1)):
    """Shared smoke renderer contract: approved material, no shadow, 85m distance cull."""
    mat = u.load_asset(MAT)
    if not mat:
        raise RuntimeError('Missing approved rolling smoke material ' + MAT)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, emitter, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': subuv[0], 'Y': subuv[1]}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 8500})


def streams(phase, salt):
    """Three per-particle variation streams + a per-emitter salt.

    Each emitter derives its own seed/mirror/flipbook phase from the same UniqueID*irrational recipe
    but with a different additive salt, so L0/L1/L2 never march in lockstep even on the same particle
    index (plan §1: independent seed / mirror / flipbook phase).
    """
    return (f'frac(float(Particles.UniqueID)*.61803398875+{phase}+{salt})',
            f'frac(float(Particles.UniqueID)*.41421356237+{phase}*.731+{salt}*.37)',
            f'frac(float(Particles.UniqueID)*.75487766623+{phase}*.411+{salt}*.59)')


def author_core(system, phase):
    """L1 inner roll layer: large, slow, dark, low-alpha cards inside the main column.

    Budget: <=6/s * <=2.5s => <=15 particles/plume (plan §5). Gated by User.L1Gate (distance<35m AND
    quality>=medium, written in C++) and always multiplied by the shared User.DetailReduction so the
    low-quality / far path drops this layer FIRST. Alpha is hard-capped at CORE_ALPHA=.18: the inner
    layer adds internal density motion, it must never build a second opaque silhouette.
    Motion is 0.6x the main column's speed, with its own seed/mirror/flipbook phase (plan §1).
    """
    ensure_emitter(system, CORE)
    gate = 'saturate(User.L1Gate)*(1-saturate(User.DetailReduction))'
    put(system, CORE, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="max(0,{CORE_RATE})*{gate}")', HL)
    renderer(system, CORE)
    seed, var, u2 = streams(phase, 0.137)
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    ang = f'{u2}*6.2831853'
    # Tighter birth disc than L0 (r*0.55): the core stays INSIDE the column instead of widening it.
    rad = f'{THROAT_R * 0.55}*sqrt({var})'
    # 0.6x slow rise: same buoyant shape, 60% of the main speed => reads as the heavy inner body.
    rise = f'0.6*({TERMINAL}*{a}+({JET}-{TERMINAL})*{JET_TAU}*(1-exp(-{a}/{JET_TAU})))'
    gatez = smooth('10', '55', rise)
    spread = f'float3(cos({ang}),sin({ang}),0)*{gatez}*(1.6+1.8*{a})'
    curl = (f'float3(sin({a}*(.62+.5*{seed})+{seed}*6.2831853),'
            f'cos({a}*(.48+.44*{var})+{u2}*6.2831853),0)')
    billow = f'{curl}*(2.2+3.4*{a})*(.6+.6*{u2})'
    w = f'({a}-.75*(1-exp(-{a}/.75)))'          # slower wind uptake than L0 (heavier body lags)
    position = (f'float3({rad}*cos({ang}),{rad}*sin({ang}),-3+4*{seed})'
                + f'+float3(0,0,{rise})+{spread}+{billow}+User.Wind*{w}*.65')
    size = (f'float2({CORE_SIZE0},{CORE_SIZE0 * 1.06})*(.86+.3*{u2})'
            + f'*lerp(1,{CORE_SIZE1 / CORE_SIZE0},saturate(sqrt({a}/{CORE_LIFE[1]})))')
    envelope = smooth('0', '.3', n) + '*(1-' + smooth('.45', '.95', n) + ')'
    fade = f'saturate((8500-Engine.Owner.LODDistance)/2500)'
    # Deep grey, darker than the L0 birth tone (adds depth without opacity): lerp toward near-black.
    tint = f'lerp(float3(.030,.029,.031),float3(.055,.052,.052),{smooth(".1","1",n)})*(.85+.3*{var})'
    color = f'float4({tint},{CORE_ALPHA}*{envelope}*{fade}*saturate(User.L1Gate))'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'({u2}-.5)*6.2831853+{a}*({var}-.5)*.55'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)')}
    assignments(system, CORE, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, f'({CORE_LIFE[0]}+{CORE_LIFE[1] - CORE_LIFE[0]}*{seed})'), **common})
    assignments(system, CORE, 'ParticleUpdateScript', common)
    contact_nodes(system, CORE)


def author_event(system, phase):
    """L2 mouth event layer: ignition steam plus the one-shot batch-completion puff.

    Two jobs in one emitter, both driven by C++-written User params:
      * Ignition: while User.Ignition < 1 the birth colour is a pale grey-white steam (bright, fast
        dissipating, buoyancy suppressed) that mixes to black over IGNITION_SECONDS; the SAME ramp is
        what the C++ side normalises, so the visual and the data agree by construction.
      * Puff: User.Puff spikes to 1 at a whole-batch boundary and decays linearly over 1.2s. The layer
        only spawns while an event is live, at <=EVENT_RATE/s, so a one-shot burst stays <=EVENT_PUFF_MAX
        particles. Dead-band elsewhere: rate is exactly 0 when Ignition>=1 and Puff<=0.
    """
    ensure_emitter(system, EVENT)
    ign = f'saturate(User.Ignition)'
    puff = f'saturate(User.Puff)'
    # Live = steam still mixing (ign<1) OR a puff window is open. Both terms -> 0 in steady state, so
    # this emitter costs nothing during normal full-heat operation (plan §5: budget from L0's slack).
    # Distance/quality gating uses LODDistance (plan §9 puts L2 at <50m) rather than User.L1Gate, so the
    # event layer is NOT collateral damage when the 35m inner-core gate closes.
    live = f'saturate(max(1-{ign},{puff}))'
    far = f'saturate((5000-Engine.Owner.LODDistance)/1200)'
    gate = f'{live}*{far}*(1-saturate(User.DetailReduction))'
    put(system, EVENT, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="max(0,{EVENT_RATE})*{gate}")', HL)
    renderer(system, EVENT)
    seed, var, u2 = streams(phase, 0.271)
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    ang = f'{u2}*6.2831853'
    rad = f'{THROAT_R * 0.7}*sqrt({var})'
    # Steam rises fast and dies young; a puff is pushed out hard then settles. lerp by the puff share
    # so the two regimes coexist inside one emitter without a second spawn path.
    steam_rise = f'1.35*({TERMINAL}*{a}+({JET}-{TERMINAL})*{JET_TAU}*(1-exp(-{a}/{JET_TAU})))'
    puff_rise = f'1.5*({TERMINAL}*{a})'
    rise = f'lerp({steam_rise},{puff_rise},{puff})*(1-.45*{ign})'   # wet steam loses buoyancy
    spread = f'float3(cos({ang}),sin({ang}),0)*(2.5+3.2*{a})'
    curl = (f'float3(sin({a}*(1.6+1.2*{seed})+{seed}*6.2831853),'
            f'cos({a}*(1.3+1.1*{var})+{u2}*6.2831853),0)')
    billow = f'{curl}*(2+3*{a})*(.7+.5*{u2})*(1+.8*{puff})'
    position = (f'float3({rad}*cos({ang}),{rad}*sin({ang}),-3+5*{seed})'
                + f'+float3(0,0,{rise})+{spread}+{billow}+User.Wind*({a}-.5*(1-exp(-{a}/.5)))')
    # Steam puffs are born large and balloon fast (a visible mouth burp); the mix collapses quickly.
    size = (f'float2({SIZE0 * 1.15},{SIZE0 * 1.32})*(.8+.45*{u2})'
            + f'*(.95+.7*sqrt({a}))*(1+.55*{puff})')
    # Steam envelope: fast fade-in, fast out (it is water vapour, not soot).
    envelope = smooth('0', '.12', n) + '*(1-' + smooth('.35', '.85', n) + ')'
    fade = f'saturate((8500-Engine.Owner.LODDistance)/2500)'
    # Colour: grey-white steam (ign=0) -> the approved L0 soot grey (ign=1). The steam is deliberately
    # brighter AND its alpha is a touch higher so the cold-start burp reads over the black column.
    base = f'lerp(float3(.050,.048,.050),float3(.088,.084,.080),{smooth(".1","1",n)})'
    steam_tint = f'float3(.42,.43,.45)'
    tint = f'lerp({base},{steam_tint},(1-{ign})*(1-{puff}))*(.85+.3*{var})'
    color = f'float4({tint},(.20+.10*{seed})*{envelope}*{fade}*(1+.35*(1-{ign}))*saturate(max(1-{ign},{puff})))'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'({u2}-.5)*6.2831853+{a}*({var}-.5)*.9'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)')}
    # Short life: a steam burp must clear well inside the 4s ignition ramp and inside the 1.2s puff.
    life = f'(.9+.9*{seed})*(1-.35*{ign})*(1+.5*{puff})'
    assignments(system, EVENT, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, life), **common})
    assignments(system, EVENT, 'ParticleUpdateScript', common)
    contact_nodes(system, EVENT)


def author():
    E.make_directory(DEST)
    system = system_asset()
    retire_tags(system)          # must precede any add/trim: stale tags would name deleted modules
    declare(system)
    ensure_emitter(system, EMITTER)
    # L0 rate: base v4 expression, then the v5 Heat gate. Identity anchor: Heat=1 -> (0.55+0.45*1)=1,
    # so the expression collapses to exactly the v4 formula. Only Rain=0 and Heat=1 keep L0 bit-identical.
    put(system, EMITTER, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,User.SpawnRate)*(1-saturate(User.DetailReduction))*(1-.25*User.Rainfall)*(.55+.45*saturate(User.Heat))")', HL)
    renderer(system, EMITTER)

    # Decorative variation: three per-particle streams from UniqueID plus a system-wide phase
    # (re-seeded on pool reuse) so neighbouring plumes never march in lockstep.
    phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
    seed, var, u2 = streams(phase, 0.0)
    a = 'Particles.Age'
    n = 'Particles.NormalizedAge'
    ang = f'{u2}*6.2831853'                                          # throat-disc azimuth
    rad = f'{THROAT_R * 0.82}*sqrt({var})'                           # area-uniform inside the r=18.4 throat
    rain = 'User.Rainfall'                                            # 0..1 from weather (C++ writes it)
    # Buoyant column: jet exit speed decays exponentially to a terminal rise (real chimney plumes
    # leave the throat fast, then entrain air and settle). Integral of v(t)=vt+(v0-vt)exp(-t/tau).
    rise = (f'({TERMINAL}*{a}+({JET}-{TERMINAL})*{JET_TAU}*(1-exp(-{a}/{JET_TAU})))')
    gate = smooth('10', '55', rise)                                  # stay a tight column until clear of the collar
    spread = f'float3(cos({ang}),sin({ang}),0)*{gate}*(3+3.4*{a})'   # conical fanning only after clearing the rim
    curl = (f'float3(sin({a}*(1.05+.95*{seed})+{seed}*6.2831853),'
            f'cos({a}*(.8+.75*{var})+{u2}*6.2831853),0)')
    billow = f'{curl}*(2.5+4.2*{a})*(.65+.6*{u2})'                    # turbulence growing with puff size
    w = f'({a}-.55*(1-exp(-{a}/.55)))'                               # integrated wind ramp (lags near source)
    # Rain tearing (v3): per-particle double-frequency sway (frequency+phase from each stream) with a
    # small downward push (drops beat the puff down); amplitude grows with age so the column shreds.
    sway = (f'float3(sin({a}*(2.1+2.4*{seed})+{seed}*6.2831853)+.5*sin({a}*(4.3+3*{u2})+{u2}*6.2831853),'
            f'cos({a}*(1.7+2.1*{u2})+{u2}*6.2831853)+.5*cos({a}*(3.7+3*{seed})+{seed}*6.2831853),'
            f'-.35*min(2,{a}))*{rain}*(1.8+9*{a})')
    position = (f'float3({rad}*cos({ang}),{rad}*sin({ang}),-4+6*{seed})'
                + f'+float3(0,0,{rise}*(1-.45*{rain}))+{spread}+{billow}+{sway}'
                + f'+User.Wind*{w}*(1+2.2*{rain})')
    # Size: squeeze out under throat width, then sqrt expansion (fast entrainment, slowing).
    size = (f'float2({SIZE0},{SIZE0 * 1.08})*(.82+.42*{u2})'
            + f'*(.9+.85*sqrt({a})*(1+.5*{rain}))*lerp(1,1.16,{smooth(".4", "1", n)})')
    # Visible life shortens in rain: the fade-out hold pulls forward (dissipation mode shifts from
    # "rise tall and thin out" to "shear low and blow apart"), and spawn-time lifetime is scaled too.
    envelope = (smooth('0', '.22', n) + '*(1-'
                + smooth(f'(.55-.4*{rain})', f'(1-.35*{rain})', n) + ')')   # v4: slower fade-in (.07→.22) so puffs don't pop at full opacity = no sharp first-frame edge
    dist = 'Engine.Owner.LODDistance'
    fade = f'saturate((8500-{dist})/2500)'
    # Grayscale layering: dark dense soot core at birth lightening as it thins; per-particle
    # seed drives both density and tone so the column reads volumetric, not flat.
    # Grayscale layering — v4: birth starts at the SAME gray family as the dissipating top
    # (was near-black .016 → hard scalloped silhouette where opaque cards overlapped).
    # Only a gentle dark→light ramp remains, so the whole column reads like the soft grey the user liked.
    tint0 = (f'lerp(float3(.050,.048,.050),float3(.088,.084,.080),'
             f'{smooth(".1", "1", n)})*(.82+.36*{var})')
    # v5 Heat gate on tone/density: identity anchor at Heat=1 -> (1-.30*(1-1))=1, so both factors are
    # exactly 1 and the v4 expressions are reproduced verbatim. Idle ember (.25) thins and lightens;
    # a full batch (1.0) reads as dense black soot. Never touches SpawnRate semantics beyond the gate.
    heat = 'saturate(User.Heat)'
    tint = f'{tint0}*(1-.40*(1-{heat}))'
    alpha0 = f'(({.26}+{.12}*{seed}))*{envelope}*{fade}*(1-.28*{rain})'
    color = f'float4({tint},{alpha0}*(.55+.45*{heat}))'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'({u2}-.5)*6.2831853+{a}*({var}-.5)*.8'),   # full random pose + slow drift
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)')}
    assignments(system, EMITTER, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, f'({LIFE[0]}+{LIFE[1]-LIFE[0]}*{seed})*(1-.38*User.Rainfall)'), **common})
    assignments(system, EMITTER, 'ParticleUpdateScript', common)
    # Contact projections last, on top of the authored motion (shared smoke-plane approximation).
    contact_nodes(system, EMITTER)
    author_core(system, phase)
    author_event(system, phase)
    E.set_metadata_tag(system, TAG_V5, (
        'v5 three-layer soot plume; L0 FurnaceSmoke (v4 + Heat gate) / L1 FurnaceSmokeCore '
        f'(rate {CORE_RATE}/s, life {CORE_LIFE}, size {CORE_SIZE0}->{CORE_SIZE1}, alpha<={CORE_ALPHA}, L1Gate) / '
        f'L2 FurnaceSmokeEvent (ignition steam tint via User.Ignition, one-shot <={EVENT_PUFF_MAX} puff via User.Puff); '
        'identity anchor Rain=0 and Heat=1 reduces L0 to v4 verbatim; shared M_RollingImpactSmoke; '
        'params User.Heat/Ignition/Puff/L1Gate written at 5Hz by UFluidPresentationSubsystem'))
    E.set_metadata_tag(system, TAG, f'Soot plume v4; throat r={THROAT_R} measured; jet {JET}->{TERMINAL} cm/s tau {JET_TAU}; rate {RATE}/s; life {LIFE}; rain-gust coupling; SOFTENED birth (grey {.05}, alpha {.26}, size {SIZE0}, fade-in .22) to match dissipating top; shared M_RollingImpactSmoke')
    save(system)
    return system


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if (DEST + '/' + NAME) in dirty:
        raise RuntimeError('Target package has unsaved changes; preserve them')
    system = author()
    (OUT / 'assets.json').write_text(json.dumps({
        'saved': SAVED, 'material_reused': MAT, 'atlas': '/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14',
        'throat': {'centre_local_cm': [-18, 0, 208], 'opening_radius_cm': THROAT_R,
                   'measured_from': 'Saved/furnace_throat.json (Blender ray profile)'},
        'rise_model': {'exit_cm_s': JET, 'terminal_cm_s': TERMINAL, 'tau_s': JET_TAU},
        'rain_coupling': {'param': 'User.Rainfall (C++ UpdateFurnaceSmoke @5Hz + RainGust random-direction wind)',
                          'buoyancy_cut': .45, 'wind_boost': 2.2, 'fade_hold_at_full': .15,
                          'lifetime_cut': .38, 'rate_cut': .25, 'size_growth_boost': .5},
        'rate_per_second': RATE, 'life': LIFE, 'birth_size_cm': SIZE0,
        'birth_softening_v4': {'grey_start_rgb': [.050, .048, .050], 'grey_end_rgb': [.088, .084, .080],
                               'alpha': '0.26+0.12*seed (was 0.44+0.16)', 'fade_in_norm_age': .22,
                               'note': 'user: hard black outline at mouth looked fake; unified toward the soft grey top'},
        'max_particles_per_plume': int(RATE * LIFE[1] * 1.15),
        'emitters_v5': {
            'L0_main': {'name': EMITTER, 'rank': f'{RATE}/s', 'life': LIFE,
                        'heat_gate': 'rate/alpha/tone all multiplied by (.55+.45*Heat) style factors that are 1 at Heat=1 (v4 identity anchor)'},
            'L1_core': {'name': CORE, 'rate': CORE_RATE, 'life': CORE_LIFE,
                        'size_cm': [CORE_SIZE0, CORE_SIZE1], 'alpha_cap': CORE_ALPHA,
                        'speed_vs_main': 0.6, 'gate': 'User.L1Gate (C++: dist<3500cm AND EffectsQuality>=1) x (1-DetailReduction)',
                        'peak_particles': int(CORE_RATE * CORE_LIFE[1] * 1.15)},
            'L2_event': {'name': EVENT, 'rate': EVENT_RATE, 'puff_max': EVENT_PUFF_MAX,
                         'gate': 'saturate(max(1-User.Ignition, User.Puff)) x <50m LOD fade x (1-DetailReduction)',
                         'note': 'ignition steam grey-white -> soot black over User.Ignition; puff one-shot at batch boundary'}},
        'peak_particles_per_plume_v5': int(RATE * LIFE[1] * 1.15) + int(CORE_RATE * CORE_LIFE[1] * 1.15) + EVENT_PUFF_MAX,
        'identity_anchor': 'Rain=0 and Heat=1 => every L0 expression reduces verbatim to v4; L1/L2 gate to 0 when their gates are 0',
        'status': 'authored_compiled_saved; not game or visually tested'}, indent=2), encoding='utf8')
    u.log('FURNACE_SMOKE_COMPLETE ' + system.get_path_name())


if __name__ == '__main__':
    main()
