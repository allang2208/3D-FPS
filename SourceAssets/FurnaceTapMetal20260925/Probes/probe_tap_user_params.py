# Probe v2 (in the real DEST package): does AddUserVariables actually register the
# parameters, and does a SpawnRate HlslExpression referencing User.DetailReduction
# compile on a fresh NS? Read-only for real assets; probe NS is deleted, never saved.
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API, ref, put, emitters
from build_fireball_flight import user_parameter

FLOAT = '/Script/Niagara.NiagaraFloat'
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
NE_CORE = '/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'
DEST = '/Game/Fluids/FurnaceTapMetal20260925'
E = u.EditorAssetLibrary

name = 'NS_ProbeTap2'
if E.does_asset_exist(DEST + '/' + name):
    E.delete_asset(DEST + '/' + name)
s = u.AssetToolsHelpers.get_asset_tools().create_asset(
    name, DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
u.log('PROBE2 created=%s' % bool(s))

for n in ['Flow', 'DetailReduction']:
    user_parameter(s, n, FLOAT)
after = str(API.call_method('GetUserVariables', (s,)).export_text())
u.log('PROBE2 vars_after=%s' % after.replace('\n', ' ')[:500])

API.call_method('AddEmitter', (s, u.load_asset(NE_CORE), 'ProbeEmitter'))
u.log('PROBE2 emitters=%s' % emitters(s))
topo = API.call_method('GetEmitterTopology', (ref(s, 'ProbeEmitter'),))
mods = topo.get_editor_property('emitter_update_script').get_editor_property('modules')
names = [str(m.get_editor_property('module_name')) for m in mods]
u.log('PROBE2 update_modules=%s' % names)
if 'SpawnBurst' in names:
    API.call_method('RemoveModule', (ref(s, 'ProbeEmitter', 'EmitterUpdateScript', 'SpawnBurst'),))
    mods = API.call_method('GetEmitterTopology', (ref(s, 'ProbeEmitter'),)).get_editor_property('emitter_update_script').get_editor_property('modules')
    names = [str(m.get_editor_property('module_name')) for m in mods]
if not any(n == 'SpawnRate' for n in names):
    API.call_method('AddModule', (ref(s, 'ProbeEmitter', 'EmitterUpdateScript'),
                                  u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    mods = API.call_method('GetEmitterTopology', (ref(s, 'ProbeEmitter'),)).get_editor_property('emitter_update_script').get_editor_property('modules')
    names = [str(m.get_editor_property('module_name')) for m in mods]
u.log('PROBE2 modules_after=%s' % names)

ok = u.RainAssetEditor.set_input(s, 'ProbeEmitter', 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
                                 HL, '(HlslExpression="max(0,16)*saturate(User.Flow)*(1-saturate(User.DetailReduction))")')
u.log('PROBE2 set_input=%s' % ok)
valid = u.RainAssetEditor.compile_rain(s)
u.log('PROBE2 RESULT valid=%d' % int(valid))
E.delete_asset(DEST + '/' + name)
u.log('PROBE2-DONE cleaned=%s' % (not E.does_asset_exist(DEST + '/' + name)))
