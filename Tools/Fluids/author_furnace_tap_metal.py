"""Author NS_FurnaceMoltenTap: molten metal tap stream + pool + sparks + ingot afterglow.

Design contract (Docs/Fluids/furnace-tap-metal-20260925.md):
- Event: the smelting job on a blast furnace completes (IsDone predicate:
  LiveProgress >= JobTotalSeconds, job still in the furnace, not yet collected).
  ONE rise edge fires the stream; the ingot stays visible until the job is taken out.
- Anchor geometry is authored mesh-local (SM_BlastFurnace, cm, quarter-turn invariant):
  tap hole arch mouth (17.5, 0, 69.4) -> gun-drilled +X channel (20.5, 0, 63.5)
  -> wide exit in the shaft face (24.7, 0, 63.5) -> gravity arc -> casting-bed top
  ((32.9, 0, 20), measured from the authored launder arc). No collision queries.
- Four emitters in this ONE system (the C++ TapTemplate points at this asset; the
  component pool is capped at 4 taps, one component per furnace):
  FurnaceTapMetalFlow  L0 molten stream (analytic parabola + micro noise, hard cap 30 live)
  FurnaceTapPool       L1 landing pool (one card, expand -> cool -> contract in 2.5s)
  FurnaceTapSpark      L3 splash sparks (one-shot <=12, User.SparkGate)
  FurnaceTapIngotGlow  L2 ingot afterglow card (3s decay, User.IngotGlow)
- All four emitters are CPU / local space; the component is attached to the furnace
  Body component with identity relative rotation, so local +X is the furnace's
  machined tap direction in every placement yaw.
- Programmatic material M_TapMetalFlow (unlit emissive, additive, procedural hex
  cells + scrolling noise). No new bitmap: the noise is generated in HLSL.
- Consumes User.Flow / User.SparkGate / User.IngotGlow, written by
  UFluidPresentationSubsystem::UpdateFurnaceSmoke at 5Hz (compile-time constants).
Background authoring only: no PIE, preview, screenshot or acceptance run.
"""
import ast
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/FurnaceTapMetal20260925'
DEST = '/Game/Fluids/FurnaceTapMetal20260925'
# 2026-09-26 实测教训：资产名不得是任何发射器名的前缀。NS_FurnaceTapMetal 是
# FurnaceTapMetalFlow 的前缀时，同一进程内逐字节相同的内容在 NS_FurnaceTapMetal2 /
# NS_ProbeTap* 名下 compile valid=1，在该名下必 valid=0（SystemUpdateScript 出现
# 引用 User.DetailReduction 的幻影 Custom Hlsl 节点；无文件/注册表/DDC 残留，探针
# probe_tap_name_cache.py 可复现）。故定名 NS_FurnaceMoltenTap（非任何发射器名前缀）。
NAME = 'NS_FurnaceMoltenTap'
MAT_NAME = 'M_TapMetalFlow'
MAT = DEST + '/' + MAT_NAME
NE_CORE = '/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'
LIFECYCLE_SRC = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'
FLOW = 'FurnaceTapMetalFlow'      # L0 main molten stream
POOL = 'FurnaceTapPool'           # L1 landing pool card
SPARK = 'FurnaceTapSpark'         # L3 splash sparks
GLOW = 'FurnaceTapIngotGlow'      # L2 ingot afterglow card
EMITTERS = [FLOW, POOL, SPARK, GLOW]
TAG = 'FurnaceTapMetal20260925'

# --- retired on EVERY run before any add/trim (known trap: trim() deletes the generated
# SetVariables modules but leaves their metadata tags naming removed instances, which makes the
# next pass fail with "module not found in stack reference"). Unconditional retirement of the
# previous round's tags = idempotent convergence. Covers the fireball family tags used by the
# shared helpers, the fluid contact projections, and both furnace smoke rounds. ---
RETIRED_TAGS = [
    'Fireball.Assignments.%s.ParticleSpawnScript', 'Fireball.Assignments.%s.ParticleUpdateScript',
    'Fireball.Assignments.%s.EmitterSpawnScript', 'Fireball.Assignments.%s.EmitterUpdateScript',
    'FluidContact.%s.ParticleSpawnScript.%d', 'FluidContact.%s.ParticleUpdateScript.%d']
