"""Focused hidden Niagara simulation for the reported invisible armor, no game/PIE start."""
import unreal as u
import json
from pathlib import Path

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FlameArmor20261016/VisibilityFix')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world is None and globals().get('FLAME_HEADLESS',False):
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
if world is None:raise RuntimeError('No diagnostic world; preserve editor session.')
report={}
for leaf in ('Body','Weapon','Arrow'):
    s=u.load_asset('/Game/Skills/FlameArmor20261016/TorchV2/NS_FlameArmor'+leaf+'V2')
    u.RainAssetEditor.compile_rain(s,True)
    fx=u.NiagaraFunctionLibrary.spawn_system_at_location(world,s,u.Vector(0,0,-100000),auto_destroy=False,auto_activate=False,pre_cull_check=False)
    row={};report[leaf]=row
    try:
        fx.set_visibility(False)
        fx.set_force_solo(True)
        for name,value in {'Fade':1.,'Detail':1.,'Coverage':1.,'UpperVisibility':1.,'WeaponSize':.7,'MotionEnergy':1.,'Radius':40.,'BodyHeight':180.}.items():
            fx.set_variable_float('User.'+name,value)
        for name,value in {'WeaponEnd':u.Vector(100,0,0),'FlameProfile':u.Vector(1,1,1),'Velocity':u.Vector(3000,0,0)}.items():
            fx.set_variable_vec3('User.'+name,value)
        for name in ('BodyOrigin','WeaponStartWorld','WeaponEndWorld','PreviousStart','PreviousEnd','PreviousPosition','CurrentPosition'):
            fx.set_variable_position('User.'+name,u.Vector(0,0,-100000))
        row['detail']=str(fx.get_variable_float('User.Detail'))
        fx.activate(True)
        fx.advance_simulation(30,1./60.)
        row['active']=fx.is_active()
        cache=u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
        result=u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,u.NiagaraSimCacheCreateParameters(),fx)
        row['capture']=str(result);row['frames']=cache.get_num_frames();row['emitters']=[]
        if row['frames']:
            for emitter in cache.get_emitter_names():
                colors=cache.read_color_attribute('Color',emitter,0)
                sizes=cache.read_vector2_attribute('SpriteSize',emitter,0)
                pos=cache.read_position_attribute('Position',emitter,False,0)
                ages=cache.read_float_attribute('Age',emitter,0)
                row['emitters'].append({'name':str(emitter),'count':len(pos),'colors':[str(v) for v in colors[:4]],
                    'sizes':[str(v) for v in sizes[:4]],'positions':[str(v) for v in pos[:3]],'ages':list(ages[:4])})
    except Exception as exc:row['error']=str(exc)
    finally:
        if fx:fx.destroy_component(fx)
    print('FLAME_PARTICLE_STAGE',leaf,json.dumps(row))
(OUT/'particle-probe-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FLAME_PARTICLES',json.dumps(report))
