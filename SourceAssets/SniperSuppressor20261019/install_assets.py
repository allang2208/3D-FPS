"""Import/save only the new sniper attachment, its finish and production icon."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();D='/Game/Weapons/SniperSuppressor20261019'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text());receipt={'complete':False,'saved':[],'runtime_tested':False}
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():raise RuntimeError('Preserve current PIE assets')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('Preserve unsaved attachment assets')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());(O/'assets_receipt.json').write_text(json.dumps(receipt,indent=2))
def texture(filename,kind,folder=D+'/Textures'):
 task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder;task.destination_name=Path(filename).stem;task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+task.destination_name)
 if not asset:raise RuntimeError('Could not import '+str(filename))
 asset.srgb=kind in ('color','icon');asset.compression_settings={'color':u.TextureCompressionSettings.TC_BC7,'normal':u.TextureCompressionSettings.TC_NORMALMAP,'rough':u.TextureCompressionSettings.TC_GRAYSCALE,'icon':u.TextureCompressionSettings.TC_EDITOR_ICON}[kind]
 asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI if kind=='icon' else u.TextureGroup.TEXTUREGROUP_WEAPON
 if kind=='normal':asset.set_editor_property('flip_green_channel',True)
 if kind=='icon':asset.never_stream=True;asset.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 save(asset);return asset
parent=u.load_asset('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel')
if not parent:raise RuntimeError('Shared weapon material is unavailable')
materials={}
for label,spec in auth['textures'].items():
 name='MI_SniperSuppressor_'+label;mat=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 mat.set_editor_property('parent',parent)
 for key,filename,kind in [('SourceBaseColor',spec['base_color'],'color'),('SourceRoughness',spec['roughness_texture'],'rough'),('SurfaceNormal',spec['normal'],'normal')]:
  L.set_material_instance_texture_parameter_value(mat,key,texture(filename,kind))
 for key,value in dict(SourceColorWeight=1.,SourceRoughnessWeight=1.,SourceRoughnessPivot=.5,Roughness=.5,Metallic=1.,MaskUVChannel=0.,GrainRoughness=0.,MottleRoughness=0.,MottleColor=0.,Stipple=0.,EdgeWear=0.,EdgeHighlight=0.,CavityDarken=0.,CavityRoughness=0.,HandlingPolish=0.,ScratchAmount=0.,AOStrength=0.,WeaponWetness=0.).items():L.set_material_instance_scalar_parameter_value(mat,key,value)
 L.update_material_instance(mat);save(mat);materials[label]=mat
name='M_SniperSuppressor_Recess';recess=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(recess)
for cls,prop,value in [(u.MaterialExpressionConstant3Vector,u.MaterialProperty.MP_BASE_COLOR,u.LinearColor(.003,.0035,.004,1)),(u.MaterialExpressionConstant,u.MaterialProperty.MP_ROUGHNESS,.92),(u.MaterialExpressionConstant,u.MaterialProperty.MP_METALLIC,0.)]:
 node=L.create_material_expression(recess,cls)
 if cls==u.MaterialExpressionConstant3Vector:node.constant=value
 else:node.r=value
 L.connect_material_property(node,'',prop)
L.recompile_material(recess);save(recess);materials['Recess']=recess
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=D;task.destination_name=auth['model'];task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory()
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.import_uniform_scale=1.;data.convert_scene_unit=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;task.options=options
 A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+auth['model'])
 if not mesh:raise RuntimeError('Mesh import did not produce an asset')
 slots=list(mesh.static_materials)
 for i,slot in enumerate(slots):slot.material_interface=materials[str(slot.material_slot_name).removeprefix('SniperSuppressor_')];slots[i]=slot
 mesh.set_editor_property('static_materials',slots)
 for name,x in [('MountFace',0.),('Muzzle',auth['tip_cm']),('AimGuide',auth['tip_cm']+10.)]:
  socket=mesh.find_socket(name)
  if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
  socket.set_editor_property('relative_location',u.Vector(x,0,0))
 E.set_metadata_tag(mesh,'GunsmithOption','sniper_heavy_suppressor');E.set_metadata_tag(mesh,'CompatibleWeapons','ue_svd,ue_svch');save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
folder='ColdSteelData/AttachmentIcons20260913/FramedFirearms'
icon=texture(O/'muzzle_sniper_heavy_suppressor.png','icon','/Game/'+folder)
shutil.copy2(O/'muzzle_sniper_heavy_suppressor.png',P/'Content'/folder/'muzzle_sniper_heavy_suppressor.png')
receipt.update(complete=True,mesh=mesh.get_path_name(),icon=icon.get_path_name());(O/'assets_receipt.json').write_text(json.dumps(receipt,indent=2));print('SNIPER_SUPPRESSOR_ASSETS_SAVED',flush=True)
