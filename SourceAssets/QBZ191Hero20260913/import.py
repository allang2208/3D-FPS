"""Import authored QBZ surfaces and maps on the existing private skeleton."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/QBZ191/Hero20260913'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
reference=u.load_asset('/Game/Weapons/QBZ191/MagazineSeat20260913/SK_QBZ191_Manny')
bindings={str(m.material_slot_name):m.material_interface for m in reference.materials}
manifest=json.loads((O/'textures.json').read_text());materials={};receipt={'materials':{},'meshes':{}}

def connect(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed: '+pin)
def output(a,out,prop):
 if not L.connect_material_property(a,out,prop):raise RuntimeError('Material output failed: '+str(prop))

for group,info in manifest.items():
 name=info['material'];path=D+'/Materials/'+name
 m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(m);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 for kind,filename in info['textures'].items():
  texname='T_QBZ191_Hero_'+group+'_'+kind
  task=u.AssetImportTask();task.filename=filename;task.destination_path=D+'/Textures';task.destination_name=texname
  task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
  tex=u.load_asset(D+'/Textures/'+texname)
  if not tex:raise RuntimeError('Texture import failed: '+texname)
  tex.set_editor_property('srgb',kind=='BaseColor')
  tex.set_editor_property('lod_bias',0)
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
  if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
  if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed: '+texname)
  node=L.create_material_expression(m,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex)
  node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  if kind=='BaseColor':output(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
  elif kind=='Normal':output(node,'RGB',u.MaterialProperty.MP_NORMAL)
  else:
   output(node,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
   output(node,'G',u.MaterialProperty.MP_ROUGHNESS)
   output(node,'B',u.MaterialProperty.MP_METALLIC)
 L.recompile_material(m)
 if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Material save failed: '+name)
 materials[name]=m;receipt['materials'][name]=m.get_path_name()
 u.log('QBZ_HERO_MATERIAL_IMPORTED '+group)

for name,skeletal in [('SK_QBZ191_Manny',True),('SM_QBZ191_RearSight',False),('SM_QBZ191_FrontSight',False)]:
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
 opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
 opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
 if skeletal:
  opt.skeleton=reference.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False)
 else:data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 task=u.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=D;task.destination_name=name;task.options=opt
 task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
 if not mesh:raise RuntimeError('Mesh import failed: '+name)
 def binding(slot):
  slotname=str(slot.material_slot_name)
  return materials[slotname] if slotname in materials else bindings[slotname]
 if skeletal:
  slots=mesh.materials
  for i,slot in enumerate(slots):slot.material_interface=binding(slot);slots[i]=slot
  mesh.set_editor_property('materials',slots)
 else:
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,binding(slot))
 if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed: '+name)
 receipt['meshes'][name]=mesh.get_path_name()
receipt['skeleton']=reference.skeleton.get_path_name()
receipt['status']='imported; no rendered or gameplay test'
(O/'import.json').write_text(json.dumps(receipt,indent=2));u.log('QBZ_HERO_IMPORT_COMPLETE')
