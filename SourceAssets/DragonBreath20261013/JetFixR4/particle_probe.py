"""Targeted first-frame size and bilateral-jet probe; no gameplay or rendering."""
import json,math,sys
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/JetFixR4')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_game_world() or editor.get_editor_world()
if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() or not world:
    # A Python commandlet may start without a world. This is a transient blank
    # world inside that process; never load/save a project map or start PIE.
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
if not world:raise RuntimeError('No world available for the particle probe')
print('DRAGON_PROBE_WORLD '+world.get_path_name())
system=u.load_asset('/Game/Skills/DragonBreath20261013/NS_DragonBreath')
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
import build_dragon_breath as author
assert u.RainAssetEditor.compile_rain(system)
report=[]
for radius,yaw in [(500.,0.),(1500.,90.),(1500.,233.)]:
    origin=u.Vector(0,0,-100000);rot=u.Rotator(0,yaw,0)
    angle=math.radians(yaw);forward=u.Vector(math.cos(angle),math.sin(angle),0);side=u.Vector(-math.sin(angle),math.cos(angle),0)
    fx=u.NiagaraFunctionLibrary.spawn_system_at_location(world,system,origin,rotation=rot,auto_destroy=False,auto_activate=False,pre_cull_check=False)
    fx.set_force_solo(True)
    try:
        for n,v in [('Range',radius),('HalfAngle',math.pi/4),('Strength',1.)]+[(f'Ray{i}',radius) for i in range(9)]:fx.set_variable_float('User.'+n,v)
        fx.set_variable_position('User.Origin',origin)
        for n,v in [('Forward',forward),('Side',side),('Up',u.Vector(0,0,1))]:fx.set_variable_vec3('User.'+n,v)
        fx.activate(True)
        for steps in [2,22,12]:
            fx.advance_simulation(steps,1/60)
            cache=u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world),u.NiagaraSimCacheCreateParameters(),fx)
            if not cache:raise RuntimeError('No particle data')
            e='Flame-Smoke';pos=cache.read_position_attribute('Position',e);sizes=cache.read_vector2_attribute('SpriteSize',e);ages=cache.read_float_attribute('Age',e);rots=cache.read_float_attribute('SpriteRotation',e)
            local=[((p.x-origin.x)*forward.x+(p.y-origin.y)*forward.y,(p.x-origin.x)*side.x+(p.y-origin.y)*side.y,p.z-origin.z) for p in pos]
            live=[v for v in local if v[0]>15]
            angles=[math.degrees(math.atan2(v[1],v[0])) for v in live]
            report.append({'range':radius,'yaw':yaw,'steps':steps,'count':len(pos),'max_size':max([max(v.x,v.y) for v in sizes],default=0),
                'left':sum(v[1]<-5 for v in live),'right':sum(v[1]>5 for v in live),'min_angle':min(angles,default=0),'max_angle':max(angles,default=0),
                'youngest':[{'age':ages[i],'size':[sizes[i].x,sizes[i].y],'rotation':rots[i] if rots else None,'local':local[i]} for i in sorted(range(len(ages)),key=lambda i:ages[i])[:4]]})
    finally:fx.destroy_component(fx.get_owner())
name=globals().get('probe_output','particles-before.json')
(OUT/name).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DRAGON_JET_PARTICLES '+json.dumps(report))
