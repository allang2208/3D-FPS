import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/ArmSupport';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;E=u.MaterialEditingLibrary;report={}
def task(file,name,opt=None,dest=P):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
 if opt:t.options=opt
 A.import_asset_tasks([t]);a=u.load_asset(dest+'/'+name);assert a,name;return a
mesh=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative')
for variant in ['prism','angled']:
 for file in sorted((O/variant).glob('*.fbx')):
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  a=task(file,file.stem,opt,P+'/'+variant);a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert L.save_loaded_asset(a,False);report[file.stem]=a.get_play_length()
assert len(report)==18
m=u.load_asset(P+'/M_AKM_Soviet_MountSteel') if L.does_asset_exist(P+'/M_AKM_Soviet_MountSteel') else A.create_asset('M_AKM_Soviet_MountSteel',P,u.Material,u.MaterialFactoryNew());E.delete_all_material_expressions(m)
for kind,prop in [('Base_color',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Normal_OpenGL',u.MaterialProperty.MP_NORMAL)]:
 name='T_AKM_Mount_'+kind;t=task(O/'Metal'/(name+'.png'),name,dest=P+'/Textures');t.set_editor_property('srgb',kind=='Base_color')
 if kind=='Normal_OpenGL':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);t.set_editor_property('flip_green_channel',True)
 elif kind!='Base_color':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
 assert L.save_loaded_asset(t,False);node=E.create_material_expression(m,u.MaterialExpressionTextureSample);node.set_editor_property('texture',t)
 if kind=='Normal_OpenGL':node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 elif kind!='Base_color':node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
 assert E.connect_material_property(node,'RGB' if kind in ['Base_color','Normal_OpenGL'] else 'R',prop)
E.recompile_material(m);assert L.save_loaded_asset(m,False)
old=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SM_AKM_optic');bindings={str(s.material_slot_name):s.material_interface for s in old.static_materials}
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
optic=task(O/'SM_AKM_optic.fbx','SM_AKM_optic',opt);slots=optic.static_materials
for i,s in enumerate(slots):s.material_interface=m if str(s.material_slot_name)=='AKM_Soviet_MountSteel' else bindings[str(s.material_slot_name)];slots[i]=s
optic.set_editor_property('static_materials',slots);assert L.save_loaded_asset(optic,False)
report['optic']={'path':optic.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
(O/'import.json').write_text(json.dumps(report,indent=2));u.log('AKM_ARM_MOUNT_IMPORT_PASS')