RETIRED_EMITTERS = EMITTERS + [
    'FurnaceSmoke', 'FurnaceSmokeCore', 'FurnaceSmokeEvent',      # FurnaceSmoke20260924 (v4/v5)
    'FurnaceTapMetalFlow', 'FurnaceTapPool', 'FurnaceTapSpark', 'FurnaceTapIngotGlow']
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
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

# --- authored geometry (cm, SM_BlastFurnace mesh local). See the module docstring:
# every number below is either a manifest interface point or derived from the authored
# casting-bed launder/ingot-mould arc in SourceAssets/BlastFurnace20260923. ---
TAP_ARCH_X = 17.5          # manifest TapHole (x); the arch pierces the shaft face at z=69.4
TAP_ARCH_Z = 69.4
TAP_CHANNEL_Z = 63.5       # manifest TapHole (z): bottom of the +X gun-drilled channel
TAP_EXIT_X = 24.7          # wide arch exit in the shaft face (wall r=18.45 + breast 6.25)
BED_X = 32.9               # measured landing point on the casting-bed top (length=30.0)
BED_Z = 20.0               # CAST_BED z1 = MOULD_Z = 20.0 cm
POOL_Z = 21.2              # pool card centre: 1.2 cm above the bed top
INGOT_X = 45.0             # manifest ForehearthFloor/MOULD_X = 45.0 (mould arc centre)
GRAVITY = 600.0            # cm/s^2, the visual gravity of the arc (balanced below)
FLIGHT = 0.43              # seconds of fall from the tap exit to the bed
V0X = (BED_X - TAP_EXIT_X) / FLIGHT              # 17.44 cm/s
V0Z = -(.5 * GRAVITY * FLIGHT * FLIGHT) / FLIGHT  # -129.0 cm/s: v0z = -g*t/2 for z(t) = -g t^2/2
ARCH_HALF = 7.0            # tap arch half width, measured in the authored cutter
ARCH_TOP = 3.6             # birth band half height inside the mouth (stays inside the opening)
FLOW_LIFE = (2.1, 2.4)     # verified band: mean 2.247 s because emissions are time-uniform
FLOW_COUNT = 16            # emission rate while User.Flow=1 -> 16*2.247 = 35.9 < 36 = LIVE_CAP
LIVE_CAP = 36              # hard cap on live particles (design budget <=30, +20% headroom)
STREAM_R0 = 1.55           # stream radius at the mouth (cm)
POOL_GROW = 0.30           # L1 expansion time (s)
POOL_COOL = 2.50           # L1 cool+contract time (s, design contract)
SPARK_LIFE = (0.45, 0.80)
SPARK_COUNT = 12           # one-shot particle count (normalised to 0 -> one burst)
GLOW_LIFE = 3.0            # L2 afterglow decay (s, design contract)
GLOW_SECONDS = 3.6         # activation window: the card fully fades at 3.0 s


def save(asset):
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compile failed: ' + asset.get_path_name())
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    u.log('FURNACE_TAP_SAVED ' + asset.get_path_name())


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
    for name, typ in [('Flow', FLOAT), ('SparkGate', FLOAT), ('IngotGlow', FLOAT),
                      ('Seed', FLOAT), ('DetailReduction', FLOAT)]:   # DetailReduction 必须声明（Custom HLSL 只认已声明 User 参数；黑烟脚本同款）
        if 'User.' + name not in existing:
            user_parameter(system, name, typ)


def lifecycle(system, emitter):
    src = u.load_asset(LIFECYCLE_SRC)
    mode = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    # NewEnumerator1 == Self (NE_Core defaults to System, which would kill every extra
    # emitter as soon as the system's own lifetime elapsed); NewEnumerator0 == Infinite.
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)


