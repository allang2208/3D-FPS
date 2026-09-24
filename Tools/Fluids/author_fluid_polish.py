"""Smoke contacts, blood liquids, cold impacts and water wakes. Authoring only."""
import sys,json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir());OUT=ROOT/'SourceAssets/FluidPolish20260924'
DEST='/Game/Fluids/FluidPolish20260924';BLOOD='/Game/Weapons/GunplayFX/Impacts/Blood'
sys.path[:0]=[str(ROOT/'Tools/Fluids'),str(ROOT/'Tools/Skills')]
import author_impact_smoke_corrosion as smoke
import author_fluid_interactions as interactions
from author_river_pilot import node,wire,custom,vector,scalar,prop
from build_fireball_assets import API,ref,put,emitters
from build_fireball_flight import user_parameter
from build_fireball_flames import FLOAT,VEC3
from water_wake_authoring import wake_inputs
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
WATERS=['/Game/Fluids/RiverPilot20260923/M_RiverPilot',
        '/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3',
        '/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle']
COLD='/Game/Skills/IceSpike/FrostV2/NS_ColdMist'

def code(name):return (OUT/(name+'.hlsl')).read_text(encoding='utf8')

def blood_materials():
    path=BLOOD+'/M_FleshDropletV2';m=smoke.material(path,instanced=True)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    owned=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
                and n.get_editor_property('description')=='Fluid polish blood drop'),None)
    if not owned:
        tex=node(m,u.MaterialExpressionTextureObject);tex.set_editor_property('texture',u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Droplets_A'))
        age=smoke.instance_data(m,4);seed=smoke.instance_data(m,5);alpha=smoke.instance_data(m,3)
        channels=[smoke.instance_data(m,i) for i in range(3)]
        tint=custom(m,'return float3(R,G,B)*lerp(1,.8,Age);',dict(zip(['R','G','B'],channels))|{'Age':age},3)
        owned=custom(m,code('BloodDroplet'),{'UV':node(m,u.MaterialExpressionTextureCoordinate),'Age':age,'Variation':seed,'Drops':tex},1,'Fluid polish blood drop')
        opacity=custom(m,'return Shape*Alpha;',{'Shape':owned,'Alpha':alpha})
        depth=node(m,u.MaterialExpressionDepthFade);depth.set_editor_property('fade_distance_default',.5)
        wire(opacity,depth,str(L.get_material_expression_input_names(depth)[0]))
        smoke.surface(m,{'BASE_COLOR':tint,'OPACITY':depth,'ROUGHNESS':smoke.constant(m,.22),'SPECULAR':smoke.constant(m,.5)})
    else:owned.set_editor_property('code',code('BloodDroplet'))
    smoke.save(m)
    m=smoke.material(BLOOD+'/M_FleshStainV3',decal=True)
    owned=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
                and n.get_editor_property('description')=='Fluid polish blood stain'),None)
    if not owned:
        color=node(m,u.MaterialExpressionDecalColor)
        tex=node(m,u.MaterialExpressionTextureObject);tex.set_editor_property('texture',u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Droplets_A'))
        clock=node(m,u.MaterialExpressionTime)
        owned=custom(m,code('BloodStain'),{'UV':node(m,u.MaterialExpressionTextureCoordinate),'Seed':(color,'R'),
            'Born':(color,'G'),'Wall':(color,'B'),'Clock':clock,'Drops':tex},1,'Fluid polish blood stain')
        age=custom(m,'return saturate(max(0,Clock-Born)/14);',{'Clock':clock,'Born':(color,'G')})
        tint=custom(m,'return lerp(float3(.22,.006,.004),float3(.078,.0028,.002),Age);',{'Age':age},3)
        rough=custom(m,'return lerp(.17,.70,Age);',{'Age':age})
        alpha=custom(m,'return Mask*Life;',{'Mask':owned,'Life':node(m,u.MaterialExpressionDecalLifetimeOpacity)})
        smoke.surface(m,{'BASE_COLOR':tint,'OPACITY':alpha,'ROUGHNESS':rough,'SPECULAR':smoke.constant(m,.42)},decal=True)
    else:owned.set_editor_property('code',code('BloodStain'))
    smoke.save(m)

def cold_impact():
    path=DEST+'/NS_IceImpactMist'
    s=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(interactions.STEAM,path)
    en='WaterSteam'
    seed='frac(float(Particles.UniqueID)*.61803399+frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453))'
    age='Particles.Age';norm='Particles.NormalizedAge'
    pos=f'float3(cos({seed}*6.283185),sin({seed}*6.283185),0)*(8+{age}*(35+25*{seed}))+User.LocalUp*(3+{age}*6)+User.Wind*{age}*.35'
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:
        topology=API.call_method('GetScriptStackTopology',(ref(s,en,script),))
        modules=[n for n in topology.get_editor_property('modules') if {'Particles.SpriteSize','Particles.Position','Particles.Color'}.issubset(
            {str(i.get_editor_property('name')) for i in n.get_editor_property('inputs')})]
        if len(modules)!=1:raise RuntimeError('Cold impact motion module is ambiguous')
        module=str(modules[0].get_editor_property('module_name'))
        expressions={'Particles.Position':pos,'Particles.SpriteSize':f'float2(80,48)*(.55+{norm}*1.1)',
            'Particles.Color':f'float4(.48,.61,.66,.26*saturate({norm}*12)*pow(1-{norm},1.5)*saturate((6500-Engine.Owner.LODDistance)/2500))'}
        if script=='ParticleSpawnScript':expressions['Particles.Lifetime']=f'1.1+.35*{seed}'
        for name,value in expressions.items():put(s,en,script,module,name,'(HlslExpression="'+value+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    smoke.save(s)

def cold_trail():
    s=u.load_asset(COLD);en='RocketTrail'
    user_parameter(s,'Wind',VEC3);user_parameter(s,'DetailReduction',FLOAT)
    put(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate',
        '(HlslExpression="saturate(User.Strength)*(18+User.Flight*65+User.ReleasePulse*90)*(1-saturate(User.DetailReduction))")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    topology=API.call_method('GetScriptStackTopology',(ref(s,en,'ParticleSpawnScript'),))
    modules=[m for m in topology.get_editor_property('modules') if {'Particles.Position','Particles.Velocity','Particles.Lifetime'}.issubset(
        {str(i.get_editor_property('name')) for i in m.get_editor_property('inputs')})]
    if len(modules)!=1:raise RuntimeError('Cold trail spawn module is ambiguous')
    module=str(modules[0].get_editor_property('module_name'))
    seed='frac(float(Particles.UniqueID)*.61803398875)';variation='frac(float(Particles.UniqueID)*.754877666)'
    radial=f'(User.Side*cos({variation}*6.2831853)+User.Up*sin({variation}*6.2831853))'
    expression=f'{radial}*(6+{seed}*8)+float3(0,0,-15)-User.FlightDirection*User.Flight*38+User.Wind'
    put(s,en,'ParticleSpawnScript',module,'Particles.Velocity','(HlslExpression="'+expression+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    smoke.save(s)

def water_wakes():
    field_code=(ROOT/'SourceAssets/RiverPilot20260923/RippleField.hlsl').read_text(encoding='utf8')
    for path in WATERS:
        m=u.load_asset(path)
        fields=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
                and n.get_editor_property('description') in ['River pilot bullet ripples','All water impact field']]
        if len(fields)!=1:raise RuntimeError('Water field not unique '+path)
        wake_inputs(m,fields[0]);fields[0].set_editor_property('code',field_code);smoke.save(m)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    targets=[p for p,_ in smoke.SYSTEMS]+[interactions.STEAM,DEST+'/NS_IceImpactMist',COLD,
             BLOOD+'/M_FleshDropletV2',BLOOD+'/M_FleshStainV3']+WATERS
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active game')
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(targets):raise RuntimeError('Preserve unsaved target assets '+str(dirty.intersection(targets)))
    for path in targets:
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=OUT/'Backup'/disk.relative_to(ROOT/'Content')
        if disk.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    E.make_directory(DEST)
    for path,meteor in smoke.SYSTEMS:smoke.impact_smoke(u.load_asset(path),meteor)
    interactions.steam();cold_impact();cold_trail();blood_materials();water_wakes()
    materials=[u.load_asset(p) for p in smoke.SAVED if isinstance(u.load_asset(p),u.Material)]
    if not u.PoisonMaggotMonster.compile_material_assets(materials):raise RuntimeError('Material compilation failed')
    for material in materials:
        if not E.save_loaded_asset(material,False):raise RuntimeError('Final material save failed')
    (OUT/'assets-saved.json').write_text(json.dumps({'saved':smoke.SAVED,'new_textures':0,'cold_impact_pool':8,
        'wake_records':4,'tests_run':False,'performance_measured':False},indent=2),encoding='utf8')
    print('FLUID_POLISH_ASSETS_SAVED',len(smoke.SAVED))

if __name__=='__main__':main()
