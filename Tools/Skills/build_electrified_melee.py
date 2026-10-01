"""Author the melee-only, local-space copy of the owned lightning ribbons.

Background production only: save assets; no PIE, preview or test run.
The active lightning asset and its accepted palette/width are unchanged.
"""
import json
from pathlib import Path
import unreal

SOURCE = '/Game/Skills/Lightning/NS_LightningChain'
DEST = '/Game/Weapons/ElectrifiedMelee/NS_ElectrifiedBlade'
api = unreal.get_default_object(unreal.NiagaraToolset_System)
dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if DEST in dirty:
    raise RuntimeError('Preserve unsaved edits in ' + DEST)
unreal.EditorAssetLibrary.make_directory('/Game/Weapons/ElectrifiedMelee')
system = unreal.load_asset(DEST) if unreal.EditorAssetLibrary.does_asset_exist(DEST) else unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
if not system:
    raise RuntimeError('Missing owned lightning system: ' + SOURCE)

def ref(emitter):
    r = unreal.NiagaraExt_StackItemReference()
    r.set_editor_property('system', system)
    r.set_editor_property('emitter_name', emitter)
    return r

emitters = {str(e.get_editor_property('emitter_name')) for e in api.call_method('GetSystemSummary', (system,)).get_editor_property('emitters')}
if 'Detail' in emitters:
    api.call_method('RemoveEmitter', (ref('Detail'),))
for emitter in ('Currency', 'MainPower'):
    data = unreal.NiagaraExt_EmitterData()
    data.set_editor_property('property_values', json.dumps({'bLocalSpace': True, 'SimTarget': 'CPUSim'}))
    api.call_method('SetEmitterData', (ref(emitter), data))
    if not unreal.RainAssetEditor.set_input(system, emitter, 'ParticleSpawnScript', 'InitializeParticle',
                                          'Lifetime', '/Script/Niagara.NiagaraFloat', '(Value=0.24)'):
        raise RuntimeError('Cannot set blade ribbon lifetime: ' + emitter)

unreal.EditorAssetLibrary.set_metadata_tag(system, 'Electrified.Source', SOURCE)
unreal.EditorAssetLibrary.set_metadata_tag(system, 'Electrified.Presentation',
    'V3 jagged local-space strikes; explicit User.BladeSpline; 0.065s hold + 0.115s fade; open forked orbital fragments; no Detail emitter')
# Compile first, then bind ALL refreshed spline defaults. Editing precompile
# cached interfaces loses the setting when Niagara replaces those objects.
# The native helper also declares the UObject in the instance parameter layout.
if not unreal.RainAssetEditor.bind_spline_user_object(system, 'User.BladeSpline'):
    raise RuntimeError('Blade Niagara compilation/source binding failed')
if not unreal.EditorAssetLibrary.save_loaded_asset(system, False):
    raise RuntimeError('Blade Niagara save failed')
out = Path(unreal.Paths.project_dir()) / 'Saved/ElectrifiedMelee/assets-authored.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'saved': [system.get_path_name()], 'source': SOURCE,
                          'spline_source': 'User.BladeSpline', 'runtime_tested': False}, indent=2), encoding='utf-8')
unreal.log('ELECTRIFIED_AUTHORED ' + system.get_path_name())