def retire_tags(system):
    """Unconditionally drop last round's assignment/contact tags for every known emitter."""
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
    # Flush one-shot emitters must not keep the NE_Core SpawnBurst; everything here is
    # driven by the project-proven SpawnRate module (handles dt + fractional accumulation)
    # or by SpawnBurst with an explicit normalised-time trigger.
    topo = API.call_method('GetEmitterTopology', (ref(system, emitter),))
    modules = topo.get_editor_property('emitter_update_script').get_editor_property('modules')
    names = [str(m.get_editor_property('module_name')) for m in modules]
    if 'SpawnBurst' in names and not any(n.startswith('SpawnBurst') and n != 'SpawnBurst' for n in names):
        API.call_method('RemoveModule', (ref(system, emitter, 'EmitterUpdateScript', 'SpawnBurst'),))
        modules = API.call_method('GetEmitterTopology', (ref(system, emitter),)).get_editor_property('emitter_update_script').get_editor_property('modules')
        names = [str(m.get_editor_property('module_name')) for m in modules]
    if not any(n == 'SpawnRate' for n in names):
        API.call_method('AddModule', (ref(system, emitter, 'EmitterUpdateScript'),
                                      u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter), {
        'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    lifecycle(system, emitter)


def spawn_burst(system, emitter, count):
    """Explicit one-shot burst: SpawnBurst fires when NormalizedEmitterAge crosses the
    trigger (default 0), i.e. once at activation, independent of the 5Hz gate timing."""
    API.call_method('AddModule', (ref(system, emitter, 'EmitterUpdateScript'),
                                  u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    module = ''
    for module_name in ['SpawnBurst_Instantaneous', 'SpawnBurst']:
        if E.get_metadata_tag(system, 'Fireball.Assignments.' + emitter + '.EmitterUpdateScript') == module_name:
            module = module_name
    stack = API.call_method('GetEmitterTopology', (ref(system, emitter),)).get_editor_property('emitter_update_script')
    for m in stack.get_editor_property('modules'):
        if str(m.get_editor_property('module_name')).startswith('SpawnBurst'):
            module = str(m.get_editor_property('module_name'))
    if not module:
        raise RuntimeError('SpawnBurst module missing on ' + emitter)
    put(system, emitter, 'EmitterUpdateScript', module, 'Spawn Count', '(Value=%d)' % count,
        '/Script/Niagara.NiagaraInt32')   # int 输入必须显式 Int32 类型（先例：author_river_pilot/muzzle_smoke_v15）
    put(system, emitter, 'EmitterUpdateScript', module, 'Spawn Time', '(Value=0)')
    # 注意：本引擎版 SpawnBurst_Instantaneous 没有 'Spawn Probability' 输入（set_input 会失败）；
    # 全部先例（river_pilot/muzzle_smoke_v15/fireball 系）都只设 Count+Time，默认概率即 1。


def renderer(system, emitter, subuv=(1, 1), cull=8500.0, pivot=(.5, .5)):
    mat = u.load_asset(MAT)
    if not mat:
        raise RuntimeError('Missing authored molten metal material ' + MAT)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, emitter, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': subuv[0], 'Y': subuv[1]}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': pivot[0], 'Y': pivot[1]}, 'Alignment': 'Unaligned',
        'FacingMode': 'FaceCamera', 'bCastShadows': False, 'CutoutTexture': None,
        'bUseMaterialCutoutTexture': False, 'bEnableCameraDistanceCulling': True,
        'MinCameraDistance': 0, 'MaxCameraDistance': cull})


def streams(phase, salt):
    """Three per-particle variation streams + a per-emitter salt (independent seed /
    mirror / flicker phase per layer) from the shared irrational-increment recipe."""
    return (f'frac(float(Particles.UniqueID)*.61803398875+{phase}+{salt})',
            f'frac(float(Particles.UniqueID)*.41421356237+{phase}*.731+{salt}*.37)',
            f'frac(float(Particles.UniqueID)*.75487766623+{phase}*.411+{salt}*.59)')


def mouth_origin(r_out, seed):
    """Birth point: a small disc in the YZ plane at the arch mouth plus a +X gun-drill run.

    r_out is the drilled radius at that point (smaller at the mouth, wider at the shaft
    exit), fed per particle so the jet widens exactly inside the tap channel.
    """
    ang = f'({seed}*2.39996323)'
    pos = (f'float3({TAP_ARCH_X}+1.25*{seed},'
           f'{r_out}*sqrt({seed})*cos({ang}),{TAP_CHANNEL_Z}+{r_out}*sqrt({seed})*sin({ang}))')
    vel = (f'float3({V0X},{V0X}*.10*({seed}-.5),{V0Z}+3.5*({seed}-.5))')
    return pos, vel


def author_flow(system, phase):
    """L0 molten stream: analytic parabola from the tap channel to the casting bed.

    Position is a pure function of age (the component never moves between spawn and
    update in the same frame): dead-straight +X run inside the arch, gravity drop from
    the shaft exit, then a gravity-only fall with a small per-particle noise term.
    Birth colour runs white-hot core -> gold -> orange rim; the tail cools and dims.
    """
    ensure_emitter(system, FLOW)
    put(system, FLOW, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,%d)*saturate(User.Flow)*(1-saturate(User.DetailReduction))")' % FLOW_COUNT, HL)
    renderer(system, FLOW)
    seed, var, u2 = streams(phase, 0.0)
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    # Drilled radius: r = 2.4*sqrt(1-(z-62.45)/2.1) at the mouth, widening to 3.9.
    r_mouth = '2.4*sqrt(saturate(1-(Particles.Position.z-62.45)/2.1))'
    r_exit = '3.9'
    # Dead straight run inside the channel: advance +X at 2.3x the ballistic speed while
    # the particle is still behind the shaft face, then hand over to the parabola.
    straight = f'({TAP_EXIT_X}-{TAP_ARCH_X})/{V0X}'
    run = f'min({a},{straight})*{V0X}*2.3'
    fall = f'max({a}-{straight},0)'
    gated = smooth(straight, f'({straight}+.06)', a)   # 边值是 HLSL 串，不是数（str+float 教训）
    y_arc = f'{V0X}*.10*(Particles.Position.y-{TAP_CHANNEL_Z})/3.0'
    z_arc = f'({V0Z}+3.5*(Particles.Position.z-{TAP_CHANNEL_Z})/3.0)*{fall}-.5*{GRAVITY}*{fall}*{fall}'
    noise = f'float3(0,sin({fall}*23+{seed}*6.2831853)*.55,cos({fall}*27+{var}*6.2831853)*.45)*{fall}'
    position = (f'float3(Particles.Position.x+{run},Particles.Position.y+{y_arc}*{gated},'
                f'Particles.Position.z+{z_arc}*{gated})+{noise}')
    # Width modulation is continuous at both ends: 1.0 at birth, +/-6% while flying,
    # and the terminal 0.9x is folded into the life-envelope collapse below.
    width = f'(1+.06*sin({a}*(9+4*{seed})+{u2}*6.2831853))*{smooth("0", ".18", a)}'
    life = f'({FLOW_LIFE[0]}+{FLOW_LIFE[1] - FLOW_LIFE[0]}*{seed})'
    collapse = f'min(1,max(0,({life}-{a})/.14))'
    size = (f'float2({STREAM_R0},{STREAM_R0}*1.10)*(.72+.5*{u2})'
            f'*{width}*lerp(1,1.22,saturate({a}/.35))*(.55+.45*{collapse})')
    # Colour: white-hot at birth -> gold body -> orange rim. Hex 0 is born at ~2400 K and
    # the tail of the life cools through the same ramp (thin stream = fast radiative loss).
    first_half = f'({a}<1.2)'
    hot = f'lerp(float3(1.00,.90,.66),float3(.72,.26,.03),saturate({a}/1.2))'
    cool = f'lerp(float3(.72,.26,.03),float3(.30,.045,.008),{smooth("1.2","2.0",a)})'
    tint = f'lerp({cool},{hot},{first_half})'
    tint = f'{tint}*lerp(1,.82,{u2}*.5)'
    envelope = smooth('0', '.10', n) + '*(1-' + smooth('.35', '1.0', n) + ')'
    fade = 'saturate((8500-Engine.Owner.LODDistance)/2500)'
    color = f'float4({tint},(.86+.14*{u2})*{envelope}*{fade}*saturate(User.Flow))'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'atan2({V0Z}-{GRAVITY}*{fall},{V0X})'),   # VM HLSL 双参用 atan2（atan 只有单参）
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},{var},{u2},0)')}   # VEC4 必须四分量（与 spawn 侧同式）
    # Birth: position inside the drilled channel, ballistic velocity, and a state index
    # used by the update to pick the mouth radius in exactly one frame.
    spawn_pos, spawn_vel = mouth_origin(r_mouth, seed)
    assignments(system, FLOW, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, life),
        'Particles.Position': (POSITION, spawn_pos),
        'Particles.Velocity': (VEC3, spawn_vel),
        'Particles.SpriteSize': (VEC2, f'float2({STREAM_R0},{STREAM_R0}*1.10)'),
        'Particles.Color': (COLOR, f'float4(1.00,.90,.66,0)'),
        'Particles.MaterialRandom': (FLOAT, f'({seed})'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},{var},{u2},0)')})
    # Frame 1+ : stay in the channel -> the wide exit run; afterwards the parabola.
    born = f'(Particles.Age<=1.03*Engine.DeltaTime)'
    run_exit = f'float3({TAP_ARCH_X}+1.0+({TAP_EXIT_X}-{TAP_ARCH_X}-1.0)*.42,{r_exit}*sqrt({var})*(Particles.Position.y/3.0),{TAP_CHANNEL_Z}+{r_exit}*sqrt({var})*((Particles.Position.z-{TAP_CHANNEL_Z})/3.0))'
    update_pos = (f'lerp({common["Particles.Position"][1]},'
                  f'{run_exit},float({born}))')
    common['Particles.Position'] = (POSITION, update_pos)
    assignments(system, FLOW, 'ParticleUpdateScript', common)
    contact_nodes(system, FLOW)


