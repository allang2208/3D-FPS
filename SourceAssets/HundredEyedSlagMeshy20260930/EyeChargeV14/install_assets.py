"""Save owned eye charge copies. Reuse MayuOrbs shading and the installed ThunderCharge stack.

No source package is modified, no game/preview/render is started.
"""
import json,sys
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT.resolve():raise RuntimeError('Wrong project')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters,setdata,put,assignments
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import expression
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools()
DEST='/Game/Monsters/HundredEyedSlag/EyeChargeV14';REV='EyeChargeV14';CREATED=[]
if u.EditorLevelLibrary.get_game_world() is not None:raise RuntimeError('End related PIE before saving charge assets')
DIRTY={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

def own(name,source=None,kind=None,factory=None):
 path=DEST+'/'+name
 if path in DIRTY:raise RuntimeError('Unsaved target preserved: '+path)
 if E.does_asset_exist(path):
  a=u.load_asset(path)
  if E.get_metadata_tag(a,'HundredEyedSlag.Revision')!=REV:raise RuntimeError('Unowned destination preserved: '+path)
 else:
  a=E.duplicate_asset(source,path) if source else T.create_asset(name,DEST,kind,factory)
 if not a:raise RuntimeError('Missing source/destination '+str(source or path))
 E.set_metadata_tag(a,'HundredEyedSlag.Revision',REV)
 if source:E.set_metadata_tag(a,'HundredEyedSlag.Source',source)
 return a

def save(a):
 if isinstance(a,u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(a):raise RuntimeError('Niagara authoring compile failed')
 if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed: '+a.get_path_name())
 CREATED.append(a.get_path_name());print('SLAG_V14_SAVED '+a.get_path_name(),flush=True)

def node(m,kind,tag):
 for x in L.get_material_expressions(m):
  if x.get_editor_property('desc')==tag:return x
 x=L.create_material_expression(m,kind);x.set_editor_property('desc',tag);return x

def param(m,kind,name,value):
 x=node(m,kind,'SlagV14.'+name);x.set_editor_property('parameter_name',name);x.set_editor_property('default_value',value);return x

def exposure(m,source):
 x=node(m,u.MaterialExpressionEyeAdaptationInverse,'SlagV14.Exposure')
 pin=str(L.get_material_expression_input_names(x)[0])
 L.connect_material_expressions(source,'',x,pin);L.connect_material_property(x,'',u.MaterialProperty.MP_EMISSIVE_COLOR)

def compile_material(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compilation failed: '+str(errors))
 save(m)

def core():
 source='/Game/MayuOrbs/02_Orbs/Orb_1/Materials/M_Orb_1'
 m=own('M_EyeOrbCore',source)
 m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
 m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 m.set_editor_property('two_sided',False);m.set_editor_property('disable_depth_test',False)
 original=E.get_metadata_tag(m,'HundredEyedSlag.OriginalEmissive')
 if original:
  output=next(x for x in L.get_material_expressions(m) if x.get_name()==original)
 else:
  output=L.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
  if not output:raise RuntimeError('MayuOrbs emissive source missing')
  E.set_metadata_tag(m,'HundredEyedSlag.OriginalEmissive',output.get_name())
 strength=param(m,u.MaterialExpressionScalarParameter,'ChargeStrength',0.)
 gain=node(m,u.MaterialExpressionMultiply,'SlagV14.CoreGain')
 L.connect_material_expressions(output,'',gain,'A');L.connect_material_expressions(strength,'',gain,'B')
 exposure(m,gain)
 opacity=param(m,u.MaterialExpressionScalarParameter,'CoreOpacity',.55)
 L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
 compile_material(m)
 mi=own('MI_EyeOrbRed','/Game/MayuOrbs/02_Orbs/Orb_1/Materials/MI_Orb_1_red')
 L.set_material_instance_parent(mi,m)
 for key,value in [('Color 1',u.LinearColor(.20,.001,.0001,1)),('Color 2',u.LinearColor(1,.006,.001,1))]:L.set_material_instance_vector_parameter_value(mi,key,value)
 for key,value in [('Fresnel Intensity',4.),('Freshnel Power',1.7),('Inner Intensity',.24),('Final Intensity',2.8),('Center Glow Intensity',.6),('ChargeStrength',0.),('CoreOpacity',.55)]:L.set_material_instance_scalar_parameter_value(mi,key,value)
 L.update_material_instance(mi);save(mi)

def custom(m,code,inputs):
 x=L.create_material_expression(m,u.MaterialExpressionCustom);x.set_editor_property('code',code);x.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
 entries=[]
 for name in inputs:
  item=u.CustomInput();item.set_editor_property('input_name',name);entries.append(item)
 x.set_editor_property('inputs',entries)
 for name,(src,pin) in inputs.items():L.connect_material_expressions(src,pin,x,name)
 return x

def shape(name,ring=False,vortex=False):
 m=own(name,kind=u.Material,factory=u.MaterialFactoryNew());L.delete_all_material_expressions(m)
 m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 m.set_editor_property('two_sided',True);m.set_editor_property('disable_depth_test',False)
 uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
 if vortex:
  tex=L.create_material_expression(m,u.MaterialExpressionTextureObject)
  tex.set_editor_property('texture',u.load_asset('/Game/MayuOrbs/04_Textures/T_Swirl_12_-_512x512'))
  time=L.create_material_expression(m,u.MaterialExpressionTime)
  strength=param(m,u.MaterialExpressionScalarParameter,'ChargeStrength',0.)
  code='float2 p=UV-.5;float r=length(p);float a=atan2(p.y,p.x)-Time*.8-r*6;float2 v=float2(cos(a),sin(a))*r+.5;float n=Texture2DSample(Tex,TexSampler,v).r;float rim=exp(-abs(r-(.38-.10*Strength))*55);return saturate(pow(saturate(n),1.8)*.7+rim*.5)*smoothstep(.5,.38,r)*(1-exp(-r*r*200));'
  mask=custom(m,code,{'UV':(uv,''),'Tex':(tex,''),'Time':(time,''),'Strength':(strength,'')})
  color=param(m,u.MaterialExpressionVectorParameter,'Tint',u.LinearColor(1,.006,.001,1))
  alpha=strength;alpha_pin=''
  intensity=param(m,u.MaterialExpressionScalarParameter,'Intensity',9.)
 else:
  code=('float r=length((UV-.5)*2);return exp(-abs(r-.78)*95)*smoothstep(1,.9,r);' if ring else
        'float x=.5+.04*sin(UV.y*19)+.015*sin(UV.y*47);return exp(-abs(UV.x-x)*75)*saturate(UV.y*9)*saturate((1-UV.y)*9);')
  mask=custom(m,code,{'UV':(uv,'')})
  color=L.create_material_expression(m,u.MaterialExpressionParticleColor);alpha=color;alpha_pin='A'
  intensity=L.create_material_expression(m,u.MaterialExpressionConstant);intensity.set_editor_property('r',12. if ring else 16.)
  L.set_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
 light=L.create_material_expression(m,u.MaterialExpressionMultiply)
 L.connect_material_expressions(color,'RGB' if not vortex else '',light,'A');L.connect_material_expressions(intensity,'',light,'B')
 exposure(m,light)
 opacity=L.create_material_expression(m,u.MaterialExpressionMultiply)
 L.connect_material_expressions(mask,'',opacity,'A');L.connect_material_expressions(alpha,alpha_pin,opacity,'B')
 fade=L.create_material_expression(m,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',1.)
 L.connect_material_expressions(opacity,'',fade,'Opacity');L.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
 compile_material(m);return m

def charge(inflow,ring):
 system=own('NS_EyeConvergence','/Game/Skills/ElectricMagic/NS_ThunderCharge')
 if 'EnergyCore' in emitters(system):API.call_method('RemoveEmitter',(ref(system,'EnergyCore'),))
 seed='frac(float(Particles.UniqueID)*.618033989)'
 t='saturate(Particles.NormalizedAge)'
 theta=f'({seed}*6.2831853+Particles.Age*(5+User.Charge*4))'
 for name,rate,life,start_radius,length,width,mat in [
  ('GatheringSparks',96,.36,40,8,1.6,inflow),('ChargingFilaments',24,.24,29,19,1.8,inflow),('GatheringRings',3,.58,0,0,0,ring)]:
  trim(system,name,{'EmitterUpdateScript':['EmitterState','SpawnRate'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
  for stage in ('ParticleSpawnScript','ParticleUpdateScript'):E.remove_metadata_tag(system,'Fireball.Assignments.'+name+'.'+stage)
  setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,name),{'bLocalSpace':True,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
  setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
   'Material':mat.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'Alignment':'Unaligned' if name=='GatheringRings' else 'VelocityAligned',
   'FacingMode':'CustomFacingVector' if name=='GatheringRings' else 'FaceCamera','SortMode':'ViewDepth','bCastShadows':False,'MotionVectorSetting':'Disable','CutoutTexture':None,'bUseMaterialCutoutTexture':False})
  expression(system,name,'EmitterUpdateScript','SpawnRate','SpawnRate',f'{rate}*(.25+.75*saturate(User.Charge))')
  r=f'(4+({start_radius}-4)*pow(1-{t},1.35))'
  position='float3(3,0,0)' if name=='GatheringRings' else f'float3(2+8*(1-{t}),cos({theta})*{r},sin({theta})*{r})'
  velocity=f'float3(-8,-cos({theta})-.5*sin({theta}),-sin({theta})+.5*cos({theta}))*100'
  size=f'float2(64,64)*(1-{t}*.68)' if name=='GatheringRings' else f'float2({width},{length})*(.75+User.Charge*.5)'
  color=f'float4(1,.008,.001,(.25+.75*saturate(User.Charge))*saturate({t}*12)*saturate((1-{t})*5))'
  # Same analytic spiral evaluated at birth and each update. No force solver, trail history or collision.
  values={'Particles.Lifetime':(FLOAT,str(life)),'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,velocity),'Particles.SpriteSize':(VEC2,size),'Particles.Color':(COLOR,color),'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SpriteFacing':(VEC3,'float3(1,0,0)'),'Particles.SubImageIndex':(FLOAT,'0')}
  assignments(system,name,'ParticleSpawnScript',values)
  assignments(system,name,'ParticleUpdateScript',{k:v for k,v in values.items() if k!='Particles.Lifetime'})
 system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-16,-55,-55),max=u.Vector(24,55,55)))
 E.set_metadata_tag(system,'HundredEyedSlag.Motion','Inward spiral from radius 40/29 cm to 4 cm; local eye coordinates; Charge controls intensity; max about 44 live sprites per eye')
 save(system)

core();inflow=shape('M_EyeInflow');ring=shape('M_EyeChargeRing');shape('M_EyeVortex',vortex=True);charge(inflow,ring)
receipt={'revision':REV,'assets_saved':CREATED,'source_packages_modified':False,
 'reuse_sources':['/Game/MayuOrbs/02_Orbs/Orb_1/Materials/M_Orb_1','/Game/MayuOrbs/02_Orbs/Orb_1/Materials/MI_Orb_1_red','/Game/MayuOrbs/04_Textures/T_Swirl_12_-_512x512','/Game/Skills/ElectricMagic/NS_ThunderCharge'],
 'runtime_tested':False,'preview_rendered':False,'editor_started':False}
(OUT/'ready_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('SLAG_V14_CHARGE_ASSETS_SAVED',flush=True)
