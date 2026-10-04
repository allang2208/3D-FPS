"""Import and save only Gaze V08 assets; reuse the accepted M09 body/skeleton."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/GazeV08')
DEST='/Game/Monsters/HangingBellM09/V08';BASE='/Game/Monsters/HangingBellM09/V04'
A=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
report={'saved':[],'complete':False,'tested':False}
if not globals().get('M09_COMMANDLET',False):
 if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
 for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
  if p.get_path_name().startswith(DEST) or p.get_path_name()==BASE+'/SK_M09_Skeleton':raise RuntimeError('Preserve unsaved M09 target '+p.get_path_name())
def owned(path):
 if not A.does_asset_exist(path):return None
 asset=u.load_asset(path)
 if A.get_metadata_tag(asset,'M09Production')!='GazeV08':raise RuntimeError('Preserve existing asset '+path)
 return asset
def save(asset):
 A.set_metadata_tag(asset,'M09Production','GazeV08')
 if not A.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 report['saved'].append(asset.get_path_name())
 (ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print('M09_V08_SAVED '+asset.get_path_name())
def imp(file,name,folder,options=None,factory=None):
 path=folder+'/'+name;existing=owned(path)
 if existing:return existing
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
 task.automated=True;task.save=False;task.replace_existing=False
 if options:task.options=options
 if factory:task.factory=factory
 T.import_asset_tasks([task]);result=u.load_asset(path)
 if not result:raise RuntimeError('Import failed '+path)
 return result
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
mesh=u.load_asset(BASE+'/SK_M09');skeleton=mesh.skeleton
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
opt.import_as_skeletal=True;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
anim=opt.anim_sequence_import_data;anim.convert_scene=True;anim.convert_scene_unit=True;anim.import_uniform_scale=1.
anim.set_editor_property('use_default_sample_rate',False);anim.set_editor_property('custom_sample_rate',60)
anim.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
clip=imp(ROOT/'Exports/A_M09_Gaze_V08.fbx','A_M09_Gaze_V08',DEST+'/Animations',opt,u.FbxFactory())
clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False)
clip.set_preview_skeletal_mesh(mesh);save(clip)
if skeleton.get_path_name().split('.')[0] in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
 if globals().get('M09_SHARED_SKELETON_READ_ONLY',False):raise RuntimeError('Shared skeleton became dirty; preserve the running editor dependency')
 if not A.save_loaded_asset(skeleton,True):raise RuntimeError('Skeleton dependency save failed')
 report['saved'].append(skeleton.get_path_name())
report['skeleton_reused']=skeleton.get_path_name()
snd=imp(ROOT/'Audio/S_M09_Gaze_V08.wav','S_M09_Gaze_V08',DEST+'/Audio',factory=u.SoundFactory());snd.set_editor_property('volume',.85);save(snd)
def material(role,instanced,depth):
 name='M_M09_'+role+'_V08';path=DEST+'/Materials/'+name
 mat=owned(path) or T.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 for old in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,old)
 mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
 mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 mat.set_editor_property('two_sided',True);mat.set_editor_property('disable_depth_test',False)
 if instanced:L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
 def node(cls,**props):
  n=L.create_material_expression(mat,cls)
  for k,v in props.items():n.set_editor_property(k,v)
  return n
 def wire(a,b,pin):
  if isinstance(pin,int):pin=str(L.get_material_expression_input_names(b)[pin])
  if not L.connect_material_expressions(a,'',b,pin):raise RuntimeError('Material connection failed '+str(pin))
 inputs={'UV':node(u.MaterialExpressionTextureCoordinate),
  'Strength':node(u.MaterialExpressionScalarParameter,parameter_name='Strength',default_value=0.),
  'Clock':node(u.MaterialExpressionScalarParameter,parameter_name='Clock',default_value=0.),
  'FirePower':node(u.MaterialExpressionScalarParameter,parameter_name='FirePower',default_value=0.),
  'Exposure':node(u.MaterialExpressionEyeAdaptation)}
 if instanced:
  data=node(u.MaterialExpressionPerInstanceCustomData,data_index=0,const_default_value=1.)
  interp=node(u.MaterialExpressionVertexInterpolator);wire(data,interp,0);inputs['InstanceAlpha']=interp
 custom=node(u.MaterialExpressionCustom,description='M09 original '+role,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
  code=(ROOT/'Authoring'/(role+'.hlsl')).read_text(encoding='utf8'))
 pins=[]
 for key in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
 custom.set_editor_property('inputs',pins)
 for key,source in inputs.items():wire(source,custom,key)
 rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
 alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
 wire(custom,rgb,0);wire(custom,alpha,0)
 fade=node(u.MaterialExpressionDepthFade,fade_distance_default=depth);wire(alpha,fade,0)
 L.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
 L.recompile_material(mat);save(mat);return mat
beam=material('GazeBeam',False,15.)
filament=material('GazeFilament',True,2.)
iris=material('GazeIris',True,.35)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
geo=opt.static_mesh_import_data;geo.convert_scene=True;geo.convert_scene_unit=True;geo.import_uniform_scale=1.
geo.set_editor_property('auto_generate_collision',False);geo.set_editor_property('combine_meshes',True)
geo.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
for name,mat in [('SM_M09_GazeRibbon_V08',beam),('SM_M09_IrisVeil_V08',iris)]:
 asset=imp(ROOT/'FX'/(name+'.fbx'),name,DEST+'/FX',opt,u.FbxFactory());asset.set_material(0,mat);save(asset)
report['complete']=True
(ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M09_V08_IMPORT_COMPLETE assets='+str(len(report['saved'])))
