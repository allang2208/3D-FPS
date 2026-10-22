"""Filled, irregular ground fuel for the Dragon-derived meteor gas volume."""
import unreal as u
from build_fireball_assets import API,ref,setdata,assignments,put
from build_fireball_flames import trim,FLOAT,VEC3,POSITION,COLOR
from build_fireball_flight import expression


def build_sources(system):
    en='ParticleSourceEmitter'
    trim(system,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],
                   'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for stage in ['ParticleSpawnScript','ParticleUpdateScript']:
        u.EditorAssetLibrary.remove_metadata_tag(system,'Fireball.Assignments.'+en+'.'+stage)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,en),
            {'bLocalSpace':False,'SimTarget':'GPUComputeSim','InterpolatedSpawnMode':'NoInterpolation'})
    top=API.call_method('GetEmitterTopology',(ref(system,en),))
    for renderer in reversed(top.get_editor_property('renderers')):
        API.call_method('RemoveRenderer',(ref(system,en,renderer=renderer.get_editor_property('renderer_index')),))
    expression(system,en,'EmitterUpdateScript','SpawnRate','SpawnRate',
               '(300+100*min(User.Radius/558.0,1.6))*saturate(User.Fade)')
    # Radius must not use the golden-angle phase: that collapses the disk
    # into a spiral band. Independent phases fill the area over time.
    seed='frac((float(Particles.UniqueID)+.5)*.7548776662)'
    variant='frac((float(Particles.UniqueID)+.5)*.41421356237)'
    angle='(float(Particles.UniqueID)*2.39996323)'
    core='(fmod(float(Particles.UniqueID),5.0)<1.0)'
    patch='max(User.CellSize*3.2,26.0)'
    edge=f'(.92+.04*sin({angle}*3)+.02*sin({angle}*7+1.1))'
    extent=f'max(0.0,User.Radius*{edge}-{patch})'
    fraction=f'({core}?.32*sqrt({seed}):pow({seed},.58))'
    radius=f'({extent})*({fraction})*saturate(User.Spread)'
    radial=f'(User.Side*cos({angle})+User.Forward*sin({angle}))'
    origin=f'User.Origin+{radial}*({radius})+User.Up*(User.CellSize*.8)'
    drift=f'(User.Side*cos({variant}*6.283185)+User.Forward*sin({variant}*6.283185))*8'
    assignments(system,en,'ParticleSpawnScript',{
        'Particles.FireOrigin':(POSITION,origin),
        'Particles.FireUp':(VEC3,'User.Up'),
        'Particles.FireStrength':(FLOAT,f'(.75+.3*{variant})*({core}?1.2:1.0)'),
        'Particles.Lifetime':(FLOAT,f'.55+.30*{variant}'),
        'Particles.Position':(POSITION,origin),
        'Particles.Velocity':(VEC3,f'User.Up*(90+80*{variant})+{drift}'),
        'Particles.Color':(COLOR,'float4(1,1,1,1)'),
    })
    assignments(system,en,'ParticleUpdateScript',{
        'Particles.Position':(POSITION,'Particles.FireOrigin+Particles.FireUp*(Particles.Age*6)'),
    })
    API.call_method('AddModule',(ref(system,en,'ParticleUpdateScript'),u.load_asset('/NiagaraFluids/Modules/Particles/SetFluidSourceAttributes')))
    sc='ParticleUpdateScript';mod='SetFluidSourceAttributes'
    strength=f'Particles.FireStrength*(.82+.18*sin(Particles.Age*9+{variant}*6.283185))*saturate(User.Fade)'
    expression(system,en,sc,mod,'Density',f'.12*({strength})')
    expression(system,en,sc,mod,'Temperature',f'5.0*({strength})')
    expression(system,en,sc,mod,'Velocity','Particles.Velocity')
    expression(system,en,sc,mod,'Velocity Scale','.7')
    expression(system,en,sc,mod,'Radius',patch)
    put(system,en,sc,mod,'Divergence','(Value=0.0)')
    put(system,en,sc,mod,'Transform To WorldSpace','(Value=0)','/Script/Niagara.NiagaraBool')
