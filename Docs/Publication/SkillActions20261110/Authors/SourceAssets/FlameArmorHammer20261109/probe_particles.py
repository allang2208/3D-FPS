"""User-requested hammer visibility diagnosis; isolated transient Niagara simulation."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent/'Review'
OUT.mkdir(exist_ok=True)
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
rows=json.loads((OUT.parent/'surface-data.json').read_text(encoding='utf-8'))
profile=next(r for r in rows if '/SM_Warhammer_hammer_heads_factory.' in r['mesh'])
system=u.load_asset('/Game/Skills/FlameArmor20261109/HammerSurfaceV13/NS_FlameArmorHammer')
fx=u.NiagaraFunctionLibrary.spawn_system_at_location(world,system,u.Vector(),auto_destroy=False,auto_activate=False,pre_cull_check=False)
if fx is None:
    raise RuntimeError('This probe requires rendering enabled; NullRHI skips Niagara instance creation.')
result={'system':system.get_path_name(),'mesh':profile['mesh'],'samples':[]}
try:
    fx.set_force_solo(True)
    for name,value in {'Fade':.92,'Detail':1.,'Coverage':.3,'WeaponSize':.62,'VariationSeed':216.25,'FlameClock':20.}.items():
        fx.set_variable_float('User.'+name,value)
    fx.set_variable_vec3('User.FlameUp',u.Vector(0,0,1))
    fx.set_variable_vec3('User.HammerFlow',u.Vector())
    for i,p in enumerate(profile['patches']):
        for key in ('a','b','c','normal'):
            value=p[key] if key=='normal' else [p[key][j]-profile['center'][j] for j in range(3)]
            fx.set_variable_vec3('User.Hammer'+('N' if key=='normal' else key.upper())+str(i),u.Vector(*value))
    fx.activate(True)
    for frame in range(1,121):
        fx.set_variable_float('User.FlameClock',20.+frame/60.)
        fx.advance_simulation(1,1./60.)
        if frame not in (15,30,60,120): continue
        cache=u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
        captured=u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,u.NiagaraSimCacheCreateParameters(),fx)
        row={'frame':frame,'capture':str(captured),'cache_frames':cache.get_num_frames(),'emitters':[]}
        if cache.get_num_frames():
            for emitter in cache.get_emitter_names():
                positions=cache.read_position_attribute('Position',emitter,False,0)
                colors=cache.read_color_attribute('Color',emitter,0)
                sizes=cache.read_vector2_attribute('SpriteSize',emitter,0)
                anchors=cache.read_position_attribute('HammerAnchor',emitter,False,0)
                idx=cache.read_float_attribute('SubImageIndex',emitter,0)
                row['emitters'].append(dict(name=str(emitter),count=len(positions),
                    colors=[str(c) for c in colors[:6]],sizes=[str(s) for s in sizes[:6]],
                    positions=[str(p) for p in positions[:6]],anchors=[str(p) for p in anchors[:6]],
                    atlas_frames=list(idx[:6]),alpha_mean=sum(c.a for c in colors)/max(1,len(colors))))
        result['samples'].append(row)
finally:
    fx.destroy_component(fx)
(OUT/'particles-before.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('HAMMER_PARTICLES_CAPTURED',str(OUT/'particles-before.json'))
