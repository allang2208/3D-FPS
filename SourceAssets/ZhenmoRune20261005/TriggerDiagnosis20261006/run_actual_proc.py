from pathlib import Path
import builtins,json,base64
import unreal as u
OUT=Path(__file__).resolve().parent
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if 'ZhenmoVisualAudit' not in u.SystemLibrary.get_command_line():raise RuntimeError('Isolated audit profile required')
if not w:raise RuntimeError('PIE required')
u.SystemLibrary.execute_console_command(w,'fps.Zhenmo.VisualAudit')
u.SystemLibrary.execute_console_command(w,'t.MaxFPS 45')
print('ACTUAL_PROC_SCHEDULED')
state={'elapsed':0.,'next':0.,'samples':[]}
def capture_tick(dt):
    state['elapsed']+=dt
    if state['elapsed']<state['next']:return
    state['next']=state['elapsed']+.2
    a=u.GameplayStatics.get_player_character(w,0)
    if a:
        fx=next((c for c in a.get_components_by_class(u.NiagaraComponent) if c.get_name()=='ZhenmoRisingGold'),None)
        ground=next((c for c in a.get_components_by_class(u.DynamicMeshComponent) if c.get_name()=='ZhenmoSoftGround'),None)
        if fx:
            state['samples'].append({'t':u.GameplayStatics.get_time_seconds(w),'active':fx.is_active(),'opacity':ground.get_material(0).get_scalar_parameter_value('FieldOpacity') if ground else None})
            if not state.get('dumped'):
                u.SystemLibrary.execute_console_command(w,'fx.Niagara.DumpComponents full filter=Zhenmo')
                state['dumped']=True
    if state['elapsed']>40:
        (OUT/'proc-samples.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        u.unregister_slate_post_tick_callback(builtins.zhenmo_proc_callback)
builtins.zhenmo_proc_callback=u.register_slate_post_tick_callback(capture_tick)
