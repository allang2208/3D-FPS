"""Five fluid integrations: incremental Niagara/material authoring, no play/preview/tests."""
import json,sys,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir())
OUT=ROOT/'SourceAssets/FluidInteractions20260924'
DEST='/Game/Fluids/FluidInteractions20260924'
sys.path[:0]=[str(ROOT/'Tools/Fluids'),str(ROOT/'Tools/Skills')]
import author_impact_smoke_corrosion as smoke
import author_venom_projectiles as venom
from build_fireball_assets import API,ref,emitters,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from fluid_contact_nodes import contact_nodes,clear_contact_tags
E=u.EditorAssetLibrary
STEAM=DEST+'/NS_WaterImpactSteam'
WATER='/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash'

def steam():
    s=u.load_asset(STEAM) if E.does_asset_exist(STEAM) else E.duplicate_asset(smoke.SYSTEMS[0][0],STEAM)
    for name in emitters(s):API.call_method('RemoveEmitter',(ref(s,name),))
    for name,typ in [('Wind',VEC3),('LocalUp',VEC3),('DetailReduction',FLOAT),('ImpactGrowth',FLOAT),('SteamCount',FLOAT)]:
        user_parameter(s,name,typ)
    name='WaterSteam';clear_contact_tags(s,name)
    API.call_method('AddEmitter',(s,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),name))
    trim(s,name,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,name),{'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,name,renderer=0),{
        'Material':smoke.DEST+'/M_RollingImpactSmoke.M_RollingImpactSmoke',
        'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,
        'PivotInUVSpace':{'X':.5,'Y':.5},'Alignment':'Unaligned','FacingMode':'FaceCamera',
        'bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False,
        'bEnableCameraDistanceCulling':True,'MinCameraDistance':0,'MaxCameraDistance':7000})
    source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    for key,old,new in [('Life Cycle Mode','System','Self'),('Loop Behavior','Infinite','Once')]:
        value=u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState',key)
        value=value.replace('NewEnumerator0','NewEnumerator1').replace('"'+old+'"','"'+new+'"')
        put(s,name,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(s,name,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=1.6)')
    API.call_method('AddModule',(ref(s,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(s,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
        '(HlslExpression="floor(User.SteamCount*(1-saturate(User.DetailReduction))+.5)")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(s,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
    seed='frac(float(Particles.UniqueID)*.61803399+frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453))'
    a='Particles.Age';n='Particles.NormalizedAge'
    pos=f'float3(cos({seed}*6.283185),sin({seed}*6.283185),0)*(12+{a}*(42+24*{seed}))+User.LocalUp*(9+{a}*(52+32*{seed}))+User.Wind*({a}-.35*(1-exp(-{a}/.35)))'
    envelope=smooth('0','.08',n)+'*(1-'+smooth('.25','1',n)+')'
    common={'Particles.Position':(POSITION,pos),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteSize':(VEC2,f'float2(105,125)*(.45+{n}*1.25)*(1+max(0,User.ImpactGrowth))'),
        'Particles.SpriteRotation':(FLOAT,f'({seed}-.5)*.8+{a}*.08'),
        'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.Color':(COLOR,f'float4(.58,.62,.64,.34*{envelope}*saturate((7000-Engine.Owner.LODDistance)/2500))'),
        'Particles.DynamicMaterialParameter':('/Script/CoreUObject.Vector4f',f'float4({seed},0,0,0)')}
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:E.remove_metadata_tag(s,'Fireball.Assignments.'+name+'.'+script)
    assignments(s,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,f'.85+.40*{seed}'),**common})
    assignments(s,name,'ParticleUpdateScript',common)
    contact_nodes(s,name)
    s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-360,-360,-40),max=u.Vector(360,360,420)))
    smoke.save(s)

def water_budget():
    s=u.load_asset(WATER);user_parameter(s,'DetailReduction',FLOAT)
    # Only burst count changes. Preserve the accepted crown graph, atlas and square-edge fix.
    count='(User.Strength<.5?(Engine.Owner.LODDistance<4000?4:2):(Engine.Owner.LODDistance<1800?12:(Engine.Owner.LODDistance<4000?7:3)))'
    put(s,'WaterDrops','EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
        '(HlslExpression="floor('+count+'*(1-saturate(User.DetailReduction))+.5)")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    smoke.save(s)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    targets=[p for p,_ in smoke.SYSTEMS]+[WATER,STEAM,venom.DEST+'/M_WitchPoisonPool']
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active game')
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(targets):raise RuntimeError('Preserve unsaved target assets: '+str(dirty.intersection(targets)))
    for path in targets:
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=OUT/'Backup'/disk.relative_to(ROOT/'Content')
        if disk.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    E.make_directory(DEST)
    for path,meteor in smoke.SYSTEMS:smoke.impact_smoke(u.load_asset(path),meteor)
    steam();water_budget();venom.pool()
    if not u.PoisonMaggotMonster.compile_material_assets([u.load_asset(venom.DEST+'/M_WitchPoisonPool')]):
        raise RuntimeError('Pool material shader compile failed')
    E.save_loaded_asset(u.load_asset(venom.DEST+'/M_WitchPoisonPool'),False)
    (OUT/'assets-saved.json').write_text(json.dumps({'saved':smoke.SAVED+venom.SAVED,
        'steam_slots':6,'splash_slots':12,'ripple_slots':8,'new_textures':0,
        'native_build':'recorded separately','game_tested':False,'visual_tested':False,'performance_measured':False},indent=2),encoding='utf8')
    print('FLUID_INTERACTIONS_ASSETS_SAVED',len(smoke.SAVED+venom.SAVED))

if __name__=='__main__':main()
