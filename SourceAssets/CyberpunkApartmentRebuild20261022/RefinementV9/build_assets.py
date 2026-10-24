from pathlib import Path
import unreal as u,json,runpy,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',materials={},meshes={},game_run=False)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing AP9 dependency '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('AP9 save failed '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin):
 names=list(L.get_material_expression_input_names(b))
 normalize=lambda s:str(s).replace(' ','').replace('_','').lower()
 actual=next((str(n) for n in names if normalize(n)==normalize(pin)),pin)
 if not pin and names:actual=str(names[0])
 if not L.connect_material_expressions(a,'',b,actual):raise RuntimeError('AP9 material input '+pin+'; available '+str(names))
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));pins=[]
 for k in inputs:p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
 n.set_editor_property('inputs',pins)
 for k,v in inputs.items():wire(v,n,k)
 return n
def param(m,k,v):return node(m,'ScalarParameter',parameter_name=k,default_value=v)
def scalar(m,v):return node(m,'Constant',r=v)
def rgb(m,r,g,b):return node(m,'Constant3Vector',constant=u.LinearColor(r,g,b,1))
def begin(key):
 path=BASE+'/Materials/M_AP9_'+key;m=load(path) if E.does_asset_exist(path) else A.create_asset('M_AP9_'+key,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 return m
ROT='''float a=radians(Tilt+TiltSweep*sin(T*6.2831853/max(Period,1)+Phase));
float b=radians(Yaw+YawSweep*sin(T*6.2831853/(max(Period,1)*1.31)+Phase*.73));
float3 q=float3(cos(a)*V.x+sin(a)*V.z,V.y,-sin(a)*V.x+cos(a)*V.z);
return float3(cos(b)*q.x-sin(b)*q.y,sin(b)*q.x+cos(b)*q.y,q.z);'''
def movement(m):
 clock=node(m,'Time');p=node(m,'WorldPosition');origin=node(m,'ActorPositionWS');relative=custom(m,'return P-O;',{'P':p,'O':origin})
 inputs={'T':clock}
 for k,v in dict(Tilt=0,TiltSweep=0,Yaw=0,YawSweep=0,Period=32,Phase=0).items():inputs[k]=param(m,k,v)
 rot=custom(m,ROT,dict(V=relative,**inputs));offset=custom(m,'return R-V;',{'R':rot,'V':relative});L.connect_material_property(offset,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 return inputs
def night(m):
 sun=node(m,'SkyAtmosphereLightDirection',light_index=0)
 return custom(m,'return 1-smoothstep(-.08,.12,Sun.z);',{'Sun':sun},1)
def texture(m,path,kind):
 return node(m,'TextureSample',texture=load(path),sampler_type=kind)
def finish(key,m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 save(m);report['materials'][key]=m.get_path_name();record()
def materials():
 m=begin('MovingMetal');rot=movement(m);m.set_editor_property('tangent_space_normal',False)
 root='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Textures/T_AP7_Machined_'
 color=texture(m,root+'BC',u.MaterialSamplerType.SAMPLERTYPE_COLOR);packed=texture(m,root+'ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS);normal=texture(m,root+'N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 transform=node(m,'Transform');wire(normal,transform,'');world_normal=custom(m,ROT,dict(V=transform,**rot))
 slab=node(m,'SubstrateShadingModels')
 for n,pin,prop in [(color,'BaseColor','BASE_COLOR'),(world_normal,'Normal','NORMAL'),(custom(m,'return P.g;',{'P':packed},1),'Roughness','ROUGHNESS'),(custom(m,'return P.b;',{'P':packed},1),'Metallic','METALLIC')]:wire(n,slab,pin);L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop))
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);finish('MovingMetal',m)
 for key in ['Lens','Beam']:
  m=begin(key);rot=movement(m);n=night(m);tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.1,.5,1,1));gain=param(m,'Gain',3.5 if key=='Lens' else .36)
  if key=='Beam':
   m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);m.set_editor_property('two_sided',False)
   uv=node(m,'TextureCoordinate');vn=node(m,'VertexNormalWS');norm=custom(m,ROT,dict(V=vn,**rot));view=node(m,'CameraVectorWS');fade=node(m,'DepthFade',fade_distance_default=500.,opacity_default=1.)
   mask=custom(m,'''float edge=pow(saturate(abs(dot(normalize(N),normalize(View)))),1.4);
float lengthFade=smoothstep(0,.018,UV.y)*pow(saturate(1-UV.y),1.1)*(1-smoothstep(.72,1,UV.y));
float mist=.94+.06*sin(T*.17+UV.y*7);
return edge*lengthFade*mist*Fade*Night;''',{'N':norm,'View':view,'UV':uv,'T':rot['T'],'Fade':fade,'Night':n},1)
   emission=custom(m,'return Tint.rgb*Gain*Mask;',{'Tint':tint,'Gain':gain,'Mask':mask})
   bsdf=node(m,'SubstrateUnlitBSDF');wire(emission,bsdf,'EmissiveColor');wire(rgb(m,1,1,1),bsdf,'TransmittanceColor');L.connect_material_property(bsdf,'',u.MaterialProperty.MP_FRONT_MATERIAL)
   L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY)
  else:
   emission=custom(m,'return Tint.rgb*Gain*Night;',{'Tint':tint,'Gain':gain,'Night':n});slab=node(m,'SubstrateShadingModels')
   m.set_editor_property('tangent_space_normal',False);lens_normal=custom(m,ROT,dict(V=node(m,'VertexNormalWS'),**rot));wire(lens_normal,slab,'Normal');L.connect_material_property(lens_normal,'',u.MaterialProperty.MP_NORMAL)
   for value,pin,prop in [(rgb(m,.015,.025,.035),'BaseColor','BASE_COLOR'),(scalar(m,.21),'Roughness','ROUGHNESS'),(scalar(m,.18),'Metallic','METALLIC'),(emission,'Emissive Color','EMISSIVE_COLOR')]:wire(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
   L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
  finish(key,m)
 def instance(name,parent,values,color=None):
  path=BASE+'/Materials/MI_AP9_'+name;mi=load(path) if E.does_asset_exist(path) else A.create_asset('MI_AP9_'+name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.set_material_instance_parent(mi,load(report['materials'][parent]))
  for k,v in values.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
  if color:L.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*color,1))
  L.update_material_instance(mi);save(mi);report['materials'][name]=mi.get_path_name()
 for b in C['SEARCH']:
  values=dict(Tilt=b['tilt'],TiltSweep=b['tilt_sweep'],Yaw=b['yaw'],YawSweep=b['yaw_sweep'],Period=b['period'],Phase=b['phase'])
  instance(b['key']+'_Head','MovingMetal',values)
  instance(b['key']+'_Yoke','MovingMetal',dict(values,Tilt=0,TiltSweep=0))
  instance(b['key']+'_Lens','Lens',values,b['color']);instance(b['key']+'_Beam','Beam',values,b['color'])
 for b in C['FIXED']:instance(b['key']+'_Lens','Lens',dict(Tilt=0,TiltSweep=0,Yaw=0,YawSweep=0),b['color'])
 record()
def main():
 try:
  materials();old='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Materials/M_AP7_Machined'
  roles={'StaticMetal':old,'Yoke':old,'HeadMetal':old,'Lens':report['materials']['Lens'],'Beam':report['materials']['Beam']}
  for row in json.loads((R/'assembly.json').read_text()):
   t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
   opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
   data=opt.static_mesh_import_data
   for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():data.set_editor_property(k,v)
   data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
   for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(roles[str(s.material_slot_name)]))
   settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
   if row['key']=='Beam':
    mesh.set_editor_property('positive_bounds_extension',u.Vector(35000,35000,12000));mesh.set_editor_property('negative_bounds_extension',u.Vector(35000,35000,12000))
   save(mesh);report['meshes'][row['key']]=mesh.get_path_name();record()
  report['stage']='assets_saved';record()
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
