from pathlib import Path
import unreal as u,json,runpy,traceback,hashlib
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',textures=[],materials={},meshes={},game_run=False)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing AP8 resource '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('AP8 material pin '+pin)
def param(m,k,v):return node(m,'ScalarParameter',parameter_name=k,default_value=v)
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
 pins=[]
 for k in inputs:p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
 n.set_editor_property('inputs',pins)
 for k,v in inputs.items():wire(v,n,k)
 return n
def texture(m,name,uv):
 n=node(m,'TextureSample',texture=load(BASE+'/Textures/'+name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(uv,n,'UVs');return n
def begin(name):
 path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 m.set_editor_property('used_with_instanced_static_meshes',True)
 return m
def finish(m,emission):
 # Opaque display surface: bounded emission and existing Substrate renderer.
 slab=node(m,'SubstrateShadingModels');zero=node(m,'Constant',r=0.);rough=node(m,'Constant',r=.43)
 normal=node(m,'Constant3Vector',constant=u.LinearColor(0,0,1,1))
 for a,pin,prop in [(zero,'BaseColor','BASE_COLOR'),(zero,'Metallic','METALLIC'),(rough,'Roughness','ROUGHNESS'),(normal,'Normal','NORMAL'),(emission,'Emissive Color','EMISSIVE_COLOR')]:
  wire(a,slab,pin);L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+prop))
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 save(m);report['materials'][m.get_name()]=m.get_path_name()
def materials():
 for kind in ['Portrait','Ribbon']:
  m=begin('M_AP8_'+kind);uv=node(m,'TextureCoordinate');clock=node(m,'Time');phase=param(m,'Phase',0.);slot=param(m,'Campaign',0.);aspect=param(m,'Aspect',2/3);rate=param(m,'PlaybackRate',1.)
  t=custom(m,'return (Clock+Phase)*Rate;',{'Clock':clock,'Phase':phase,'Rate':rate},1)
  sun=node(m,'SkyAtmosphereLightDirection',light_index=0)
  brightness=custom(m,'return lerp(.55,2.6,1-smoothstep(-.08,.12,Sun.z));',{'Sun':sun},1)
  if kind=='Portrait':
   coords=[]
   for advance in [0,1]:
    code='float k=fmod(floor(T/12)+Slot+'+str(advance)+',4);float f=frac(T/12);float zoom=1.0+.035*sin(f*3.14159265);float2 q=(UV-.5)/zoom+.5; q+=float2(.003*sin(T*.31),.003*cos(T*.27));q=clamp(q,.018,.982);return (q+float2(fmod(k,2),floor(k/2)))*.5;'
    coords.append(custom(m,code,{'UV':uv,'T':t,'Slot':slot},2))
   ca=texture(m,'T_AP8_CampaignAtlas_BC',coords[0]);cb=texture(m,'T_AP8_CampaignAtlas_BC',coords[1])
   mix=custom(m,'return smoothstep(.88,.98,frac(T/12)+(UV.x-.5)*.10);',{'UV':uv,'T':t},1)
   e=custom(m,'''float3 c=lerp(A,B,W);
float2 q=(UV-.5)*float2(.6667,1);float r=length(q);float ang=atan2(q.y,q.x);
float f=frac(T/12);float k=fmod(floor(T/12)+Slot,4);
float3 accent=k<.5?float3(.15,.65,1):k<1.5?float3(1,.38,.055):k<2.5?float3(.35,.22,1):float3(1,.06,.5);
float scan=exp(-pow((UV.y-frac(T*.09))/.055,2));
float ring=exp(-pow((r-(.22+.035*sin(ang*2-T*.7)))/.009,2));
float orbit=.5+.5*sin(ang*3-T*1.2);
float bars=smoothstep(.84,.90,UV.y)*(1-smoothstep(.92,.97,UV.y))*step(UV.y,.87+.06*sin(floor(UV.x*18)*1.7+T*2));
float fx=k<.5?scan*.07:k<1.5?ring*orbit*.085:k<2.5?scan*.045:bars*.085;
// Wide, faint signal dropout once per cycle; no rapid full-screen flicker.
float dropout=smoothstep(.70,.73,f)*(1-smoothstep(.74,.77,f))*exp(-pow((UV.y-.61)/.06,2));
return min((c*(1-dropout*.06)+accent*fx)*Brightness,3.0);''',{'A':ca,'B':cb,'W':mix,'UV':uv,'T':t,'Slot':slot,'Brightness':brightness})
  else:
   # U is continuous/repeating; derivative is evaluated by the sampler, not a frac wrap.
   q=custom(m,'return float2(UV.x*Aspect/16+T*.028, (clamp(UV.y,.035,.965)+Slot)*.25);',{'UV':uv,'T':t,'Aspect':aspect,'Slot':slot},2)
   c=texture(m,'T_AP8_Ticker_BC',q)
   e=custom(m,'float edge=smoothstep(0,.035,UV.x)*(1-smoothstep(.965,1,UV.x));return C*Brightness*edge;',{'C':c,'UV':uv,'Brightness':brightness})
  finish(m,e)
 for b in C['BOARDS']:
  name='MI_AP8_'+b['key'];path=BASE+'/Materials/'+name
  mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.set_material_instance_parent(mi,load(BASE+'/Materials/M_AP8_'+('Portrait' if b['kind']=='portrait' else 'Ribbon')))
  for k,v in dict(Phase=b['phase'],Campaign=b['slot'],Aspect=b['w']/b['h'],PlaybackRate=.92 if b['key']=='Port' else 1.).items():L.set_material_instance_scalar_parameter_value(mi,k,v)
  L.update_material_instance(mi);save(mi);report['materials'][name]=mi.get_path_name()
def main():
 try:
  for file in sorted((R/'Textures').glob('*.png')):
   t=u.AssetImportTask();t.filename=str(file);t.destination_path=BASE+'/Textures';t.destination_name=file.stem;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);asset=load(BASE+'/Textures/'+file.stem)
   for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,never_stream=False,power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO).items():asset.set_editor_property(k,v)
   asset.set_editor_property('address_x',u.TextureAddress.TA_WRAP if 'Ticker' in file.stem else u.TextureAddress.TA_CLAMP);asset.set_editor_property('address_y',u.TextureAddress.TA_CLAMP);save(asset);report['textures'].append(asset.get_path_name())
  materials();record()
  old='/Game/Props/CyberpunkApartmentRebuild20261022/'
  roles=dict(MountMetal=old+'RefinementV7/Materials/M_AP7_Machined',CyanTrim=old+'RefinementV6/Materials/M_AP6_Neon0',AmberTrim=old+'RefinementV6/Materials/M_AP6_Neon2',Display=BASE+'/Materials/M_AP8_Portrait')
  for row in json.loads((R/'assembly.json').read_text())['meshes']:
   t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
   opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
   data=opt.static_mesh_import_data
   for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():data.set_editor_property(k,v)
   data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
   for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(roles[str(s.material_slot_name)]))
   settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
   if row['name']=='SM_AP8_MountedFrames':
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True;settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;settings.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',settings)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('AP8 structure Nanite build failed')
   save(mesh);report['meshes'][row['name']]=mesh.get_path_name();record()
  report['stage']='assets_saved';record()
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