def author_pool(system, phase):
    """L1 landing pool: one card a touch above the casting bed.

    Expand 0.30 s -> cool 2.50 s (bright gold -> red -> dark) -> contract. Radius and
    opacity are analytic in age, so the layer is pure per-particle state.
    """
    ensure_emitter(system, POOL)
    put(system, POOL, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,1)*saturate(User.Flow)*(1-saturate(User.DetailReduction))")', HL)
    renderer(system, POOL)
    seed, var, u2 = streams(phase, 0.211)
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    grow = f'{POOL_GROW}'
    total = f'{POOL_GROW + POOL_COOL}'
    rad = f'(2+16*sqrt(saturate({a}/{grow})))*(1-.55*saturate(({a}-{grow})/{POOL_COOL}))'
    # The card lies on the bed: the landing puddle is a flat ellipse, not a billboard ball.
    size = f'float2({rad}*2.1,{rad}*1.5)'
    glow = f'lerp(float3(1.00,.72,.26),float3(.62,.10,.012),saturate(({a}-{grow})/{POOL_COOL}))'
    dark = f'lerp({glow},float3(.075,.022,.010),{smooth("1.8","2.5",a)})'
    alpha = f'(.62*(1-.72*saturate(({a}-{grow})/{POOL_COOL})))*(1-{smooth("2.1","2.5",a)})'
    fade = 'saturate((8500-Engine.Owner.LODDistance)/2500)'
    color = f'float4({dark},{alpha}*{fade}*saturate(User.Flow))'
    common = {
        'Particles.Position': (POSITION, f'float3({BED_X},{var}*2.6-1.3,{POOL_Z})'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},{var},{u2},2)')}
    assignments(system, POOL, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, total), 'Particles.MaterialRandom': (FLOAT, '0'), **common})
    assignments(system, POOL, 'ParticleUpdateScript', common)
    contact_nodes(system, POOL)


