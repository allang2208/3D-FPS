"""Save the hammer's dedicated sky-strike assets; source library packages are read-only."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/ThunderGodHammer20261028/HeavyThunderV1'
DEST = '/Game/Weapons/ThunderGodHammer20261028/HeavyThunderV1'
SOURCE = '/Game/Weapons/ElectrifiedMelee/NS_ElectrifiedBlade'
API = u.get_default_object(u.NiagaraToolset_System)
EAL = u.EditorAssetLibrary
saved = []
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST + '/') for p in dirty):
    raise RuntimeError('Preserve unsaved hammer strike packages')
EAL.make_directory(DEST)

def own(source, name):
    path = DEST + '/' + name
    obj = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not obj:
        raise RuntimeError('Missing library asset: ' + source)
    EAL.set_metadata_tag(obj, 'ThunderHammer.Source', source)
    return obj

def ref(system, emitter):
    r = u.NiagaraExt_StackItemReference()
    r.set_editor_property('system', system)
    r.set_editor_property('emitter_name', emitter)
    return r

def put(system, emitter, module, name, value, typ='/Script/Niagara.NiagaraFloat'):
    if not u.RainAssetEditor.set_input(system, emitter, 'ParticleSpawnScript', module, name, typ, value):
        raise RuntimeError('Cannot author ' + emitter + '/' + name)

def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Save failed: ' + obj.get_path_name())
    saved.append(obj.get_path_name())

# Read actual installed assets and retain their emitter inventory in the authoring receipt.
library = {}
for path in (SOURCE, '/Game/Skills/Lightning/NS_LightningChain', '/Game/Skills/ElectricMagic/NS_ElectricImpact'):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Library source missing: ' + path)
    summary = API.call_method('GetSystemSummary', (obj,))
    library[path] = [str(e.get_editor_property('emitter_name')) for e in summary.get_editor_property('emitters')]

bolt = own(SOURCE, 'NS_ThunderHammerBolt')
for emitter, color, width in (
    ('Currency', '(R=0.08,G=0.34,B=1.0,A=1.0)', 'User._Width'),
    ('MainPower', '(R=0.72,G=0.90,B=1.0,A=1.0)', 'User._Width*0.32'),
):
    data = u.NiagaraExt_EmitterData()
    data.set_editor_property('property_values', json.dumps({'bLocalSpace': True, 'SimTarget': 'CPUSim'}))
    API.call_method('SetEmitterData', (ref(bolt, emitter), data))
    put(bolt, emitter, 'InitializeParticle', 'Lifetime', '(Value=0.72)')
    put(bolt, emitter, 'InitializeParticle', 'Color', color, '/Script/CoreUObject.LinearColor')
    for switch in ('AdjustHue', 'AdjustSaturation', 'AdjustValue', 'AdjustAlpha'):
        put(bolt, emitter, 'InitializeParticle', switch, '(Value=0)', '/Script/Niagara.NiagaraBool')
    put(bolt, emitter, 'InitializeParticle', 'Ribbon Width', '(HlslExpression="' + width + '")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
# Explicit object binding lets each branch have its own local spline within one pooled actor.
if not u.RainAssetEditor.bind_spline_user_object(bolt, 'User.BladeSpline'):
    raise RuntimeError('Hammer bolt compilation/binding failed')
EAL.set_metadata_tag(bolt, 'ThunderHammer.Shape', 'World-vertical jagged trunk; three tapered forks; two ground arcs; white-blue core; two return strokes')
save(bolt)

impact = own('/Game/Skills/ElectricMagic/NS_ElectricImpact', 'NS_ThunderHammerImpact')
# Retain the source's finite CPU spark burst; the ground slam already owns debris/dust.
if not u.RainAssetEditor.compile_rain(impact):
    raise RuntimeError('Hammer impact compilation failed')
save(impact)
sound = own('/Game/Skills/ElectricMagic/S_ThunderLanceDischarge', 'S_ThunderHammerStrike')
sound.set_editor_property('looping', False)
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
save(sound)

receipt = {'saved': saved, 'library_emitters': library, 'runtime_tested': False, 'rendered': False,
           'runtime': {'radius_cm': 300, 'magic_attack_scale': 1, 'stun_seconds': 1.5,
                       'height_cm': 2400, 'max_simultaneous_strikes': 4, 'visual_seconds': 0.65}}
(OUT / 'asset-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('THUNDER_HAMMER_ASSETS_SAVED ' + json.dumps(saved))
