"""Adapt Slag's inward particle stack for M09; save only independent V10 assets."""
import json,sys
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/HangingBellM09Meshy20261003'/globals().get('M09_CHARGE_OUTPUT','GazeChargeV10')
DEST='/Game/Monsters/HangingBellM09/V10'
SOURCE='/Game/Monsters/HundredEyedSlag/EyeChargeV14/NS_EyeConvergence'
(OUT/'Records').mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters,setdata,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import expression
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools()
if not globals().get('M09_COMMANDLET',False):
 if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End related PIE before saving charge assets')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
saved=[]
def own(name,source=None):
 path=DEST+'/'+name
 if path in dirty:raise RuntimeError('Preserve unsaved V10 target '+path)
 if E.does_asset_exist(path):
  a=u.load_asset(path)
  if E.get_metadata_tag(a,'M09Production')!='GazeChargeV10':raise RuntimeError('Preserve unowned target '+path)
 else:a=E.duplicate_asset(source,path) if source else T.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 if not a:raise RuntimeError('Asset authoring failed '+path)
 E.set_metadata_tag(a,'M09Production','GazeChargeV10')
 return a
def save(a):
 if isinstance(a,u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(a):raise RuntimeError('Niagara compile failed '+a.get_path_name())
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 saved.append(a.get_path_name());print('M09_V10_SAVED '+a.get_path_name(),flush=True)
 (OUT/'Records/import_saved.json').write_text(json.dumps({'complete':False,'saved':saved,'tested':False},indent=2),encoding='utf8')
def material(name,streak):
 m=own(name)
 if globals().get('M09_UPDATE_EXISTING',False):
  # Parameter-only revisions retain the existing graph. In a commandlet, the
  # material expressions loaded by the native CDO may be rooted by Python;
  # deleting/rebuilding them is both unnecessary and rejected by the engine.
  gains=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionConstant)]
  if len(gains)!=1:raise RuntimeError('Missing existing M09 particle gain node')
  gains[0].set_editor_property('r',8.4 if streak else 10.5)
  errors=L.recompile_material(m)
  if errors:raise RuntimeError('Material compilation failed '+str(errors))
  save(m);return m
 for old in list(L.get_material_expressions(m)):L.delete_material_expression(m,old)
 m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
 m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 m.set_editor_property('two_sided',True);m.set_editor_property('disable_depth_test',False)
 L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True)
 def node(cls,**props):
  n=L.create_material_expression(m,cls)
  for k,v in props.items():n.set_editor_property(k,v)
  return n
 def wire(a,b,pin,out=''):
  if isinstance(pin,int):pin=str(L.get_material_expression_input_names(b)[pin])
  if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed '+str(pin))
 uv=node(u.MaterialExpressionTextureCoordinate)
 code=('float2 p=UV*2-1;return exp(-p.x*p.x*10)*pow(saturate(1-abs(p.y)),1.5)*smoothstep(1.,.7,abs(p.x));' if streak else
       'float r=length(UV*2-1);return exp(-r*r*5.5)*(1-smoothstep(.55,1.,r));')
 mask=node(u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
 pin=u.CustomInput();pin.set_editor_property('input_name','UV');mask.set_editor_property('inputs',[pin]);wire(uv,mask,'UV')
 color=node(u.MaterialExpressionParticleColor)
 gain=node(u.MaterialExpressionConstant,r=8.4 if streak else 10.5)
 light=node(u.MaterialExpressionMultiply);wire(color,light,'A','RGB');wire(gain,light,'B')
 exposure=node(u.MaterialExpressionEyeAdaptationInverse);wire(light,exposure,0)
 L.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
 alpha=node(u.MaterialExpressionMultiply);wire(mask,alpha,'A');wire(color,alpha,'B','A')
 fade=node(u.MaterialExpressionDepthFade,fade_distance_default=1.5);wire(alpha,fade,'Opacity')
 L.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compilation failed '+str(errors))
 save(m);return m
speck=material('M_M09_GatherSpeck_V10',False)
streak=material('M_M09_GatherStreak_V10',True)
system=own('NS_M09_EyeGather_V10',SOURCE)
keep=('GatheringSparks','ChargingFilaments','GatheringRings')
for name in emitters(system):
 if name not in keep:API.call_method('RemoveEmitter',(ref(system,name),))
recipes=[('GatheringSparks',88,.38,42,4.0,3.5,speck),
 ('ChargingFilaments',25,.24,34,15.,2.2,streak),
 ('GatheringRings',38,.30,27,2.2,2.2,speck)]
for name,rate,life,start_radius,length,width,mat in recipes:
 if not globals().get('M09_UPDATE_EXISTING',False):
  trim(system,name,{'EmitterUpdateScript':['EmitterState','SpawnRate'],
   'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
  for stage in ('ParticleSpawnScript','ParticleUpdateScript'):E.remove_metadata_tag(system,'Fireball.Assignments.'+name+'.'+stage)
 setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),
  {'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
 setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
  'Material':mat.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
  'Alignment':'VelocityAligned' if name=='ChargingFilaments' else 'Unaligned',
  'FacingMode':'FaceCamera','SortMode':'ViewDepth','bCastShadows':False,'MotionVectorSetting':'Disable',
  'CutoutTexture':None,'bUseMaterialCutoutTexture':False,'SubImageSize':{'X':1,'Y':1}})
 expression(system,name,'EmitterUpdateScript','SpawnRate','SpawnRate',f'{rate}*(.32+.68*saturate(User.Charge))')
 seed='frac(float(Particles.UniqueID)*.618033989)'
 age='saturate(Particles.NormalizedAge)'
 charge='saturate(User.Charge)'
 theta=f'({seed}*6.2831853+Particles.Age*(5+{charge}*5))'
 # Each particle accelerates inward. During final charge all trajectories
 # contract together, so the field visibly collapses into the eye before fire.
 collapse=f'(1-.96*pow(saturate(({charge}-.82)/.18),2))'
 radius=f'(.4+({start_radius}-.4)*(1-pow({age},1.65))*{collapse})'
 position=f'float3(1+10*(1-{age})*{collapse},cos({theta})*{radius},sin({theta})*{radius})'
 velocity=f'float3(-.2,-cos({theta})-.55*sin({theta}),-sin({theta})+.55*cos({theta}))*100'
 size=f'float2({width},{length})*(.7+.35*{charge})*(1-.35*{age})'
 alpha=f'(.40+.56*{charge})*saturate({age}*10)*saturate((1-{age})*7)'
 color=f'float4(.60+.15*{seed},.46+.18*{seed},.82+.10*{seed},{alpha})'
 values={'Particles.Lifetime':(FLOAT,str(life)),'Particles.Position':(POSITION,position),
  'Particles.Velocity':(VEC3,velocity),'Particles.SpriteSize':(VEC2,size),'Particles.Color':(COLOR,color),
  'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SubImageIndex':(FLOAT,'0')}
 assignments(system,name,'ParticleSpawnScript',values)
 assignments(system,name,'ParticleUpdateScript',{k:v for k,v in values.items() if k!='Particles.Lifetime'})
system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-12,-54,-54),max=u.Vector(22,54,54)))
E.set_metadata_tag(system,'M09SourceSystem',SOURCE)
E.set_metadata_tag(system,'M09Motion','Inward specks, curved short streaks and fine dust; collapse into iris before firing; no rings')
E.set_metadata_tag(system,'M09VisualRevision','GazeVisibilityV12')
save(system)
receipt={'complete':True,'saved':saved,'source':SOURCE,'source_packages_modified':False,
 'emitters':[{'name':x[0],'max_spawn_rate':x[1],'lifetime':x[2],'start_radius_cm':x[3]} for x in recipes],
 'max_live_estimate_per_eye':sum(x[1]*x[2] for x in recipes),'eyes':5,
 'provenance':'Derived from local Slag EyeChargeV14 / ElectricMagic Niagara stack; new M09 particle shapes, colors and trajectories',
 'tested':False,'preview_rendered':False}
(OUT/'Records/import_saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('M09_GAZE_CHARGE_V10_SAVED assets='+str(len(saved)))
