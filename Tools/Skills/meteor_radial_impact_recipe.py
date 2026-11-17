"""Shared radial wave/spark recipe for full rebuilds and incremental authoring."""
from build_fireball_assets import assignments, put
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_slow_burn import smooth

VEC4='/Script/CoreUObject.Vector4f'
A,N='Particles.Age','Particles.NormalizedAge'
SEED='frac(float(Particles.UniqueID)*.61803398875+.173)'
VAR='frac(float(Particles.UniqueID)*.41421356237+.317)'
ANGLE='(float(Particles.UniqueID)*2.39996323+.4)'
DIR=f'float3(cos({ANGLE}),sin({ANGLE}),0)'
DETAIL='(1-saturate(User.DetailReduction))'
REVISION=2


def apply(system):
    def update(name,count,delay,life,values):
        put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
            f'(HlslExpression="{count}")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time',f'(Value={delay})')
        assignments(system,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**values})
        assignments(system,name,'ParticleUpdateScript',values)

    # One surface-aligned sprite. Shape radius ~0.41 of its width; compensate
    # that coverage so the visible wave travels beyond the fire crown.
    wave_diameter=f'(135+min(User.ImpactRadius*2.70,3400)*(1-exp(-{A}*6.5)))'
    wave_cooling=smooth(.12,.78,N)
    update('RefGroundShockFront','(User.SurfaceHit>.5?1:0)',.02,'.62',{
        'Particles.Position':(POSITION,'User.LocalUp*10'),
        'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteSize':(VEC2,f'float2(1,1)*{wave_diameter}'),
        'Particles.Color':(COLOR,f'float4(lerp(float3(1,.64,.22),float3(.44,.31,.20),{wave_cooling}),.82*(1-{smooth(.30,1,N)}))'),
        'Particles.DynamicMaterialParameter':(VEC4,f'float4({N},.37,2.1*exp(-{N}*4.2)+.32,{wave_diameter})'),
        'Particles.SpriteFacing':(VEC3,'float3(0,0,1)'),
        'Particles.SpriteAlignment':(VEC3,'float3(0,1,0)'),
    })

    # Stable per-particle azimuth and drag: no combat RNG, new actors, collision
    # queries or lights. Sparks fade on reaching the impact plane, never hover.
    for name,count,delay,life,speed,up,drag,ember in [
        ('RefHotRadialSplinters',36,.018,f'.48+.30*{SEED}',f'870+750*{SEED}',
         f'530+620*{VAR}',1.3,False),
        ('RefCoolingEmbers',24,.045,f'1.05+.65*{VAR}',f'420+620*{VAR}',
         f'420+440*{SEED}',1.4,True),
    ]:
        z=f'(22+({up})*{A}-490*{A}*{A})'
        travel=f'((1-exp(-{drag}*{A}))/{drag})'
        velocity=f'({DIR}*({speed})*exp(-{drag}*{A})+User.LocalUp*(({up})-980*{A}))'
        ground_fade=f'(User.SurfaceHit>.5?saturate(({z}-4)/18):1)'
        alpha=f'.95*(1-{smooth(.62,1,N)})*{ground_fade}'
        size=(f'float2(6.5+3.5*{VAR},9+7*{SEED})*(1-.40*{N})' if ember else
              f'float2(4.8+2.2*{VAR},clamp(length({velocity})*.035,12,52))*(1-.35*{N})')
        flicker=f'(1-.20*pow(sin({A}*37+{VAR}*23),2))' if ember else '1'
        update(name,f'floor({count}*{DETAIL}+.5)',delay,life,{
            'Particles.Position':(POSITION,f'{DIR}*((18+({speed})*{travel}))+User.LocalUp*max(4,{z})'),
            'Particles.Velocity':(VEC3,velocity),
            'Particles.SpriteAlignment':(VEC3,f'normalize({velocity}+float3(0,0,.001))'),
            'Particles.SpriteSize':(VEC2,size),
            'Particles.Color':(COLOR,f'float4(1,lerp(.78,.13,{N}),lerp(.29,.008,{N}),{alpha})'),
            'Particles.DynamicMaterialParameter':(VEC4,f'float4({N},{VAR},(4.4*pow(saturate(1-{N}),1.1)+.8)*{flicker},{1 if ember else 0})'),
        })