def author_spark(system, phase):
    """L3 splash sparks: one instantaneous burst of <=12 particles, gated by User.SparkGate.

    Age is normalised by the spawn lifetime, so the whole burst is one deterministic
    event; ballistic arcs with an analytic settling clamp on the bed plane.
    """
    ensure_emitter(system, SPARK)
    spawn_burst(system, SPARK, SPARK_COUNT)
    renderer(system, SPARK, cull=4000.0)
    seed, var, u2 = streams(phase, 0.457)
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    ang = f'({seed}*2.39996323)'
    speed = f'(150+230*{var})'
    position = (f'float3({TAP_EXIT_X}+{speed}*.34*{a}*1.35,'
                f'sin({ang})*{speed}*.34*{a},'
                f'5+cos({ang})*{speed}*.30*{a}-.5*{GRAVITY}*.30*{a}*{a})')
    bed_clamp = f'max(0,{BED_Z}+2-Particles.Position.z)'
    position = f'{position}+float3(0,0,{bed_clamp})'
    size = f'float2(.62,.62)*(1-.35*{n})*(.6+.9*{u2})'
    # Sparks are born white-hot and end as dull red embers.
    tint = f'lerp(float3(1.00,.86,.58),float3(.85,.16,.02),saturate({n}*1.25))'
    envelope = f'saturate({n}*14)*(1-{smooth(".45","1.0",n)})'
    fade = 'saturate((4000-Engine.Owner.LODDistance)/1200)'
    color = f'float4({tint},{envelope}*{fade}*saturate(User.SparkGate))'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},{var},{u2},1)')}
    energy = f'({SPARK_LIFE[0]}+{SPARK_LIFE[1] - SPARK_LIFE[0]}*{u2})*saturate(User.SparkGate)'
    assignments(system, SPARK, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, energy), 'Particles.MaterialRandom': (FLOAT, f'({var})'), **common})
    assignments(system, SPARK, 'ParticleUpdateScript', common)
    contact_nodes(system, SPARK)


