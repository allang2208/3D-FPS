"""Author NS_FurnaceBlackSmoke: continuous chimney soot plume for the working blast furnace.

Design contract (Docs/Fluids/furnace-black-smoke-20260924.md):
- Reuses the approved Mantaflow rolling smoke surface M_RollingImpactSmoke (T_MuzzleSmokeMantaflowV14,
  per-particle Seed rolling/mirroring; no new bake).
- Single CPU emitter, local space, identity-rotated component: local axes == world axes (+Z up).
- Position is a pure function of age (proven impact pattern): buoyant rise, per-particle lateral
  meander (random spread) and integrated User.Wind drift (wind-following).
- Consumes the shared smoke contract: User.SpawnRate / DetailReduction / Wind / SmokePlane0..4 /
  WetImpact; contact approximation from fluid_contact_nodes.
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
TAG = 'FurnaceSmoke20260924'
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
    for name, typ in [('SpawnRate', FLOAT), ('Wind', VEC3), ('DetailReduction', FLOAT),
                      ('WetImpact', FLOAT), ('Rainfall', FLOAT)]:
        if 'User.' + name not in existing:
            user_parameter(system, name, typ)


def lifecycle(system):
    src = u.load_asset(LIFECYCLE_SRC)
    mode = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    # ENiagaraEmitterLifeCycleMode: NewEnumerator1 == Self; ENiagara_EmitterStateOptions: NewEnumerator0 == Infinite.
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(system, EMITTER, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, EMITTER, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)


def author():
    E.make_directory(DEST)
    system = system_asset()
    if EMITTER not in emitters(system):
        API.call_method('AddEmitter', (system, u.load_asset(NE_CORE), EMITTER))
        if EMITTER not in emitters(system):
            raise RuntimeError('Cannot add emitter ' + EMITTER)
    trim(system, EMITTER, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState']})
    # trim deletes the generated SetVariables_<guid> modules — both the assignments() module and the
    # five contact_nodes() projection modules per script — but their metadata tags would still name
    # removed instances, and a stale tag makes the next pass reference a module that no longer exists
    # (re-run failure "在堆栈引用中未找到模块"). Retire those tags unconditionally: both helpers then
    # recreate fresh modules in the correct order (assignments first, contact projections last), so
    # idempotent re-runs converge deterministically.
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        E.remove_metadata_tag(system, 'Fireball.Assignments.' + EMITTER + '.' + script)
        for i in range(5):
            E.remove_metadata_tag(system, f'FluidContact.{EMITTER}.{script}.{i}')
    # Continuous spawn via the project-proven SpawnRate module (handles dt + fractional
    # accumulation internally; its rate input binds User.* variables). NE_Core lacks it, so add.
    stale = E.get_metadata_tag(system, 'Fireball.Assignments.' + EMITTER + '.EmitterSpawnScript')
    if stale:
        # Previous draft authored spawning as a custom SpawnGroupCount expression that referenced
        # Engine.Environment.DeltaTime; that binding is unavailable in SetParameters. Retire it.
        API.call_method('RemoveModule', (ref(system, EMITTER, 'EmitterSpawnScript', str(stale)),))
        E.remove_metadata_tag(system, 'Fireball.Assignments.' + EMITTER + '.EmitterSpawnScript')
    topo = API.call_method('GetEmitterTopology', (ref(system, EMITTER),))
    stack = topo.get_editor_property('emitter_update_script')
    if not any(str(m.get_editor_property('module_name')) == 'SpawnRate' for m in stack.get_editor_property('modules')):
        API.call_method('AddModule', (ref(system, EMITTER, 'EmitterUpdateScript'),
                                      u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(system, EMITTER, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,User.SpawnRate)*(1-saturate(User.DetailReduction))*(1-.25*User.Rainfall)")', HL)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, EMITTER), {
        'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    lifecycle(system)
    declare(system)
    mat = u.load_asset(MAT)
    if not mat:
        raise RuntimeError('Missing approved rolling smoke material ' + MAT)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, EMITTER, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 8500})

    # Decorative variation: three per-particle streams from UniqueID plus a system-wide phase
    # (re-seeded on pool reuse) so neighbouring plumes never march in lockstep.
    phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
    seed = f'frac(float(Particles.UniqueID)*.61803398875+{phase})'
    var = f'frac(float(Particles.UniqueID)*.41421356237+{phase}*.731)'
    u2 = f'frac(float(Particles.UniqueID)*.75487766623+{phase}*.411)'
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
    tint = (f'lerp(float3(.050,.048,.050),float3(.088,.084,.080),'
            f'{smooth(".1", "1", n)})*(.82+.36*{var})')
    color = f'float4({tint},(({.26}+{.12}*{seed}))*{envelope}*{fade}*(1-.28*{rain}))'
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
        'status': 'authored_compiled_saved; not game or visually tested'}, indent=2), encoding='utf8')
    u.log('FURNACE_SMOKE_COMPLETE ' + system.get_path_name())


if __name__ == '__main__':
    main()
