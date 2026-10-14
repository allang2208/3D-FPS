"""Invisible world-space combustion sources for the V8 volumetric dragon jet."""
import unreal as u
from build_fireball_assets import API,ref,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC3,POSITION,COLOR
from build_fireball_flight import expression


def build_sources(system):
    en='ParticleSourceEmitter'
    trim(system,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],
                    'ParticleSpawnScript':['InitializeParticle'],
                    'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:
        u.EditorAssetLibrary.remove_metadata_tag(system,'Fireball.Assignments.'+en+'.'+script)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,en),
            {'bLocalSpace':False,'SimTarget':'GPUComputeSim','InterpolatedSpawnMode':'NoInterpolation'})
    # These particles only feed the gas grid. No visible flame sprites remain.
    top=API.call_method('GetEmitterTopology',(ref(system,en),))
    for r in reversed(top.get_editor_property('renderers')):
        API.call_method('RemoveRenderer',(ref(system,en,renderer=r.get_editor_property('renderer_index')),))
    expression(system,en,'EmitterUpdateScript','SpawnRate','SpawnRate','360*saturate(User.EmissionScale)')
    seed='frac((float(Particles.UniqueID)+.5)*.61803398875)'
    variant='frac((float(Particles.UniqueID)+.5)*.41421356237)'
    # Seventy percent of the fuel forms the strong central jet. The remaining
    # fuel opens into the existing 90-degree spell fan, with symmetric births.
    yaw=f'(({seed}<.7)?(({seed}/.7-.5)*.26):((({seed}-.7)/.3-.5)*2*User.HalfAngle*.95))'
    pitch=f'({variant}-.5)*.12'
    direction=f'normalize(User.Forward*cos({yaw})+User.Side*sin({yaw})+User.Up*{pitch})'
    ray=f'clamp(int(floor(({yaw}/max(.01,User.HalfAngle)+1)*4+.5)),0,8)'
    limit='User.Ray8'
    for i in reversed(range(8)):limit=f'(({ray}=={i})?User.Ray{i}:{limit})'
    speed='(1450+clamp(User.Range,500,1500)*.75)'
    assignments(system,en,'ParticleSpawnScript',{
        'Particles.JetOrigin':(POSITION,'User.Origin'),
        'Particles.JetDirection':(VEC3,direction),
        'Particles.JetSide':(VEC3,'User.Side'),
        'Particles.JetUp':(VEC3,'User.Up'),
        'Particles.JetLimit':(FLOAT,f'min(User.Range,{limit})'),
        'Particles.JetSpeed':(FLOAT,speed),
        'Particles.JetCore':(FLOAT,f'({seed}<.7)?1:.55'),
        'Particles.Lifetime':(FLOAT,f'clamp(min(User.Range,{limit})/{speed}+.08,.06,.8)'),
        'Particles.Position':(POSITION,'User.Origin'),
        'Particles.Velocity':(VEC3,f'{direction}*{speed}'),
        'Particles.Color':(COLOR,'float4(1,1,1,1)'),
    })
    distance='min(Particles.Age*Particles.JetSpeed,Particles.JetLimit)'
    # A slight curved trajectory supplies broad rolling features; the fluid
    # solver supplies the visible evolution rather than card spin or scaling.
    curl=f'(Particles.JetSide*sin(Particles.Age*8+{variant}*6.283)+Particles.JetUp*cos(Particles.Age*6+{variant}*6.283))*({distance})*.022'
    assignments(system,en,'ParticleUpdateScript',{
        'Particles.Position':(POSITION,f'Particles.JetOrigin+Particles.JetDirection*({distance})+{curl}'),
        'Particles.Velocity':(VEC3,'Particles.JetDirection*Particles.JetSpeed'),
    })
    API.call_method('AddModule',(ref(system,en,'ParticleUpdateScript'),u.load_asset('/NiagaraFluids/Modules/Particles/SetFluidSourceAttributes')))
    sc='ParticleUpdateScript';mod='SetFluidSourceAttributes'
    edge='saturate((Particles.JetLimit-Particles.Age*Particles.JetSpeed)/max(25,User.CellSize*2))'
    # A light source density avoids the smoke blanket from earlier versions.
    expression(system,en,sc,mod,'Density',f'.22*({edge})')
    expression(system,en,sc,mod,'Temperature',f'(3.4+1.6*Particles.JetCore)*({edge})')
    expression(system,en,sc,mod,'Velocity','Particles.Velocity')
    expression(system,en,sc,mod,'Velocity Scale',f'.72*({edge})')
    expression(system,en,sc,mod,'Radius',f'max(User.CellSize*1.35,11+({distance})*.07)')
    put(system,en,sc,mod,'Divergence','(Value=0.0)')
    put(system,en,sc,mod,'Transform To WorldSpace','(Value=0)','/Script/Niagara.NiagaraBool')
