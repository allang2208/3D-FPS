"""Install contact animation and fresh wear materials, preserving mesh binding."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/QBZ191/ContactWear20260913';SOURCE='/Game/Weapons/QBZ191/Hero20260913'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
reference=u.load_asset(SOURCE+'/SK_QBZ191_Manny');materials={};report={'materials':{},'meshes':{},'clips':{}}
def connect(a,out,prop):
 if not L.connect_material_property(a,out,prop):raise RuntimeError('Material output failed: '+str(prop))
for group,info in json.loads((O/'textures.json').read_text()).items():
 name=info['material'];path=D+'/Materials/'+name
 mat=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 for kind,file in info['textures'].items():
  texname='T_QBZ191_Wear_'+group+'_'+kind
  task=u.AssetImportTask();task.filename=file;task.destination_path=D+'/Textures';task.destination_name=texname;task.automated=True;task.replace_existing=True;task.save=False
  A.import_asset_tasks([task]);tex=u.load_asset(D+'/Textures/'+texname)
  if not tex:raise RuntimeError('Texture import failed: '+texname)
  tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('lod_bias',0)
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
  if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
  if not E.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed: '+texname)
  node=L.create_material_expression(mat,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex)
  node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  if kind=='BaseColor':connect(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
  elif kind=='Normal':connect(node,'RGB',u.MaterialProperty.MP_NORMAL)
  else:connect(node,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION);connect(node,'G',u.MaterialProperty.MP_ROUGHNESS);connect(node,'B',u.MaterialProperty.MP_METALLIC)
 L.recompile_material(mat)
 if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed: '+name)
 materials[group]=mat;report['materials'][group]=mat.get_path_name();u.log('QBZ_WEAR_IMPORTED '+group)
# Reuse the imported mesh directly. Its existing inverse bind poses, skin,
# normals, tangents and folding head pivots remain byte-for-byte mesh data.
for name,skeletal in [('SK_QBZ191_Manny',True),('SM_QBZ191_RearSight',False),('SM_QBZ191_FrontSight',False)]:
 path=D+'/'+name;mesh=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(SOURCE+'/'+name,path)
 if not mesh:raise RuntimeError('Mesh duplication failed: '+name)
 slots=mesh.materials if skeletal else mesh.static_materials
 for i,slot in enumerate(slots):
  slotname=str(slot.material_slot_name);group=slotname.removeprefix('M_QBZ191_Hero_')
  if group not in materials:continue
  if skeletal:slot.material_interface=materials[group];slots[i]=slot
  else:mesh.set_material(i,materials[group])
 if skeletal:mesh.set_editor_property('materials',slots)
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed: '+name)
 report['meshes'][name]=mesh.get_path_name()
for key,info in json.loads((O/'build.json').read_text()).items():
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
 opt.skeleton=reference.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
 dest=D+'/Animations/'+info['family'];task=u.AssetImportTask();task.filename=info['file'];task.destination_path=dest;task.destination_name=info['name'];task.options=opt;task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);clip=u.load_asset(dest+'/'+info['name'])
 if not clip:raise RuntimeError('Animation import failed: '+key)
 clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
 u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
 if not E.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed: '+key)
 report['clips'][key]=clip.get_path_name();(O/'import.json').write_text(json.dumps(report,indent=2));u.log('QBZ_CONTACT_IMPORTED '+key)
report['skeleton']=reference.skeleton.get_path_name();report['status']='saved authoring assets; no runtime acceptance'
(O/'import.json').write_text(json.dumps(report,indent=2));u.log('QBZ_CONTACT_WEAR_IMPORT_COMPLETE')
