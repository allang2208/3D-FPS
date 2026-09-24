"""Five local contact planes shared by impact smoke, steam and cold impact mist."""
import unreal as u
from build_fireball_assets import API,ref,put
from build_fireball_flight import user_parameter
from build_fireball_flames import POSITION,COLOR

def contact_nodes(system,emitter):
    for i in range(5):user_parameter(system,'SmokePlane'+str(i),'/Script/CoreUObject.Vector4f')
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:
        # These modules follow the emitter's authored motion/color, so projections
        # accumulate across corner planes without a large repeated expression tree.
        for i in range(5):
            tag=f'FluidContact.{emitter}.{script}.{i}'
            module=u.EditorAssetLibrary.get_metadata_tag(system,tag)
            if not module:
                entries=[]
                for name,typ in [('Particles.Position',POSITION),('Particles.Color',COLOR)]:
                    entry=u.NiagaraExt_SetParameterEntry()
                    entry.import_text('(Variable=(Name="'+name+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))')
                    entries.append(entry)
                module=str(API.call_method('AddSetParametersModule',(ref(system,emitter,script),entries)).get_editor_property('module_name'))
                u.EditorAssetLibrary.set_metadata_tag(system,tag,module)
            plane=f'User.SmokePlane{i}'
            penetration=f'max(0,{plane}.w-dot(Particles.Position,{plane}.xyz))'
            expressions={'Particles.Position':f'Particles.Position+{plane}.xyz*{penetration}',
                         'Particles.Color':f'float4(Particles.Color.rgb,Particles.Color.a*exp(-{penetration}*.018))'}
            for name,expression in expressions.items():
                put(system,emitter,script,module,name,'(HlslExpression="'+expression+'")',
                    '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')

def clear_contact_tags(system,emitter):
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:
        for i in range(5):u.EditorAssetLibrary.remove_metadata_tag(system,f'FluidContact.{emitter}.{script}.{i}')
