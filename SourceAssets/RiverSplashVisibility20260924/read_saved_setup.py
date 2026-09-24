"""Read only: diagnose the reported invisible splash, without starting a game."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if root!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
out=root/'SourceAssets/RiverSplashVisibility20260924'
api=u.get_default_object(u.NiagaraToolset_System)
system=u.load_asset('/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash')
report={'system':system.get_path_name(),'emitters':[]}
def ref(e,script='',module='',renderer=-1):
    r=u.NiagaraExt_StackItemReference()
    for k,v in dict(system=system,emitter_name=e,script_name=script,module_name=module,renderer_index=renderer).items():r.set_editor_property(k,v)
    return r
for emitter in api.call_method('GetSystemSummary',(system,)).get_editor_property('emitters'):
    name=str(emitter.get_editor_property('emitter_name'))
    topology=api.call_method('GetEmitterTopology',(ref(name),))
    renderer=json.loads(api.call_method('GetRendererData',(ref(name,renderer=0),)).get_editor_property('property_values'))
    record={'name':name,'renderer':renderer,'inputs':{}}
    for script,prop,variables in [
        ('ParticleSpawnScript','particle_spawn_script',['Particles.Lifetime','Particles.SplashVelocity','Particles.Color']),
        ('ParticleUpdateScript','particle_update_script',['Particles.SpriteSize','Particles.Color'])]:
        for module in topology.get_editor_property(prop).get_editor_property('modules'):
            mod=str(module.get_editor_property('module_name'))
            if mod.startswith('SetVariables'):
                record['inputs'][script]={v:u.RainAssetEditor.read_input(system,name,script,mod,v) for v in variables}
    report['emitters'].append(record)
if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
    report['pie_already_running']=False
else:
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    report['pie_already_running']=bool(editor and editor.is_in_play_in_editor())
out.mkdir(parents=True,exist_ok=True)
(out/'saved-setup-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('RIVER_SPLASH_READ '+json.dumps({'emitters':[e['name'] for e in report['emitters']],
    'pie_already_running':report['pie_already_running']},ensure_ascii=False))
