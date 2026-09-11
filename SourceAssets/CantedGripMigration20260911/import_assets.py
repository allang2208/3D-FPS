import unreal as u,json,sys,os
from pathlib import Path
O=Path(__file__).parent;A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;report=json.loads((O/'import.json').read_text()) if (O/'import.json').exists() else {};P='/Game/Weapons/AKMIntegration/SovietFab'
def task(file,name,opt,dest):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);asset=u.load_asset(dest+'/'+name);assert asset,name;return asset
for key in ['canted','vertical','angled']:
 if os.environ.get('FPS_GRIP_IMPORT_FILTER') and 'akm:'+key not in os.environ['FPS_GRIP_IMPORT_FILTER'].split(','):continue
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
 a=task(O/'akm'/f'SM_AKM_{key}.fbx','SM_AKM_'+key+('_CompactMount' if key=='canted' else ''),opt,P+'/GripErgonomic');original=u.load_asset('/Game/Weapons/M4CantedForegrip/SM_CantedForegrip' if key=='canted' else '/Game/Weapons/M4AngledForegripCompact75/SM_M4_AngledForegrip' if key=='angled' else '/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip');slots=a.static_materials
 for i,s in enumerate(slots):
  s.material_interface=u.load_asset(P+'/ArmSupport/M_AKM_Soviet_MountSteel') if 'AdapterSteel' in str(s.material_slot_name) else original.get_material(1 if key=='angled' and 'Grip' in str(s.material_slot_name) else 0);assert s.material_interface;slots[i]=s
 a.set_editor_property('static_materials',slots);assert L.save_loaded_asset(a,False);report[a.get_path_name()]={'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
for weapon,variant in [('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]:
 if os.environ.get('FPS_GRIP_IMPORT_FILTER') and weapon+':'+variant not in os.environ['FPS_GRIP_IMPORT_FILTER'].split(','):continue
 d=O/weapon/variant;build=json.loads((d/('animation_build.json' if weapon=='m4' else 'build.json')).read_text());assert len(build)==9
 mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='m4' else P+'/Attachments/SK_AKM_MannyNative');dest='/Game/Weapons/M4CantedErgonomic' if weapon=='m4' else P+'/GripErgonomic/'+variant
 for clip,info in build.items():
  name=f'A_{weapon.upper()}_{"Canted" if weapon=="m4" else variant}_{clip}';opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['sample_rate'])
  a=task(d/(name+'.fbx'),name,opt,dest);a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));u.AKMAnimationAuditLibrary.finish_animation_compression(a);assert L.save_loaded_asset(a,False);assert abs(a.get_play_length()-info['duration'])<.0001
  report[a.get_path_name()]={'duration':a.get_play_length(),'sample_rate':info['sample_rate'],'source':str(d/(name+'.fbx'))};(O/'import.json').write_text(json.dumps(report,indent=2));u.log('GRIP_MIGRATION_IMPORTED '+name)
u.log('GRIP_MIGRATION_IMPORT_PASS '+str(len(report))+' assets recorded')
