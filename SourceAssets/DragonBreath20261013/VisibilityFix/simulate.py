import json,math
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/VisibilityFix')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world() or editor.get_editor_world()
if not world:raise RuntimeError('No existing world; do not start PIE automatically')
system=u.load_object(None,globals().get('probe_asset','/Game/Skills/DragonBreath20261013/NS_DragonBreath.NS_DragonBreath'))
for old in u.ObjectIterator(u.NiagaraComponent):
    if old.get_asset()==system and old.get_world_location().z == -100000:
        old.destroy_component(old.get_owner())
origin=u.Vector(0,0,-100000)
fx=u.NiagaraFunctionLibrary.spawn_system_at_location(world,system,origin,auto_destroy=False,auto_activate=False,pre_cull_check=False)
if not fx:raise RuntimeError('Niagara component was not created')
report={'system':system.get_path_name(),'origin':str(origin),'samples':[]}
try:
    for name,value in [('Range',500.),('HalfAngle',math.pi/4),('Strength',1.)]+[(f'Ray{i}',500.) for i in range(9)]:
        fx.set_variable_float('User.'+name,value)
    fx.set_variable_position('User.Origin',origin)
    for name,value in [('Forward',u.Vector(1,0,0)),('Side',u.Vector(0,1,0)),('Up',u.Vector(0,0,1))]:
        fx.set_variable_vec3('User.'+name,value)
    fx.activate(True)
    for steps in [6,15,21]:
        fx.advance_simulation(steps,1/60)
        cache=u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world),u.NiagaraSimCacheCreateParameters(),fx)
        row={'steps':steps,'active':fx.is_active(),'cache':bool(cache),'emitters':{}}
        if cache:
            for name in ['Flame-Smoke','Embers','EmbersBig']:
                pos=cache.read_position_attribute('Position',name)
                color=cache.read_color_attribute('Color',name)
                sizes=cache.read_vector2_attribute('SpriteSize',name)
                initial=cache.read_color_attribute('Initial.Color',name)
                row['emitters'][name]={'count':len(pos),'colors':[[v.r,v.g,v.b,v.a] for v in color[:4]],'initial_colors':[[v.r,v.g,v.b,v.a] for v in initial[:2]],
                    'positions':[[v.x,v.y,v.z] for v in pos[:4]],'sizes':[[v.x,v.y] for v in sizes[:4]]}
        report['samples'].append(row)
finally:
    fx.destroy_component(fx.get_owner())
(OUT/globals().get('probe_output','simulation-before.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DRAGON_SIMULATION '+json.dumps({'system':report['system'],'samples':[{k:v for k,v in row.items() if k!='emitters'}|{'emitters':{n:{k:v for k,v in d.items() if k not in ['positions','sizes']} for n,d in row['emitters'].items()}} for row in report['samples']]}))