def author_glow(system, phase):
    """L2 ingot afterglow: a soft billboard over the mould position, 3 s linear decay.

    The card is NOT attached to the ingot component (three furnaces would share any
    single attachment); it lives in the same local space and opens/enables only while
    User.IngotGlow is 1. The afterglow always plays its full 3 s from activation, so
    SpawnRate is gated and the particle colour owns the fade.
    """
    ensure_emitter(system, GLOW)
    put(system, GLOW, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,1.2)*saturate(User.IngotGlow)*(1-saturate(User.DetailReduction))")', HL)
    renderer(system, GLOW)
    seed, var, u2 = streams(phase, 0.683)
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    size = f'float2(26,26)*(1+.10*sin({a}*(7+2*{u2})+{u2}*6.2831853))'
    tint = f'lerp(float3(1.00,.74,.30),float3(.70,.20,.02),saturate({a}/{GLOW_LIFE}))'
    alpha = f'(.42*(1-{a}/{GLOW_LIFE}))*(1-{smooth("2.4","3.0",a)})'
    fade = 'saturate((8500-Engine.Owner.LODDistance)/2500)'
    color = f'float4({tint},{alpha}*{fade}*saturate(User.IngotGlow))'
    common = {
        'Particles.Position': (POSITION, f'float3({INGOT_X},{var}*.8-.4,{BED_Z}+8)'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, color),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},{var},{u2},3)')}
    assignments(system, GLOW, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, f'{GLOW_SECONDS}'), 'Particles.MaterialRandom': (FLOAT, '0'), **common})
    assignments(system, GLOW, 'ParticleUpdateScript', common)
    contact_nodes(system, GLOW)


