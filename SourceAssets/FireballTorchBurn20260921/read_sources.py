import unreal,json,sys
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir()).resolve()
if ROOT.as_posix().lower()!='d:/fps3d/fpsgame':raise RuntimeError('Wrong project')
OUT=ROOT/'SourceAssets/FireballTorchBurn20260921';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters
report={}
for path in ['/Game/Props/RomanColumn20260915/NS_TorchFlame','/Game/Skills/Fireball/NS_FireballSlowBurnCore','/Game/Skills/Fireball/NS_FireballVelocityTrail']:
    system=unreal.load_asset(path)
    r={'emitters':{}}
    for name in emitters(system):
        top=API.call_method('GetEmitterTopology',(ref(system,name),))
        modules={}
        for key in ['emitter_update_script','particle_spawn_script','particle_update_script']:
            stack=top.get_editor_property(key)
            modules[key]=[str(m.get_editor_property('module_name')) for m in stack.get_editor_property('modules')]
        data=API.call_method('GetRendererData',(ref(system,name,renderer=0),)).get_editor_property('property_values')
        r['emitters'][name]={'renderer':json.loads(data),'modules':modules}
        if name.startswith('NE_Flame'):
            r['emitters'][name]['inputs']={}
            for script,module,inputs in [('EmitterUpdateScript','EmitterState',['Life Cycle Mode']),('EmitterUpdateScript','SpawnRate',['SpawnRate']),('ParticleSpawnScript','InitializeParticle',['Lifetime Min','Lifetime Max','Sprite Size Min','Sprite Size Max'])]:
                for inp in inputs:
                    try:r['emitters'][name]['inputs'][module+'/'+inp]=str(unreal.RainAssetEditor.read_input(system,name,script,module,inp))
                    except Exception as e:r['emitters'][name]['inputs'][module+'/'+inp]=str(e)
    report[path]=r
for number in (1,2):
    path='/Game/Props/RomanColumn20260915/MI_TorchSoft_Flame%02d'%number
    mat=unreal.load_asset(path)
    parent=mat.get_editor_property('parent')
    r={'parent':parent.get_path_name(),'scalars':{},'textures':{},'vectors':{},'switches':{},'expressions':[]}
    for name in LIB.get_scalar_parameter_names(mat):r['scalars'][str(name)]=LIB.get_material_instance_scalar_parameter_value(mat,name)
    for name in LIB.get_texture_parameter_names(mat):
        value=LIB.get_material_instance_texture_parameter_value(mat,name)
        r['textures'][str(name)]=value.get_path_name() if value else None
    for name in LIB.get_vector_parameter_names(mat):r['vectors'][str(name)]=str(LIB.get_material_instance_vector_parameter_value(mat,name))
    for name in LIB.get_static_switch_parameter_names(mat):r['switches'][str(name)]=LIB.get_material_instance_static_switch_parameter_value(mat,name)
    for node in LIB.get_material_expressions(parent):
        n={'class':node.get_class().get_name()}
        for key in ('parameter_name','default_value','code','texture','function'):
            try:n[key]=str(node.get_editor_property(key))
            except Exception:pass
        r['expressions'].append(n)
    report[path]=r
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
report['editor_world']=world.get_path_name() if world else None
report['placed_torches']=[]
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_class().get_name()=='BronzeTorch':
        comp=actor.get_component_by_class(unreal.NiagaraComponent)
        report['placed_torches'].append({'name':actor.get_actor_label(),'position':str(actor.get_actor_location()),'flame':comp.get_asset().get_path_name() if comp and comp.get_asset() else None})
(OUT/'source-settings.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FIREBALL_SOURCE_READ',str(OUT/'source-settings.json'))
print('WORLD',report['editor_world'],'TORCHES',len(report['placed_torches']))
for p,r in report.items():
    if isinstance(r,dict) and 'parent'in r:print(p,r['parent'],r['scalars'],r['textures'],r['switches'])
