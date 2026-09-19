import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/Attachments';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary
old=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/SK_AKM_MannyNative');assert old
for clip in ['reload','reload_empty']:
 dest=P+'/A_AKM_drum_'+clip
 if not L.does_asset_exist(dest):assert L.duplicate_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_'+clip,dest)
 assert L.save_asset(dest,only_if_is_dirty=False)
sources=json.loads((O/'sources.json').read_text());report={}
adapter=u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/M_AKM_FabGunsteel');assert adapter
def task(file,name,options,dest=P):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.options=options;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);m=u.load_asset(dest+'/'+name);assert m,name;return m
for key,spec in sources.items():
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
 m=task(O/f'SM_AKM_{key}.fbx','SM_AKM_'+key,opt);slots=m.get_editor_property('static_materials');i=0
 for j,s in enumerate(slots):
  if 'AdapterSteel' in str(s.material_slot_name):s.material_interface=adapter
  else:s.material_interface=u.load_asset(spec['materials'][min(i,len(spec['materials'])-1)]);i+=1
  slots[j]=s
 m.set_editor_property('static_materials',slots);assert L.save_loaded_asset(m,False);report[key]={'path':m.get_path_name(),'slots':[str(s.material_slot_name) for s in slots]}
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=old.skeleton
m=task(O/'SK_AKM_MannyNative.fbx','SK_AKM_MannyNative',opt);bindings={str(s.material_slot_name):s.material_interface for s in old.materials};slots=m.materials
for i,s in enumerate(slots):s.material_interface=bindings['M_AKM_Soviet_PBR'] if str(s.material_slot_name)=='M_AKM_Soviet_Magazine' else bindings[str(s.material_slot_name)];slots[i]=s
m.set_editor_property('materials',slots);assert L.save_loaded_asset(m,False)
for variant in ['prism','angled']:
 for file in sorted((O/variant).glob('A_AKM_*.fbx')):
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=old.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  a=task(file,file.stem,opt,P+'/'+variant);a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert L.save_loaded_asset(a,False);report[file.stem]=a.get_play_length()
(O/'import.json').write_text(json.dumps(report,indent=2));u.log('AKM_ATTACHMENTS_IMPORT_PASS')
