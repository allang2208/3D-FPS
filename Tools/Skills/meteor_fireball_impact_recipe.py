"""Replace meteor combustion with copies of the live fireball impact emitters."""
import json
import unreal as u
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
from build_fireball_flames import FLOAT, VEC2, POSITION, COLOR
from meteor_renderer_bindings import bind_impact_attributes

E=u.EditorAssetLibrary
SOURCE='/Game/Skills/Fireball/ImpactRealistic20260914/'
DEST='/Game/Skills/FireMagic20260921/MeteorFireballImpactV8/'
MATERIAL_NAMES=('M_MeteorFireballCombustion','MI_MeteorFireballCombustion')
REPLACED=('RefWhiteHotCore','RefPressureFireCrown',
          'RefVolumeCenterRoll','RefVolumeShoulderA','RefVolumeShoulderB')
LAYERS=(('ContactIgnition','FireballMeteorContact',1,1.08),
        ('OutwardCombustion','FireballMeteorCombustion',8,2.05))
REVISION=2


def retime_outward_position(system,name):
    # Preserve the original path and final spread while taking longer to
    # traverse it. Only the copied combustion's position clock is changed;
    # ParticleState and the system/impact clocks continue to use real time.
    scale=1.18/2.05
    topology=API.call_method('GetEmitterTopology',(ref(system,name),))
    changed=[]
    for field in ('particle_spawn_script','particle_update_script'):
        stack=topology.get_editor_property(field)
        stage=str(stack.get_editor_property('script_name'))
        for module in stack.get_editor_property('modules'):
            module_name=str(module.get_editor_property('module_name'))
            if not module_name.startswith('SetVariables_'):continue
            text=u.RainAssetEditor.read_input(system,name,stage,module_name,'Particles.Position')
            if not text:continue
            value=u.NiagaraExt_StackInputData_HlslExpression()
            value.import_text(text)
            expression=str(value.get_editor_property('hlsl_expression'))
            if 'Particles.Age' not in expression:continue
            expression=expression.replace('Particles.Age',f'(Particles.Age*{scale:.9f})')
            put(system,name,stage,module_name,'Particles.Position',
                '(HlslExpression="'+expression+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
            changed.append(stage)
    if set(changed)!={'ParticleSpawnScript','ParticleUpdateScript'}:
        raise RuntimeError('Could not retime the copied fireball position graph: '+name)
    return scale


def rolling_atlas_frame():
    # Keep the ignition brisk. Spend the additional time in the orange rolling
    # frames, then play the complete cooling tail rather than freezing a tile.
    age='Particles.Age'
    progress=f'saturate(({age}-.075)/max(.01,Particles.Lifetime-.075))'
    return f'({age}<.075?14*{age}/.075:14+48.95*pow({progress},1.35))'


def author_materials():
    E.make_directory(DEST.rstrip('/'))
    materials=[]
    for source,name in zip(('M_ImpactCombustion','MI_ImpactCombustion'),MATERIAL_NAMES):
        path=DEST+name
        material=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(SOURCE+source,path)
        if not material:raise RuntimeError('Missing fireball combustion source: '+source)
        materials.append(material)
    parent,instance=materials
    LIB.set_material_instance_parent(instance,parent)
    # Retain the actual fireball texture, normals, temperature and opacity.
    # A modest gain increase accompanies the larger, denser meteor body.
    for key,value in (('Emissive Gain',1.85),('Depth Fade Distance',24.0)):
        LIB.set_material_instance_scalar_parameter_value(instance,key,value)
    LIB.update_material_instance(instance)
    for asset in materials:E.set_metadata_tag(asset,'Meteor.FireballImpact.Revision',str(REVISION))
    return materials


def apply(system,material):
    donor=u.load_asset(SOURCE+'NS_FireballImpactRealistic')
    if not donor:raise RuntimeError('Missing runtime fireball impact donor')
    # Copy the actual embedded emitters. Their SubUV animation, cooling,
    # normal shading, variation and outward deceleration remain intact.
    templates=[obj for obj in u.ObjectIterator(u.NiagaraEmitter) if obj.get_outer()==donor]
    handles={source:next((obj for obj in templates if obj.get_name()==source or obj.get_name().startswith(source+'_')),None)
             for source,_,_,_ in LAYERS}
    if any(handle is None for handle in handles.values()):
        raise RuntimeError('Missing embedded fireball combustion emitter')
    # Source graphs still read this fireball parameter. Carry its authored
    # default; meteor scaling is applied separately after the copied graphs.
    source_users=API.call_method('GetUserVariables',(donor,)).get_editor_property('user_variables')
    growth=[value for value in source_users if str(value.get_editor_property('name'))=='User.ImpactGrowth']
    if not growth:raise RuntimeError('Missing fireball ImpactGrowth input')
    API.call_method('AddUserVariables',(system,growth))
    current=set(emitters(system))
    # Remove only the rejected fire crown/lobes and our previous copies.
    for name in REPLACED+tuple(row[1] for row in LAYERS):
        if name in current:API.call_method('RemoveEmitter',(ref(system,name),))
        for stage in ('ParticleSpawnScript','ParticleUpdateScript'):
            E.remove_metadata_tag(system,'Fireball.Assignments.'+name+'.'+stage)

    width='(3.25*clamp(User.ImpactRadius/652.5,.85,1.30))'
    height='(3.05*clamp(sqrt(User.ImpactRadius/652.5),.85,1.25))'
    source_growth='max(.01,1+User.ImpactGrowth)'
    # The fireball actor scales local positions by .765, whereas sprite sizes
    # are world units. Reproduce that distinction inside the meteor system.
    position=f'float3(Particles.Position.xy*({width}*.765),Particles.Position.z*({height}*.765))'
    size=f'Particles.SpriteSize*float2({width},{height})/{source_growth}'
    for source,name,count,duration in LAYERS:
        API.call_method('AddEmitter',(system,handles[source],name))
        # Sever the private emitter parent after copying. Saving must not link
        # the meteor package back to a private object in the fireball package.
        no_parent={'Emitter':'None','Version':'00000000-0000-0000-0000-000000000000'}
        setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),
                {'VersionedParent':no_parent,'VersionedParentAtLastMerge':no_parent})
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),
                {'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
                 'bEnableCameraDistanceCulling':True,'MinCameraDistance':0,'MaxCameraDistance':10000})
        if count>1:
            # Keep at least four moving fire masses at the existing low-detail
            # setting; only decoration density drops with the presentation budget.
            put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
                '(HlslExpression="4+floor(4*(1-saturate(User.DetailReduction))+.5)")',
                '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
            retime_outward_position(system,name)
        fields={'Particles.Position':(POSITION,position),'Particles.SpriteSize':(VEC2,size)}
        if count>1:
            fields['Particles.SubImageIndex']=(FLOAT,rolling_atlas_frame())
        # Post modules follow the donor's absolute position/size writes every
        # frame, so scale never accumulates from one update to the next.
        assignments(system,name,'ParticleSpawnScript',
                    {'Particles.Lifetime':(FLOAT,f'Particles.Lifetime*{duration}'),**fields})
        assignments(system,name,'ParticleUpdateScript',fields)
    bind_impact_attributes(system,[row[1] for row in LAYERS])
    E.remove_metadata_tag(system,'Meteor.ExplosionVolume.Revision')
    E.set_metadata_tag(system,'Meteor.FireballImpact.Revision',str(REVISION))
    E.set_metadata_tag(system,'Meteor.FireballImpact.Source',donor.get_path_name())
    return dict(revision=REVISION,source=donor.get_path_name(),source_layers=[row[0] for row in LAYERS],
                retired_layers=list(REPLACED),horizontal_scale_at_baseline=3.25,vertical_scale_at_baseline=3.05,
                local_position_calibration=.765,contact_lifetime_multiplier=1.08,combustion_lifetime_multiplier=2.05,
                combustion_position_clock_scale=1.18/2.05,combustion_lifetime_range_seconds=[.984,1.476],
                ignition_knee_seconds=.075,ignition_knee_atlas_frame=14,rolling_playback_exponent=1.35,
                moving_flame_particles=8,combustion_particles=9,max_impact_particles=88,smoke_budget=16,
                material=material.get_path_name())
