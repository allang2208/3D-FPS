"""Read-only structural verification of NS_FurnaceBlackSmoke (no writes)."""
import json
import unreal as u

API = u.get_default_object(u.NiagaraToolset_System)
s = u.load_asset('/Game/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke')
R = {'loaded': bool(s)}
if s:
    def ref(e, script='', module='', renderer=-1):
        r = u.NiagaraExt_StackItemReference()
        for k, v in dict(system=s, emitter_name=e, script_name=script, module_name=module, renderer_index=renderer).items():
            r.set_editor_property(k, v)
        return r
    ems = [str(x.get_editor_property('emitter_name')) for x in API.call_method('GetSystemSummary', (s,)).get_editor_property('emitters')]
    R['emitters'] = ems
    R['emitter_data'] = str(API.call_method('GetEmitterData', (ref(ems[0]),)).export_text())[:500]
    R['renderer'] = str(API.call_method('GetRendererData', (ref(ems[0], renderer=0),)).export_text())[:700]
    R['user_vars'] = [ln for ln in str(API.call_method('GetUserVariables', (s,)).export_text()).replace('),(', ')\n(').splitlines() if 'Name="User.' in ln][:30]
    topo = API.call_method('GetEmitterTopology', (ref(ems[0]),))
    for field in ['emitter_update_script', 'particle_spawn_script', 'particle_update_script']:
        stack = topo.get_editor_property(field)
        R[str(stack.get_editor_property('script_name'))] = [str(m.get_editor_property('module_name')) for m in stack.get_editor_property('modules')]
    for script, module, name, want in [
        ('EmitterUpdateScript', 'SpawnRate', 'SpawnRate', 'expr'),
        ('EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', 'enum'),
    ]:
        try:
            R[f'{module}.{name}'] = str(u.RainAssetEditor.read_input(s, ems[0], script, module, name))[:220]
        except Exception as exc:  # noqa: BLE001
            R[f'{module}.{name}'] = 'ERR ' + str(exc)[:80]
with open(u.Paths.project_dir() + '/Saved/furnace_ns_verify.json', 'w', encoding='utf8') as fh:
    json.dump(R, fh, indent=1, ensure_ascii=False)
u.log('FURNACE_VERIFY_DONE')
