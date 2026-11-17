"""Author only the meteor impact revision from the inspected video reference.

Use DragonBreathAuthor commandlet. V6 flight and all ground/gameplay remain.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_meteor_combustion_v6 as base

OUT=ROOT/'SourceAssets/MeteorImpactReferenceV7_20261114'
DEST='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7'
base.OUT,base.DEST=OUT,DEST
base.SAVED.clear()
E,LIB=base.E,base.LIB
FLOAT,VEC2,VEC3,VEC4,POSITION,COLOR=base.FLOAT,base.VEC2,base.VEC3,base.VEC4,base.POSITION,base.COLOR
A,N=base.A,base.N
SEED,VAR,ANGLE,DIR=base.SEED,base.VAR,base.ANGLE,base.DIR
R,H='User.ImpactRadius','clamp(sqrt(User.ImpactRadius/652.5),.85,1.25)'
smooth=base.smooth


def fields_material(name,tex,smoke=False):
    mat=base.material(name,tex,smoke)
    for node in LIB.get_material_expressions(mat):
        if isinstance(node,u.MaterialExpressionDepthFade):
            node.set_editor_property('fade_distance_default',24.0 if smoke else 18.0)
        if not isinstance(node,u.MaterialExpressionCustom):
            continue
        tag=node.get_editor_property('description')
        if tag=='MeteorV6.Sample':
            node.set_editor_property('code',(ROOT/'Tools/Skills/meteor_reference_v7_sample.hlsl').read_text(encoding='utf8'))
        elif tag=='MeteorV6.Opacity':
            node.set_editor_property('code','return (1-exp(-pow(max(0,Fields.b-.008),.85)*4.8))*Alpha;' if smoke else 'return (1-exp(-max(0,Fields.r-.003)*4.2))*Alpha;')
        elif tag=='MeteorV6.Thermal':
            node.set_editor_property('code',(ROOT/'Tools/Skills/meteor_reference_v7_thermal.hlsl').read_text(encoding='utf8'))
    E.set_metadata_tag(mat,'Meteor.ReferenceV7','Pressure impulse: video 231-232s and 444.7-445.5s')
    base.save(mat)
    return mat


def analytic_material(name,kind):
    mat=base.own(name)
    if not E.get_metadata_tag(mat,'Meteor.ReferenceV7.Analytic'):
        for key,value in dict(blend_mode=u.BlendMode.BLEND_ALPHA_COMPOSITE,
            shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True,
            disable_depth_test=False,enable_responsive_aa=True,
            allow_front_layer_translucency=False,output_translucent_velocity=False,
            is_translucency_velocity_from_depth=False,
            translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF).items():
            mat.set_editor_property(key,value)
        LIB.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True)
        uv=base.node(mat,u.MaterialExpressionTextureCoordinate)
        color=base.node(mat,u.MaterialExpressionParticleColor)
        dynamic=base.node(mat,u.MaterialExpressionDynamicParameter,param_names=['Age','Seed','Energy','Unused'])
        code=(ROOT/('Tools/Skills/meteor_reference_v7_'+kind+'.hlsl')).read_text(encoding='utf8')
        coverage=base.custom(mat,'MeteorV7.Shape',code,{'UV':uv,'Dynamic':(dynamic,'RGBA')},1)
        alpha=base.node(mat,u.MaterialExpressionMultiply)
        base.wire(coverage,alpha,'A');base.wire(color,alpha,'B','A')
        fade=base.node(mat,u.MaterialExpressionDepthFade,fade_distance_default=3. if kind=='pressure' else 2.)
        base.wire(alpha,fade,str(LIB.get_material_expression_input_names(fade)[0]))
        energy=base.custom(mat,'MeteorV7.Energy','return Tint*max(0,Dynamic.z);',
                           {'Tint':(color,'RGB'),'Dynamic':(dynamic,'RGBA')},3)
        exposure=base.node(mat,u.MaterialExpressionEyeAdaptationInverse)
        base.wire(energy,exposure,str(LIB.get_material_expression_input_names(exposure)[0]))
        premult=base.node(mat,u.MaterialExpressionMultiply)
        base.wire(exposure,premult,'A');base.wire(fade,premult,'B')
        LIB.connect_material_property(premult,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        LIB.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
        E.set_metadata_tag(mat,'Meteor.ReferenceV7.Analytic',kind)
    else:
        for node in LIB.get_material_expressions(mat):
            if isinstance(node,u.MaterialExpressionCustom) and node.get_editor_property('description')=='MeteorV7.Shape':
                node.set_editor_property('code',(ROOT/('Tools/Skills/meteor_reference_v7_'+kind+'.hlsl')).read_text(encoding='utf8'))
    base.save(mat)
    return mat


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    E.make_directory(DEST)
    tex=base.texture('Blast')
    contract=json.loads((OUT/'Blast/atlas-manifest.json').read_text(encoding='utf8'))
    # Fire is present in only the initial tiles; the remaining tiles are smoke.
    # Never interpret the shared 64-frame atlas as 64 frames of combustion.
    fire_first,fire_last=contract['playback_windows']['fire']
    frame_denominator=contract['frames']-1
    fire_age=f'(({fire_first}+.35+({fire_last-fire_first}-.35)*pow({N},.72))/{frame_denominator})'
    core_age=f'(({fire_first}+.35+({fire_last-fire_first}*.55)*{N})/{frame_denominator})'
    fire=fields_material('M_PressureCombustionV7',tex)
    smoke=fields_material('M_PressureAfterSmokeV7',tex,True)
    flash=analytic_material('M_ContactFlashV7','flash')
    rays=analytic_material('M_PressureRaysV7','rays')
    pressure=analytic_material('M_GroundPressureV7','pressure')
    spark=analytic_material('M_HotEjectaV7','spark')
    defaults=[('ImpactRadius',FLOAT,'(Value=652.5)'),('LocalUp',VEC3,'(X=0,Y=0,Z=1)'),
        ('SurfaceHit',FLOAT,'(Value=1)'),('DetailReduction',FLOAT,'(Value=0)'),
        ('Wind',VEC3,'(X=0,Y=0,Z=0)'),('WetImpact',FLOAT,'(Value=0)')]
    system=base.system('NS_MeteorPressureV7',
        '/Game/Skills/FireMagic20260921/MeteorCombustionV6/NS_MeteorCollisionV6',
        defaults,[(-1800,-1800,-400),(1800,1800,1400)])

    def burst(name,material,count,delay,life,size,position,color,dynamic,
              pivot=.5,ground=False,dust=False,align=None,velocity='float3(0,0,0)'):
        values={'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,velocity),
            'Particles.SpriteSize':(VEC2,size),'Particles.Color':(COLOR,color),
            'Particles.DynamicMaterialParameter':(VEC4,dynamic)}
        if ground:
            values.update({'Particles.SpriteFacing':(VEC3,'float3(0,0,1)'),
                           'Particles.SpriteAlignment':(VEC3,'float3(0,1,0)')})
        if align:
            values['Particles.SpriteAlignment']=(VEC3,align)
        base.layer(system,name,material,True,{'Particles.Lifetime':(FLOAT,life),**values},values,
            count=count,delay=delay,dust=dust,align=bool(align) or ground,pivot=pivot)
        if ground:
            base.setdata('SetRendererData',u.NiagaraExt_RendererData,base.ref(system,name,renderer=0),
                {'FacingMode':'CustomFacingVector','Alignment':'CustomAlignment'})

    # One concentrated contact, followed by a coherent expanding crown.
    burst('RefContactImpulse',flash,1,0,'.085',
        f'float2(340,210)*{H}*(.78+.22*(1-exp(-{A}*90)))','User.LocalUp*52',
        f'float4(1,.87,.60,1-{smooth(.16,1,N)})',f'float4({N},0,21*exp(-{N}*5.8)+.2,0)')
    # The reference's conspicuous white radial fan is separate from drifting sparks.
    burst('RefRadialPressureFan',rays,1,.008,'.20',
        f'float2(1120,620)*{H}*(.65+.35*(1-exp(-{A}*42)))','User.LocalUp*18',
        f'float4(1,.82,.52,.88*(1-{smooth(.20,1,N)}))',
        f'float4({N},.27,8*pow(saturate(1-{N}),1.35)+.35,0)',pivot=.90)
    burst('RefWhiteHotCore',fire,1,.012,'.26',
        f'float2(480,340)*{H}*(.78+.25*(1-exp(-{A}*30)))','User.LocalUp*10',
        f'float4(1,1,1,.92*(1-{smooth(.48,1,N)}))',
        f'float4({core_age},0,3.8*pow(1-{N},2)+.2,0)',pivot=.97)
    burst('RefPressureFireCrown',fire,1,.025,'.82',
        f'float2(min({R}*1.75,1500),560*{H})*(.86+.14*(1-exp(-{A}*22)))','User.LocalUp*9',
        f'float4(1,1,1,.96*(1-{smooth(.57,1,N)}))',
        f'float4({fire_age},0,.95-.55*{N},0)',pivot=.97)
    # An irregular wave on the contact plane; no permanent luminous magic ring.
    burst('RefGroundShockFront',pressure,'(User.SurfaceHit>.5?1:0)',.012,'.34',
        f'float2(1,1)*(95+{R}*1.55*(1-exp(-{A}*13)))','float3(0,0,8)',
        f'float4(1,.40,.08,.64*(1-{N})*(1-{smooth(.52,1,N)}))',
        f'float4({N},.37,1.3*(1-{N})+.10,0)',ground=True)
    # Reference-visible radial needles cool into small ballistic embers.
    detail='(1-saturate(User.DetailReduction))'
    for name,count,delay,life,speed,up,size,alpha in [
        ('RefHotRadialSplinters',24,.018,f'.24+.21*{SEED}',f'430+640*{SEED}',f'240+620*{VAR}',
         f'float2(2.8+2*{VAR},29+45*{SEED})','.95'),
        ('RefCoolingEmbers',16,.035,f'.52+.45*{VAR}',f'210+420*{VAR}',f'280+490*{SEED}',
         f'float2(2+2*{VAR},7+10*{SEED})','.85')]:
        vel=f'{DIR}*({speed})+User.LocalUp*(({up})-840*{A})'
        position=f'{DIR}*(({speed})*{A})+User.LocalUp*max(4,22+({up})*{A}-420*{A}*{A})'
        burst(name,spark,f'floor({count}*{detail}+.5)',delay,life,
            f'{size}*(1-.55*{N})',position,
            f'float4(1,lerp(.86,.16,{N}),lerp(.40,.012,{N}),{alpha}*(1-{smooth(.45,1,N)}))',
            f'float4({N},{VAR},8*pow(1-{N},1.5)+.35,0)',
            align=f'normalize({vel}+float3(0,0,.001))',velocity=vel)
    # Same shared 16-particle smoke budget as V6; no native gameplay change.
    wind=f'User.Wind*({A}-.32*(1-exp(-{A}/.32)))'
    fade=f'{smooth(0,.07,N)}*(1-{smooth(.28,1,N)})'
    burst('RefLowPressureDust',smoke,f'(User.WetImpact<.5?floor(10*{detail}+.5):0)',.025,
        f'.48+.28*{VAR}',f'float2(205,62)*(.75+.3*{VAR})*(.72+.48*{N})',
        f'{DIR}*{R}*(.065+(.46+.27*{SEED})*(1-exp(-{A}*7)))+float3(0,0,20+{A}*16)+{wind}',
        f'float4(.29,.23,.17,.58*{fade})',f'float4(.3+.7*{N},{VAR},0,0)',dust=True)
    burst('RefCooledRollingSmoke',smoke,f'floor(6*{detail}+.5)',.22,
        f'1.22+.52*{VAR}',f'float2(280,260)*(.76+.3*{SEED})*(.65+.50*{N})',
        f'{DIR}*{R}*(.06+.21*{SEED})*(1-exp(-{A}*3.6))+User.LocalUp*(65+{A}*(58+26*{VAR}))+{wind}',
        f'float4(lerp(float3(.19,.16,.13),float3(.43,.46,.47),saturate(User.WetImpact)),.66*{fade})',
        f'float4(.30+.70*{N},{VAR},0,0)',dust=True)
    # Keep the current radial wave and ballistic sparks when rebuilding V7.
    from meteor_radial_impact_recipe import apply as apply_radial_impact
    apply_radial_impact(system)
    from meteor_fireball_impact_recipe import apply as apply_fireball_impact, author_materials
    fireball_materials=author_materials()
    for material in fireball_materials:base.save(material)
    fireball_profile=apply_fireball_impact(system,fireball_materials[-1])
    from meteor_renderer_bindings import bind_impact_attributes
    bind_impact_attributes(system)
    base.save(system)
    receipt=dict(complete=True,saved_assets=list(dict.fromkeys(base.SAVED)),
        impact_system=system.get_path_name(),max_particles=88,smoke_budget=16,fireball_combustion=fireball_profile,
        new_runtime_fluid_grids=0,new_lights=0,reference='BV1ZEWj6qE8S / peHi4w1SKEA',
        reference_times_seconds=[231,232,444.7,445.5],
        preserved=['rock and existing fragments','V6 flight','V4 low ground fire','damage and timing','sound','camera','scorch'],
        rendered=False,runtime_tested=False,visual_match_claimed=False)
    (OUT/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('METEOR_V7_AUTHOR_COMPLETE '+json.dumps(receipt),flush=True)


if __name__=='__main__':
    run()
