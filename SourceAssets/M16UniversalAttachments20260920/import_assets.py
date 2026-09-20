"""Author/save private M16 assets in the full editor through the batch mutex."""
import unreal as u,json,re,time
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M16A2/UniversalAttachments20260920'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before attachment import')
models=json.loads((O/'models.json').read_text());animations=json.loads((O/'animations.json').read_text())
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf-8')) if (O/'import_receipt.json').exists() else {'meshes':{},'materials':{},'animations':{},'testing':'Not run; production import/save only'}
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing asset '+path)
 return obj
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outer()],False):raise RuntimeError('Save failed '+obj.get_path_name())
def record(): (O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,n,pin):
 x,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(x,out,n,pin):raise RuntimeError('Material input '+pin)
def output(src,prop):
 x,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(x,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def current(m,prop,default):
 p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
 return (n,L.get_material_property_input_node_output_name(m,p)) if n else node(m,u.MaterialExpressionConstant,r=default)
def custom(m,code,inputs,size):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n
def imported(file,name,folder,options=None):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.options=options
 A.import_asset_tasks([task]);return load(folder+'/'+name)
textures={}
for key in ('BaseColor','Metallic','Roughness','Normal'):
 name='T_M16_Coat_'+key;t=imported(O/'Textures'/(name+'.png'),name,D+'/Textures');t.srgb=key=='BaseColor'
 t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
 if key=='Normal':t.flip_green_channel=True
 t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;save(t);textures[key]=t
def sample(m,key,uv):
 n=node(m,u.MaterialExpressionTextureSample,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);wire(uv,n,'UVs');return (n,'RGB' if key in ('BaseColor','Normal') else 'R')
materials={};wet={row['dry']:load(row['wet']) for row in receipt['materials'].values()}
BEADS=(O.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text()
def material(key,slot,path):
 if key=='ext_mag':return load(path)
 if path and any(s in (slot+' '+path).lower() for s in ('glass','lens','reticle','red_dot','rubber','interior','recess','titanium','polymer')) and key!='large_drum':return load(path)
 cachekey=(key,slot)
 if cachekey in materials:return materials[cachekey]
 name='M_M16_'+key+'_'+re.sub('[^A-Za-z0-9_]','_',slot)+'_Surface'
 existing=u.load_asset(D+'/Materials/'+name)
 existing_wet=u.load_asset(D+'/Materials/'+name+'_Wet')
 if existing and existing_wet:
  materials[cachekey]=existing;wet[existing.get_path_name()]=existing_wet;return existing
 if existing:
  E.rename_asset(existing.get_path_name(),D+'/AuthoringRecovery/'+name+'_Incomplete_'+str(int(time.time())))
 if path:
  source=load(path);m=A.duplicate_asset(name,D+'/Materials',source.get_base_material())
  if isinstance(source,u.MaterialInstanceConstant):
   for n in L.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionScalarParameter):n.set_editor_property('default_value',L.get_material_instance_scalar_parameter_value(source,n.get_editor_property('parameter_name')))
    elif isinstance(n,u.MaterialExpressionVectorParameter):n.set_editor_property('default_value',L.get_material_instance_vector_parameter_value(source,n.get_editor_property('parameter_name')))
    elif isinstance(n,u.MaterialExpressionTextureSampleParameter):n.set_editor_property('texture',L.get_material_instance_texture_parameter_value(source,n.get_editor_property('parameter_name')))
    elif isinstance(n,u.MaterialExpressionStaticSwitchParameter):n.set_editor_property('default_value',L.get_material_instance_static_switch_parameter_value(source,n.get_editor_property('parameter_name')))
 else:m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 if not m:raise RuntimeError('Material creation '+name)
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=3)
 oldbase=current(m,'BASE_COLOR',.03);oldrough=current(m,'ROUGHNESS',.5);oldmetal=current(m,'METALLIC',1. if not path else 0.)
 normalnode=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
 oldnormal=(normalnode,L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)) if normalnode else node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1))
 full=not path or any(s in slot.lower() for s in ('metal','collar','adapter','saddle','fastener'))
 mask=node(m,u.MaterialExpressionConstant,r=1.) if full else custom(m,'return smoothstep(.18,.55,Metal)*(1-smoothstep(.3,.65,max(Base.r,max(Base.g,Base.b))));',{'Metal':oldmetal,'Base':oldbase},1)
 for prop,old,key in [('BASE_COLOR',oldbase,'BaseColor'),('ROUGHNESS',oldrough,'Roughness'),('METALLIC',oldmetal,'Metallic')]:
  lerp=node(m,u.MaterialExpressionLinearInterpolate);wire(old,lerp,'A');wire(sample(m,key,uv),lerp,'B');wire(mask,lerp,'Alpha');output(lerp,prop)
 fineuv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0,u_tiling=12.,v_tiling=12.)
 output(custom(m,'return normalize(float3(Base.xy+Fine.xy*.18*Mask,Base.z));',{'Base':oldnormal,'Fine':sample(m,'Normal',fineuv),'Mask':mask},3),'NORMAL')
 E.set_metadata_tag(m,'M16CoatingReference','M_M16A2_PBR receiver UV (1049,2370)/4096; UV3 4cm tile; source UV0 structural normal/AO retained')
 L.recompile_material(m);save(m);materials[cachekey]=m
 # Same exterior material acquires the project's existing adhered-water layer.
 w=A.duplicate_asset(name+'_Wet',D+'/Materials',m)
 base=current(w,'BASE_COLOR',.03);rough=current(w,'ROUGHNESS',.5);norm=L.get_material_property_input_node(w,u.MaterialProperty.MP_NORMAL)
 wetness=node(w,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
 beads=custom(w,BEADS,{'UV':node(w,u.MaterialExpressionTextureCoordinate),'Wet':wetness},4)
 output(custom(w,'return Base*(1-Data.a*.055);',{'Base':base,'Data':beads},3),'BASE_COLOR')
 output(custom(w,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1),'ROUGHNESS')
 output(custom(w,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':norm,'Data':beads},3),'NORMAL')
 L.recompile_material(w);save(w);wet[m.get_path_name()]=w
 receipt['materials'][name]={'source':path,'dry':m.get_path_name(),'wet':w.get_path_name(),'saved':True};record();return m
for key,part in models['parts'].items():
 oldmesh=u.load_asset(D+'/Meshes/'+part['name'])
 if key in receipt['meshes'] and oldmesh and E.get_metadata_tag(oldmesh,'M16VisualOnlyExport')=='true':continue
 if oldmesh and E.get_metadata_tag(oldmesh,'M16VisualOnlyExport')!='true':
  E.rename_asset(oldmesh.get_path_name(),D+'/AuthoringRecovery/'+part['name']+'_SourceCollision_'+str(int(time.time())))
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
 mesh=imported(part['file'],part['name'],D+'/Meshes',options)
 slots=mesh.static_materials
 for i,s in enumerate(slots):
  label=str(s.material_slot_name)
  binding=label
  if binding not in part['bindings']:
   matches=[n for n in part['bindings'] if n.startswith(label+'_')]
   if len(matches)!=1:raise RuntimeError('Unknown source slot '+key+' '+label)
   binding=matches[0]
  s.material_interface=material(key,binding,part['bindings'][binding]);slots[i]=s
 mesh.set_editor_property('static_materials',slots)
 editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
 settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,settings)
 for name,spec in part['sockets'].items():
  socket=mesh.find_socket(name)
  if not socket:
   socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
  socket.set_editor_property('relative_location',u.Vector(*spec['location']));socket.set_editor_property('relative_rotation',u.Rotator(*spec['rotation']))
 E.set_metadata_tag(mesh,'M16VisualOnlyExport','true');E.set_metadata_tag(mesh,'M16AuthoringFrame',part['frame']);E.set_metadata_tag(mesh,'M16AttachmentSource',part['source']);save(mesh)
 b=mesh.get_bounds();extent=list(b.box_extent.to_tuple())
 receipt['meshes'][key]={'asset':mesh.get_path_name(),'extent_cm':extent,'frame':part['frame'],'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'saved':True};record()
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
library=u.load_asset(D+'/DA_M16_AttachmentWetMaterials') or A.create_asset('DA_M16_AttachmentWetMaterials',D,u.WeatherPresentationAssets,factory);library.set_editor_property('wet_materials',wet);save(library)
skeleton=load('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny').skeleton;compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for key,clip in animations['clips'].items():
 if key in receipt['animations']:continue
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
 data=options.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',120)
 asset=imported(clip['file'],clip['name'],D+'/Animations/'+clip['family'],options);asset.set_editor_property('bone_compression_settings',compression);save(asset)
 receipt['animations'][key]={'asset':asset.get_path_name(),'duration':asset.get_play_length(),'saved':True};record()
u.log('M16_UNIVERSAL_ATTACHMENTS_SAVED')
