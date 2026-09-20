"""Install the model upgrade at the existing drum paths in the running editor."""
import json
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LargeDrumUpgrade20260920')
D='/Game/Weapons/LargeDrumUpgrade20260920'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
sources=json.loads((O/'Reference/current_assets.json').read_text())
receipt_file=O/'import_receipt.json'
receipt=json.loads(receipt_file.read_text()) if receipt_file.exists() else {'status':'installing','guns':{},'saved':{},'game_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(obj):
 ok=bool(E.save_loaded_asset(obj,False));receipt['saved'][obj.get_path_name()]=ok;record()
 if not ok:raise RuntimeError('Package save failed '+obj.get_path_name())
def node(mat,cls,**props):
 n=L.create_material_expression(mat,cls)
 for key,value in props.items():n.set_editor_property(key,value)
 return n
def link(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection '+pin)
def output(a,out,prop):
 if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def custom(mat,code,pins,dim):
 n=node(mat,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(dim)))
 inputs=[]
 for name in pins:
  p=u.CustomInput();p.set_editor_property('input_name',name);inputs.append(p)
 n.set_editor_property('inputs',inputs)
 for name,(src,out) in pins.items():link(src,out,n,name)
 return n
def import_file(file,dest,name,options=None,replace=False):
 if not replace and E.does_asset_exist(dest+'/'+name):
  obj=u.load_asset(dest+'/'+name)
  if receipt['saved'].get(obj.get_path_name()):return obj
  raise RuntimeError('Revision target exists without saved receipt '+dest+'/'+name)
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name
 t.automated=True;t.replace_existing=replace;t.replace_existing_settings=replace;t.save=False;t.options=options
 A.import_asset_tasks([t]);obj=u.load_asset(dest+'/'+name)
 if not obj:raise RuntimeError('Import failed '+str(file))
 return obj
def mesh_options():
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
 opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False
 opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
 opt.static_mesh_import_data.generate_lightmap_u_vs=False
 opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 return opt
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is active; defer drum asset writes until it stops')
wet={}
for gun,source in sources.items():
 if receipt['guns'].get(gun,{}).get('saved'):
  existing=receipt['guns'][gun];wet[existing['materials'][0]]=u.load_asset(existing['wet_material']);continue
 dest=D+'/'+gun;old=u.load_asset(source['asset']);backup=D+'/Before/'+gun+'_OriginalDrum'
 if E.does_asset_exist(backup):
  if receipt['guns'].get(gun,{}).get('original_backup')!=backup:raise RuntimeError('Unrecorded backup '+gun)
  old_copy=u.load_asset(backup)
 else:old_copy=E.duplicate_asset(source['asset'],backup)
 if not old_copy:raise RuntimeError('Could not preserve original '+gun)
 save(old_copy);receipt['guns'][gun]={'original_backup':backup};record()
 textures={}
 for kind in ['BaseColor','MetalRough','Normal']:
  name='T_'+gun+'_Drum_'+kind;t=import_file(O/gun/'Textures'/(name+'.png'),dest,name)
  t.srgb=kind=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
  if kind=='Normal':t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.flip_green_channel=True
  elif kind=='MetalRough':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
  save(t);textures[kind]=t
 mat=u.load_asset(dest+'/M_'+gun+'_DrumSurface') if E.does_asset_exist(dest+'/M_'+gun+'_DrumSurface') else None
 create_graph=mat is None
 if create_graph:mat=A.create_asset('M_'+gun+'_DrumSurface',dest,u.Material,u.MaterialFactoryNew())
 if not mat:raise RuntimeError('Material creation failed '+gun)
 samples={}
 if create_graph:
  for kind,t in textures.items():samples[kind]=node(mat,u.MaterialExpressionTextureSample,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  for kind,channel,prop in [('BaseColor','RGB','BASE_COLOR'),('MetalRough','G','ROUGHNESS'),('MetalRough','B','METALLIC'),('Normal','RGB','NORMAL')]:output(samples[kind],channel,prop)
 E.set_metadata_tag(mat,'DrumFinish','Graphite polymer shell; per-rifle coated latch pins; own UV0 atlas')
 L.recompile_material(mat);save(mat)
 wet_path=dest+'/M_'+gun+'_DrumSurface_Wet'
 w=u.load_asset(wet_path) if E.does_asset_exist(wet_path) else E.duplicate_asset(mat.get_path_name(),wet_path)
 if not receipt['saved'].get(w.get_path_name()):
  uv=node(w,u.MaterialExpressionTextureCoordinate)
  param=node(w,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
  bead=custom(w,(O.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text(),{'UV':(uv,''),'Wet':(param,'')},4)
  for prop,code,dim in [('BASE_COLOR','return Base*(1-Data.a*.055);',3),('ROUGHNESS','return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',1),('NORMAL','if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',3)]:
   enum=getattr(u.MaterialProperty,'MP_'+prop)
   original=(L.get_material_property_input_node(w,enum),L.get_material_property_input_node_output_name(w,enum))
   result=custom(w,code,{'Base':original,'Data':(bead,'')},dim);output(result,'',prop)
 L.recompile_material(w);save(w);wet[mat.get_path_name()]=w
 # Keep the existing asset identity so actor, gunsmith, reload/drop and cook
 # consumers pick up the same model upgrade without a native logic change.
 path=source['asset'];target_dir,name=path.rsplit('/',1)
 mesh=import_file(O/'Export'/('SM_'+gun+'_LargeDrum_Upgrade.fbx'),target_dir,name,mesh_options(),True)
 slots=list(mesh.static_materials)
 if len(slots)!=len(source['slots']):
  # QBZ's former FBX used material names different from its runtime slot labels.
  # Reimport retains these legacy slots and appends the three new FBX slots.
  labels=[s['slot'] for s in source['slots']]
  chosen=[]
  for label in labels:
   candidates=[s for s in slots if str(s.get_editor_property('imported_material_slot_name'))==label]
   if len(candidates)!=1:raise RuntimeError('Cannot map imported material slot '+gun+' '+label)
   chosen.append(candidates[0])
  subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
  for section in range(mesh.get_num_sections(0)):
   old_index=subsystem.get_lod_material_slot(mesh,0,section)
   new_index=labels.index(str(slots[old_index].material_slot_name))
   subsystem.set_lod_material_slot(mesh,new_index,0,section)
  slots=chosen
 for i,slot in enumerate(slots):
  slot.material_interface=mat;slot.material_slot_name=source['slots'][i]['slot'];slots[i]=slot
 mesh.set_editor_property('static_materials',slots)
 E.set_metadata_tag(mesh,'ModelRevision','LargeDrumUpgrade20260920; original feed interface and runtime frame preserved')
 save(mesh)
 lod=u.ModelingService.set_lods(path,[1.,.55,.25],True,True)
 if not lod.success:raise RuntimeError(str(lod))
 collision=u.ModelingService.generate_collision(path,'ConvexHulls',3,48,True)
 if not collision.success:raise RuntimeError(str(collision))
 save(mesh);b=mesh.get_bounds()
 receipt['guns'][gun].update({'mesh':mesh.get_path_name(),'materials':[s.material_interface.get_path_name() for s in mesh.static_materials],
  'material_slots':[str(s.material_slot_name) for s in mesh.static_materials],
  'bounds_origin_cm':[b.origin.x,b.origin.y,b.origin.z],'bounds_extent_cm':[b.box_extent.x,b.box_extent.y,b.box_extent.z],
  'lods':str(lod),'collision':str(collision),'wet_material':w.get_path_name(),'saved':True});record()
table=u.load_asset('/Game/Weather/RainVisibility/DA_WeatherPresentation')
mapping=dict(table.get_editor_property('wet_materials'));mapping.update(wet);table.set_editor_property('wet_materials',mapping);save(table)
receipt['status']='three_drum_models_reimported_saved';receipt['weather_library']=table.get_path_name();record()
print('LARGE_DRUM_UPGRADE_INSTALLED '+','.join(receipt['guns']))
