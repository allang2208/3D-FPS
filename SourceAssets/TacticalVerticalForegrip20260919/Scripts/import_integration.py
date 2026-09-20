"""Import formal per-rifle assets in the running editor; preserve other assets."""
import json
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/TacticalVerticalForegrip20260919/Integration')
D='/Game/Weapons/TacticalVerticalForegrip20260919'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'guns':{},'saved':{},'game_tested':False};profiles=json.loads((O/'finish_profiles.json').read_text())
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(obj):
 ok=bool(E.save_loaded_asset(obj,False));receipt['saved'][obj.get_path_name()]=ok;record()
 if not ok:raise RuntimeError('Save failed '+obj.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(src,out,dst,pin):
 if not L.connect_material_expressions(src,out,dst,pin):raise RuntimeError('Material wire '+pin)
def output(src,out,prop):
 if not L.connect_material_property(src,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def custom(m,code,inputs,dim):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(dim)))
 pins=[]
 for k in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
 n.set_editor_property('inputs',pins)
 for k,(src,out) in inputs.items():link(src,out,n,k)
 return n
def imported(file,name,dest,options=None):
 if E.does_asset_exist(dest+'/'+name):raise RuntimeError('Formal target exists; read receipt before retry: '+dest+'/'+name)
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.options=options;t.automated=True;t.save=False
 A.import_asset_tasks([t]);obj=u.load_asset(dest+'/'+name)
 if not obj:raise RuntimeError('Import failed '+str(file))
 return obj
wet={}
for gun in ['M4','AKM','QBZ191','ASH12']:
 dest=D+'/'+gun;folder=O/gun;tex={}
 for key in ['BaseColor','MetalRough','Normal']:
  t=imported(folder/'Export/Textures'/('T_TacticalVerticalForegrip_'+key+'.png'),'T_TacticalVerticalForegrip_'+key,dest)
  t.srgb=key=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
  if key=='Normal':t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.flip_green_channel=True
  elif key=='MetalRough':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
  save(t);tex[key]=t
 mat=A.create_asset('M_TacticalVerticalForegrip',dest,u.Material,u.MaterialFactoryNew())
 if not mat:raise RuntimeError('Material exists or creation failed '+dest)
 samples={}
 for key,t in tex.items():
  samples[key]=node(mat,u.MaterialExpressionTextureSample,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 output(samples['BaseColor'],'RGB','BASE_COLOR');output(samples['MetalRough'],'G','ROUGHNESS');output(samples['MetalRough'],'B','METALLIC');output(samples['Normal'],'RGB','NORMAL')
 E.set_metadata_tag(mat,'WeaponFinishReference',profiles[gun]['source']);L.recompile_material(mat);save(mat)
 w=E.duplicate_asset(mat.get_path_name(),dest+'/M_TacticalVerticalForegrip_Wet')
 props={p:(L.get_material_property_input_node(w,getattr(u.MaterialProperty,'MP_'+p)),L.get_material_property_input_node_output_name(w,getattr(u.MaterialProperty,'MP_'+p))) for p in ['BASE_COLOR','ROUGHNESS','NORMAL']}
 uv=node(w,u.MaterialExpressionTextureCoordinate);param=node(w,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
 beads=custom(w,(O.parents[1]/'WeatherNatural20260912/WeaponBeads.hlsl').read_text(),{'UV':(uv,''),'Wet':(param,'')},4)
 for p,code,dim in [('BASE_COLOR','return Base*(1-Data.a*.055);',3),('ROUGHNESS','return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',1),('NORMAL','if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',3)]:
  result=custom(w,code,{'Base':props[p],'Data':(beads,'')},dim);output(result,'',p)
 L.recompile_material(w);save(w);wet[mat.get_path_name()]=w
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
 opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 mesh=imported(folder/'Export/SM_TacticalVerticalForegrip.fbx','SM_TacticalVerticalForegrip',dest,opt)
 for i,s in enumerate(mesh.static_materials):
  label=str(s.material_slot_name)
  m=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/M_AKM_Soviet_MountSteel') if gun=='AKM' and ('Adapter' in label or 'MountSteel' in label) else mat
  mesh.set_material(i,m)
 E.set_metadata_tag(mesh,'TacticalGripFrame',profiles[gun]['attachment_frame']);save(mesh)
 lod=u.ModelingService.set_lods(dest+'/SM_TacticalVerticalForegrip',[1.,.5,.2],True,True)
 if not lod.success:raise RuntimeError(str(lod))
 collision=u.ModelingService.generate_collision(dest+'/SM_TacticalVerticalForegrip','ConvexHulls',2,32,True)
 if not collision.success:raise RuntimeError(str(collision))
 b=mesh.get_bounds()
 receipt['guns'][gun]={'mesh':mesh.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'bounds_extent_cm':[b.box_extent.x,b.box_extent.y,b.box_extent.z],'lods':str(lod),'collision':str(collision),'wet_material':w.get_path_name()};record()
library=u.load_asset('/Game/Weather/RainVisibility/DA_WeatherPresentation')
if not library:
 raise RuntimeError('Current weather presentation library is unavailable')
mapping=dict(library.get_editor_property('wet_materials'));mapping.update(wet);library.set_editor_property('wet_materials',mapping);save(library)
receipt['weather_library']=library.get_path_name();receipt['status']='imported_saved_not_game_tested';record()
print('TACTICAL_GRIP_FORMAL_IMPORT_COMPLETE '+','.join(receipt['guns']))
