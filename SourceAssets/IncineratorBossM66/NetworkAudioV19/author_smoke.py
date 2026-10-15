import json,sys,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/NetworkAudioV19');DEST='/Game/Monsters/IncineratorBossM66/NetworkAudioV19'
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,ref,emitters,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();name='NS_M66HistorySoot';path=DEST+'/'+name
system=u.load_asset(path) if E.does_asset_exist(path) else A.duplicate_asset(name,DEST,u.load_asset('/Game/Monsters/IncineratorBossM66/BackSmokeV12/NS_M66DescendingSoot'))
en='M66HistorySoot'
for old in emitters(system):API.call_method('RemoveEmitter',(ref(system,old),))
for tag in ('ParticleSpawnScript','ParticleUpdateScript'):E.remove_metadata_tag(system,'Fireball.Assignments.'+en+'.'+tag)
API.call_method('AddEmitter',(system,u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),en))
trim(system,en,{'EmitterUpdateScript':['EmitterState'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
API.call_method('AddModule',(ref(system,en,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
put(system,en,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count','(Value=128)','/Script/Niagara.NiagaraInt32')
source=u.load_asset('/Game/Monsters/IncineratorBossM66/BackSmokeV12/NS_M66DescendingSoot')
for key in ('Life Cycle Mode','Loop Behavior'):
    value=u.RainAssetEditor.read_input(source,'M66DescendingSoot','EmitterUpdateScript','EmitterState',key)
    put(system,en,'EmitterUpdateScript','EmitterState',key,value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
put(system,en,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=100000)')
setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,en),{'bLocalSpace':False,'SimTarget':'CPUSim','CalculateBoundsMode':'Dynamic'})
variables=str(API.call_method('GetUserVariables',(system,)).export_text())
for n,t in [('HistoryOrigin',POSITION),('ClockOffset',FLOAT),('HistoryReady',FLOAT)]:
    if 'User.'+n not in variables:user_parameter(system,n,t)
DI='/Script/Niagara.NiagaraDataInterfaceArrayFloat4'
for n in ('PuffBirth','PuffMotion'):
    variable=u.NiagaraExt_UserVariable();variable.import_text('(Name="User.'+n+'",Type=(ClassStructOrEnum="'+DI+'",UnderlyingType=1))');API.call_method('AddUserVariables',(system,[variable]))
VEC4='/Script/CoreUObject.Vector4f';HL='/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
stage='ParticleUpdateScript'
assignments(system,en,stage,{'Particles.HistoryBirth':(VEC4,'float4(0,0,0,-10000)'),'Particles.HistoryMotion':(VEC4,'float4(0,0,0,0)')})
module=E.get_metadata_tag(system,'Fireball.Assignments.'+en+'.'+stage)
for field,param in [('Particles.HistoryBirth','PuffBirth'),('Particles.HistoryMotion','PuffMotion')]:
    put(system,en,stage,module,field,'(DynamicInputAsset="/Niagara/DynamicInputs/Arrays/SelectVector4_FromArray.SelectVector4_FromArray")','/Script/NiagaraEditor.NiagaraExt_StackInputData_DynamicInput')
    put(system,en,stage,module,field+'|Array Sampling Mode','(Enum="/Niagara/Enums/ENiagaraArraySamplingMode.ENiagaraArraySamplingMode",EnumName="ENiagaraArraySamplingMode::NewEnumerator1",DisplayName="Direct Set")','/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system,en,stage,module,field+'|Vector4 Selection Array','(LinkedVariable=(Name="User.'+param+'",Type=(ClassStructOrEnum="'+DI+'",UnderlyingType=1)))','/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked')
    put(system,en,stage,module,field+'|Direct Array Index','(HlslExpression="int(Particles.UniqueID)")',HL)
E.remove_metadata_tag(system,'Fireball.Assignments.'+en+'.'+stage)
birth='Particles.HistoryBirth';motion='Particles.HistoryMotion';age=f'max(0,Engine.Time+User.ClockOffset-{birth}.w)'
n=f'saturate({age}*User.DiffusionSpeed/max(.1,User.SmokeLifetime))'
seed=f'frac(({motion}.w+.137)*.61803398875)';other=f'frac(({motion}.w+.413)*.75487766623)';var=f'frac(({motion}.w+.273)*.41421356237)'
travel=f'(2.2*(1-exp(-{age}/2.2)))';sink=f'(38*({age}-.5*(1-exp(-{age}*2))))'
center=f'(User.HistoryOrigin+float3({birth}.xy+{motion}.xy*{travel},max({motion}.z+55,{birth}.z-{sink})))'
spread=f'float3(cos({other}*6.2831853),sin({other}*6.2831853),({var}-.5)*.18)*User.Radius*(.015+.10*sqrt({n}))*(.6+.4*{var})'
roll=f'float3(sin({age}*.48+{other}*6.283),cos({age}*.43+{seed}*6.283),sin({age}*.35+{var}*6.283)*.25)*User.Radius*.025*saturate({age}*.6)'
fade=f'saturate((User.SmokeLifetime-{age})/max(.01,User.SmokeLifetime-User.SmokeHoldTime))'
alpha=f'User.HistoryReady*.65*saturate({age}/.35)*({fade}*{fade}*(3-2*{fade}))'
assignments(system,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'100000'),'Particles.SpriteSize':(VEC2,'float2(0,0)'),'Particles.Color':(COLOR,'float4(0,0,0,0)')})
assignments(system,en,stage,{'Particles.Position':(POSITION,center+'+'+spread+'+'+roll),
 'Particles.SpriteSize':(VEC2,f'User.Radius*(.12+.68*sqrt({n}))*(.94+.12*{other})*float2(1,1.12)'),
 'Particles.Color':(COLOR,f'float4(.030,.026,.028,{alpha})'),
 'Particles.SpriteRotation':(FLOAT,f'{other}*6.2831853+{age}*({var}-.5)*.22'),
 'Particles.SpriteUVScale':(VEC2,'float2(1,1)'), 'Particles.DynamicMaterialParameter':(VEC4,f'float4({seed},0,0,0)')})
material=u.load_asset('/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/M_SlagPersistentBodySmoke')
setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,en,renderer=0),{'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'Alignment':'Unaligned','FacingMode':'FaceCamera','bCastShadows':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False,'bEnableCameraDistanceCulling':True,'MaxCameraDistance':4500})
if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('M66 history Niagara compile failed')
if not E.save_loaded_asset(system,False):raise RuntimeError('M66 history Niagara save failed')
(ROOT/'smoke_install.json').write_text(json.dumps({'saved':system.get_path_name(),'history_groups':32,'particles':128,'clock':'server world time','same_slag_material':True},indent=2))
print('M66_HISTORY_SMOKE_SAVED '+system.get_path_name())
