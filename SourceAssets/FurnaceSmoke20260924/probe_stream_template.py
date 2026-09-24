"""Read-only ground-truth dump for furnace smoke authoring (no writes, no saves)."""
import json
import unreal as u

API = u.get_default_object(u.NiagaraToolset_System)
OUT = u.Paths.project_dir() + '/Saved/furnace_probe.json'
R = {}


def ref(system, emitter, script='', module='', renderer=-1):
    r = u.NiagaraExt_StackItemReference()
    for k, v in dict(system=system, emitter_name=emitter, script_name=script,
                     module_name=module, renderer_index=renderer).items():
        r.set_editor_property(k, v)
    return r


def read(s, e, script, module, name):
    try:
        return str(u.RainAssetEditor.read_input(s, e, script, module, name))
    except Exception as exc:  # noqa: BLE001
        return 'ERR:' + str(exc)[:90]


sys_path = '/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV15'
s = u.load_asset(sys_path)
R['loaded'] = bool(s)
if s:
    R['emitters'] = [str(e.get_editor_property('emitter_name'))
                     for e in API.call_method('GetSystemSummary', (s,)).get_editor_property('emitters')]
    R['topology'] = str(API.call_method('GetEmitterTopology', (ref(s, 'Muzzle_Smoke'),)))[:6000]
    R['emitter_data'] = str(API.call_method('GetEmitterData', (ref(s, 'Muzzle_Smoke'),)))[:900]
    R['renderer_data'] = str(API.call_method('GetRendererData', (ref(s, 'Muzzle_Smoke', renderer=0),)))[:1200]
    R['user_vars'] = str(API.call_method('GetUserVariables', (s,)).export_text())[:2500]
    for script, module, inputs in [
        ('EmitterUpdateScript', 'EmitterState', ['Life Cycle Mode', 'Loop Behavior', 'Loop Duration']),
        ('ParticleSpawnScript', 'InitializeParticle', ['Lifetime Min', 'Lifetime Max', 'Spawn Color', 'Render Sprite Size', 'Velocity']),
        ('ParticleSpawnScript', 'AddVelocity', ['Velocity', 'Cone Angle', 'Direction']),
        ('ParticleSpawnScript', 'SetVariables_285AF4AB4D469F20CC2C7FB5409ABDBA', ['Particles.Velocity']),
    ]:
        for name in inputs:
            R[f'{script}.{module}.{name}'] = read(s, 'Muzzle_Smoke', script, module, name)

v9 = u.load_asset('/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV9')
rate_tag = u.EditorAssetLibrary.get_metadata_tag(v9, 'GunplayV9.Rate') if v9 else ''
rise_tag = u.EditorAssetLibrary.get_metadata_tag(v9, 'GunplayV9.Rise') if v9 else ''
spread_tag = u.EditorAssetLibrary.get_metadata_tag(v9, 'GunplayV9.Spread') if v9 else ''
R['v9_tags'] = {'rate': str(rate_tag), 'rise': str(rise_tag), 'spread': str(spread_tag)}
if s and rate_tag:
    for name in ['Constant Rate', 'Rate', 'Spawn Rate']:
        R[f'rate.{name}'] = read(s, 'Muzzle_Smoke', 'EmitterUpdateScript', str(rate_tag), name)

rate_asset = u.load_asset('/Niagara/Modules/Spawn/Rate')
R['rate_asset'] = rate_asset.get_path_name() if rate_asset else 'MISSING'
R['rain_input_helpers'] = [m for m in dir(u.RainAssetEditor) if 'input' in m.lower()][:20]
R['api_module_helpers'] = [m for m in dir(API) if 'module' in m.lower() or 'Module' in m][:25]

with open(OUT, 'w', encoding='utf8') as fh:
    json.dump(R, fh, indent=1, ensure_ascii=False)
u.log('FURNACE_PROBE_DONE')
