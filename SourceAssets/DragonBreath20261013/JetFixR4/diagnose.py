import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/DragonBreath20261013/JetFixR4';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_dragon_breath as a
system=u.load_asset(a.DEST+'/NS_DragonBreath')
out={'game_world':str(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'spawn':{},'live':[]}
for e in a.emitters(system):
    out['spawn'][e]={k:u.RainAssetEditor.read_input(system,e,'ParticleSpawnScript','InitializeParticle',k) for k in ['Sprite Size Mode','Uniform Sprite Size','Uniform Sprite Size Min','Uniform Sprite Size Max','Sprite Size','Sprite Size Min','Sprite Size Max','Sprite Rotation Mode','Sprite Rotation Angle Min','Sprite Rotation Angle Max']}
for fx in u.ObjectIterator(u.NiagaraComponent):
    if fx.get_asset()!=system or not fx.is_active():continue
    row={'name':fx.get_path_name(),'location':str(fx.get_world_location()),'rotation':str(fx.get_world_rotation()),'scale':str(fx.get_world_scale()),'params':{},'particles':{}}
    for n in ['Range','HalfAngle','Strength']+[f'Ray{i}' for i in range(9)]:row['params'][n]=fx.get_variable_float('User.'+n)
    for n in ['Forward','Side','Up']:row['params'][n]=str(fx.get_variable_vec3('User.'+n))
    cache=u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(fx),u.NiagaraSimCacheCreateParameters(),fx)
    if cache:
        for e in a.emitters(system):
            sizes=cache.read_vector2_attribute('SpriteSize',e);ages=cache.read_float_attribute('Age',e);pos=cache.read_position_attribute('Position',e)
            row['particles'][e]={'count':len(sizes),'min_age':min(ages,default=0),'max_size':max([max(v.x,v.y) for v in sizes],default=0),'youngest':[{'age':ages[i],'size':[sizes[i].x,sizes[i].y],'position':[pos[i].x,pos[i].y,pos[i].z]} for i in sorted(range(len(ages)),key=lambda i:ages[i])[:5]]}
    out['live'].append(row)
(OUT/'before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('DRAGON_JET_DIAGNOSE '+json.dumps(out))
