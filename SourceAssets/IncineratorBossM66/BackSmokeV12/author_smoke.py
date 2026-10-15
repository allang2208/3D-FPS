"""Build M66's descending variant using the unchanged Slag black-smoke material."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/BackSmokeV12')
sys.path[:0]=['D:/FPS3D/FPSGAME/Tools/Skills']
from build_fireball_assets import API,ref,emitters,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
DEST='/Game/Monsters/IncineratorBossM66/BackSmokeV12';E=u.EditorAssetLibrary
HL='/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
ENUM='/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum';VEC4='/Script/CoreUObject.Vector4f'
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before authoring the M66 smoke asset')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 smoke asset has unsaved changes')
path=DEST+'/NS_M66DescendingSoot'
system=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset('NS_M66DescendingSoot',DEST,u.NiagaraSystem,u.NiagaraSystemFactoryNew())
material=u.load_asset('/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/M_SlagPersistentBodySmoke')
if not system or not material:raise RuntimeError('M66 system or existing Slag smoke material missing')
emitter='M66DescendingSoot'
for old in emitters(system):
    for script in ('EmitterSpawnScript','EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript'):
        E.remove_metadata_tag(system,'Fireball.Assignments.'+old+'.'+script)
    API.call_method('RemoveEmitter',(ref(system,old),))
API.call_method('AddEmitter',(system,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),emitter))
trim(system,emitter,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
API.call_method('AddModule',(ref(system,emitter,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
variables=str(API.call_method('GetUserVariables',(system,)).export_text())
parameters=[('Radius',FLOAT),('DiffusionSpeed',FLOAT),('SmokeLifetime',FLOAT),('SmokeHoldTime',FLOAT),('EmissionRate',FLOAT),('EmitDrift',VEC3)]
for i in range(4):parameters.extend([('EmitOrigin%d'%i,POSITION),('EmitFloor%d'%i,FLOAT)])
for name,typ in parameters:
    if 'User.'+name not in variables:user_parameter(system,name,typ)
setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,emitter),{'bLocalSpace':False,'SimTarget':'CPUSim','InterpolatedSpawnMode':'RunUpdateScript','CalculateBoundsMode':'Dynamic'})
source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
mode=str(u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState','Life Cycle Mode')).replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
loop=str(u.RainAssetEditor.read_input(source,'Explosion','EmitterUpdateScript','EmitterState','Loop Behavior')).replace('NewEnumerator1','NewEnumerator0').replace('"Once"','"Infinite"')
put(system,emitter,'EmitterUpdateScript','EmitterState','Life Cycle Mode',mode,ENUM)
put(system,emitter,'EmitterUpdateScript','EmitterState','Loop Behavior',loop,ENUM)
put(system,emitter,'EmitterUpdateScript','SpawnRate','SpawnRate','(HlslExpression="max(0,User.EmissionRate)")',HL)
setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,emitter,renderer=0),{
    'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
    'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'PivotInUVSpace':{'X':.5,'Y':.5},
    'Alignment':'Unaligned','FacingMode':'FaceCamera','bCastShadows':False,'CutoutTexture':None,
    'bUseMaterialCutoutTexture':False,'bEnableCameraDistanceCulling':True,'MinCameraDistance':0,'MaxCameraDistance':3000})
seed='frac(float(Particles.UniqueID)*.61803398875+.137)'
var='frac(float(Particles.UniqueID)*.41421356237+.273)'
other='frac(float(Particles.UniqueID)*.75487766623+.413)'
def select(prefix):return f'({seed}<.25?User.{prefix}0:({seed}<.5?User.{prefix}1:({seed}<.75?User.{prefix}2:User.{prefix}3)))'
assignments(system,emitter,'ParticleSpawnScript',{
    'Particles.MistBirthPosition':(POSITION,select('EmitOrigin')),
    'Particles.MistBirthDrift':(VEC3,'User.EmitDrift'),
    'Particles.MistBirthFloor':(FLOAT,select('EmitFloor'))})
tag='Fireball.Assignments.'+emitter+'.ParticleSpawnScript'
E.set_metadata_tag(system,'M66.BirthCaptureModule',E.get_metadata_tag(system,tag));E.remove_metadata_tag(system,tag)
a='max(0,Particles.Age)';n=f'saturate({a}*User.DiffusionSpeed/max(.1,User.SmokeLifetime))'
travel=f'(2.2*(1-exp(-{a}/2.2)))'
sink=f'(38*({a}-.5*(1-exp(-{a}*2))))'
centre=f'(Particles.MistBirthPosition+Particles.MistBirthDrift*{travel})'
height=f'max(Particles.MistBirthFloor+55,Particles.MistBirthPosition.z-{sink})'
angle=f'({other}*6.2831853)'
spread=f'float3(cos({angle}),sin({angle}),({var}-.5)*.18)*User.Radius*(.015+.10*sqrt({n}))*(.6+.4*{var})'
roll=f'float3(sin({a}*.48+{other}*6.283),cos({a}*.43+{seed}*6.283),sin({a}*.35+{var}*6.283)*.25)*User.Radius*.025*saturate({a}*.6)'
fade=f'saturate((User.SmokeLifetime-{a})/max(.01,User.SmokeLifetime-User.SmokeHoldTime))'
common={
    'Particles.Position':(POSITION,f'float3({centre}.xy,{height})+{spread}+{roll}'),
    'Particles.SpriteSize':(VEC2,f'User.Radius*(.12+.68*sqrt({n}))*(.94+.12*{other})*float2(1,1.12)'),
    'Particles.Color':(COLOR,f'float4(.030,.026,.028,.65*saturate({a}/.35)*({fade}*{fade}*(3-2*{fade})))'),
    'Particles.SpriteRotation':(FLOAT,f'{other}*6.2831853+{a}*({var}-.5)*.22'),
    'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
    'Particles.DynamicMaterialParameter':(VEC4,f'float4({seed},0,0,0)')}
assignments(system,emitter,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'User.SmokeLifetime'),**common})
assignments(system,emitter,'ParticleUpdateScript',common)
system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-4000,-4000,-1200),max=u.Vector(4000,4000,1200)))
E.set_metadata_tag(system,'M66.BackSmoke','V12: four animated vent rims; detached world puffs; bounded rear drift and ground-limited sinking')
if not u.RainAssetEditor.compile_rain(system):raise RuntimeError('M66 descending smoke Niagara compile failed')
if not E.save_loaded_asset(system,False):raise RuntimeError('M66 descending smoke save failed')
report={'complete':True,'saved':[system.get_path_name()],'reused_material':material.get_path_name(),
    'ports':4,'particle_rate':12,'hold_seconds':8,'fade_seconds':1.5,'maximum_particles':114,
    'world_space':True,'birth_position_drift_and_floor_captured':True,'sink_speed_cm_s':38,
    'floor_clearance_cm':55,'diffusion_speed':1.7,'radius_multiplier':1.5,
    'runtime_tested':False,'rendered':False}
(ROOT/'Records/niagara_install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_BACK_SMOKE_SAVED '+json.dumps(report))