def material():
    """M_TapMetalFlow: unlit additive emissive, procedural hex cells + scrolling noise.

    No bitmap is authored or imported. The noise is a small hash-lattice value noise in
    a Custom node; the hex-cell break-up gives the stream its molten "beading" and its
    softer, translucent rim (the rim term also varies per particle through
    Particles.DynamicMaterialParameter.x, which is why the material is not translucency-
    masked: per-particle lighting inputs are unreachable in a masked/opaque graph).
    """
    path = DEST + '/' + MAT_NAME
    mat = u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        MAT_NAME, DEST, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('Cannot create ' + path)
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    # 2026-09-26 实机教训②：MaterialFactoryNew 的空白材质不带任何 usage flag——
    # 真机报「missing usage flag NiagaraSprites! Default Material will be used in game」
    # ＝粒子全变白马赛克。NullRHI commandlet 不检查 usage flag，只有真机会。
    mat.set_editor_property('used_with_niagara_sprites', True)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    uv = LIB.create_material_expression(mat, u.MaterialExpressionTextureCoordinate)
    time = LIB.create_material_expression(mat, u.MaterialExpressionTime)
    speed = LIB.create_material_expression(mat, u.MaterialExpressionScalarParameter)
    speed.set_editor_property('parameter_name', 'ScrollSpeed')
    speed.set_editor_property('default_value', .55)
    boost = LIB.create_material_expression(mat, u.MaterialExpressionScalarParameter)
    boost.set_editor_property('parameter_name', 'EmissiveBoost')
    boost.set_editor_property('default_value', 1.0)
    noise = LIB.create_material_expression(mat, u.MaterialExpressionCustom)
    noise.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    noise.set_editor_property('code', (
        'float2 p=UV*float2(3.0,5.0);\n'
        'float m=p.x-floor(p.x);\n'
        'p.x=floor(p.x)+floor(p.y)+floor(m+0.5);\n'
        'p.y=p.y+T*Speed;\n'
        'float2 i=floor(p);float2 f=frac(p);f=f*f*(3.0-2.0*f);\n'
        'float a=frac(sin(dot(i,float2(12.9898,78.233)))*43758.5453);\n'
        'float b=frac(sin(dot(i+float2(1.0,0.0),float2(12.9898,78.233)))*43758.5453);\n'
        'float c=frac(sin(dot(i+float2(0.0,1.0),float2(12.9898,78.233)))*43758.5453);\n'
        'float d=frac(sin(dot(i+float2(1.0,1.0),float2(12.9898,78.233)))*43758.5453);\n'
        'return lerp(lerp(a,b,f.x),lerp(c,d,f.x),f.y);'))
    pins = []
    for pin_name in ['UV', 'T', 'Speed']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', pin_name)
        pins.append(pin)
    noise.set_editor_property('inputs', pins)
    shape = LIB.create_material_expression(mat, u.MaterialExpressionCustom)
    shape.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    shape.set_editor_property('code', (
        'float n=N;\n'
        'float2 q=(UV-0.5)*2.0;\n'
        'float r=length(q);\n'
        'float band=exp(-4.5*r*r);\n'
        'float rim=exp(-2.2*abs(r-0.55));\n'
        'float hot=saturate((n-0.35)*2.6);\n'
        'float3 core=float3(1.00,0.86,0.58)+float3(0.0,0.0,0.0);\n'
        'float3 gold=float3(0.92,0.42,0.055);\n'
        'float3 orange=float3(0.80,0.19,0.022);\n'
        'float3 col=lerp(gold,orange,rim);\n'
        'col=lerp(col,core,saturate(hot*0.85));\n'
        'float a=0.30+0.70*band;\n'
        'a*=0.55+0.45*n;\n'
        'a*=0.72+0.55*rim;\n'
        'a*=0.48+0.52*Var;\n'
        'return col*a;'))
    pins = []
    for pin_name in ['UV', 'N', 'Var']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', pin_name)
        pins.append(pin)
    shape.set_editor_property('inputs', pins)
    # 2026-09-26 实机教训：ParticleSubUV 节点没有绑定 SubUV 纹理时，NullRHI commandlet 编译
    # 通过、但运行时平台（PCD3D_SM6）编译失败「Missing ParticleSubUV input texture」→
    # 游戏内 Default Material、粒子不可见。每粒子变化改走 DynamicParameter.x
    # （四个发射器都在写 Particles.DynamicMaterialParameter=float4(seed,var,u2,layer)）。
    var = LIB.create_material_expression(mat, u.MaterialExpressionDynamicParameter)
    varmask = LIB.create_material_expression(mat, u.MaterialExpressionComponentMask)
    varmask.set_editor_property('r', True)
    varmask.set_editor_property('g', False)
    varmask.set_editor_property('b', False)
    varmask.set_editor_property('a', False)
    gain = LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
    LIB.connect_material_expressions(shape, '', gain, 'A')
    LIB.connect_material_expressions(boost, '', gain, 'B')
    LIB.connect_material_expressions(uv, '', noise, 'UV')
    LIB.connect_material_expressions(time, '', noise, 'T')
    LIB.connect_material_expressions(speed, '', noise, 'Speed')
    LIB.connect_material_expressions(uv, '', shape, 'UV')
    LIB.connect_material_expressions(noise, '', shape, 'N')
    LIB.connect_material_expressions(var, '', varmask, '')
    LIB.connect_material_expressions(varmask, '', shape, 'Var')
    LIB.connect_material_property(gain, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(mat)
    save(mat)
    return mat


def verify_source(path):
    """Static self-check: the file must parse, and must not use the two banned constructs."""
    text = path.read_text(encoding='utf8')
    ast.parse(text)
    # 拼接构造禁项字面量：扫描器会扫到本行自身，直接写全会自我命中（2026-09-26 实跑教训）。
    for banned in ['Engine.Environment.' + 'DeltaTime', 'smooth' + 'step(']:
        hits = [i + 1 for i, line in enumerate(text.splitlines()) if banned in line]
        if hits:
            raise RuntimeError('Banned construct %s at lines %s' % (banned, hits))
    return len(text.splitlines())


def author():
    E.make_directory(DEST)
    material()
    system = system_asset()
    retire_tags(system)          # must precede any add/trim: stale tags would name deleted modules
    declare(system)
    phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
    author_flow(system, phase)
    author_pool(system, phase)
    author_spark(system, phase)
    author_glow(system, phase)
    E.set_metadata_tag(system, TAG, (
        'Molten tap stream + pool + sparks + ingot afterglow for the blast furnace ('
        'Docs/Fluids/furnace-tap-metal-20260925.md). L0 FurnaceTapMetalFlow: analytic parabola '
        'from the mesh-local tap arch (17.5,0,69.4) / channel (17.5,0,63.5) / shaft exit '
        '(24.7,0,63.5) to the casting bed (32.9,0,20), g0 %.0f cm/s2, flight %.2fs, life %s, '
        '%d/s while User.Flow=1, live cap %d; white-hot core -> gold -> orange rim (a<1.2s) then '
        'cooling. L1 FurnaceTapPool: one card on the bed, expand %.2fs -> cool %.2fs -> contract, '
        'alpha and colour analytic in age. L3 FurnaceTapSpark: instantaneous SpawnBurst <=%d gated '
        'by User.SparkGate (<35m and quality>=medium, written in C++). L2 FurnaceTapIngotGlow: '
        '%.0fs linear-decay card at the mould arc (45,0,20) gated by User.IngotGlow. Material '
        '%s is fully procedural (unlit additive, value-noise + hex cells); no new bitmap. '
        'C++ owns the pool, the ingot mesh and the 85m/35m gates.' % (
            GRAVITY, FLIGHT, FLOW_LIFE, FLOW_COUNT, LIVE_CAP, POOL_GROW, POOL_COOL,
            SPARK_COUNT, GLOW_LIFE, MAT)))
    save(system)
    return system


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = verify_source(Path(__file__))
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for target in [DEST + '/' + NAME, DEST + '/' + MAT_NAME]:
        if target in dirty:
            raise RuntimeError('Target package has unsaved changes; preserve them: ' + target)
    system = author()
    (OUT / 'assets.json').write_text(json.dumps({
        'saved': SAVED, 'material': MAT, 'material_is_procedural': True,
        'new_bitmaps': [],
        'anchor_cm': {'tap_arch_mouth': [TAP_ARCH_X, 0, TAP_ARCH_Z],
                      'tap_channel': [TAP_ARCH_X, 0, TAP_CHANNEL_Z],
                      'tap_exit': [round(TAP_EXIT_X, 1), 0, TAP_CHANNEL_Z],
                      'landing_bed': [BED_X, 0, BED_Z],
                      'ingot_mould': [INGOT_X, 0, BED_Z],
                      'space': 'SM_BlastFurnace mesh local (cm); component attached to Body with identity relative rotation'},
        'gravity_cm_s2': GRAVITY, 'flight_seconds': FLIGHT,
        'v0_cm_s': [round(V0X, 2), 0, round(V0Z, 2)],
        'budget': {'l0': {'rate': FLOW_COUNT, 'life': FLOW_LIFE, 'live_cap': LIVE_CAP},
                   'l1_pool_per_second': 1, 'l1_life': POOL_GROW + POOL_COOL,
                   'l3_sparks_per_burst': SPARK_COUNT, 'l2_glow_life': GLOW_LIFE},
        'parameters': {'User.Flow': 'C++ writes 1 on the completion rise edge, 0 when the job ends',
                       'User.SparkGate': 'C++ writes 1 only when the furnace is <3500cm from Eye and EffectsQuality>=1',
                       'User.IngotGlow': 'C++ writes 1 while the ingot is on show, 0 when hidden',
                       'User.DetailReduction': 'shared budget (ConfigureSmoke-style token bucket)'},
        'emitters': EMITTERS,
        'no_contact_planes_note': 'the stream/pool may use the shared User.SmokePlane0..4 approximations; the C++ side writes zeros, so the projection terms are inert',
        'author_lines': lines,
        'status': 'authored_compiled_saved; not game or visually tested'}, indent=2), encoding='utf8')
    u.log('FURNACE_TAP_COMPLETE ' + system.get_path_name())


if __name__ == '__main__':
    main()