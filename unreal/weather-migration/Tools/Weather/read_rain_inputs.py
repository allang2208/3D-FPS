import unreal,json
from pathlib import Path
api=unreal.get_default_object(unreal.NiagaraToolset_System)
report={}
for name in ['NS_FPS_RainFine','NS_FPS_SurfaceSplashes','NS_FPS_RainMist','NS_FPS_RoofDrips']:
    s=unreal.load_asset('/Game/Weather/VFX/'+name)
    e='RainSplashes' if name=='NS_FPS_SurfaceSplashes' else 'RainDrops'
    row={}
    for p in ['Life Cycle Mode','Loop Behavior','Loop Duration']:
        row['EmitterState.'+p]=unreal.RainAssetEditor.read_input(s,e,'EmitterUpdateScript','EmitterState',p)
    for script,module,p in [('EmitterUpdateScript','SpawnRate','SpawnRate'),('ParticleSpawnScript','InitializeParticle','Sprite Size Mode'),('ParticleSpawnScript','InitializeParticle','Lifetime Mode')]:
        row[module+'.'+p]=unreal.RainAssetEditor.read_input(s,e,script,module,p)
    for script,module,inputs in [('ParticleSpawnScript','InitializeParticle',['Color','Lifetime Min','Lifetime Max','Uniform Sprite Size Min','Uniform Sprite Size Max'] if e=='RainSplashes' else ['Color','Lifetime Min','Lifetime Max','Sprite Size']),('ParticleSpawnScript','ShapeLocation',['Box Size']),('ParticleUpdateScript','GravityForce',['Gravity'])]:
        for p in inputs:row[module+'.'+p]=unreal.RainAssetEditor.read_input(s,e,script,module,p)
    r=unreal.NiagaraExt_StackItemReference();r.set_editor_property('system',s);r.set_editor_property('emitter_name',e)
    (Path(unreal.Paths.project_saved_dir())/'RainUpgrade'/(name+'-topology.txt')).write_text(api.call_method('GetEmitterTopology',(r,)).export_text())
    report[name]=row
(Path(unreal.Paths.project_saved_dir())/'RainUpgrade/inputs-readback.json').write_text(json.dumps(report,indent=2))
unreal.log('RAIN_INPUT_READ_PASS')
