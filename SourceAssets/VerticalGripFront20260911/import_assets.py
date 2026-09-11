import unreal as u,json,os
from pathlib import Path
O=Path(__file__).parent;L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();P='/Game/Weapons/AKMIntegration/SovietFab';report=json.loads((O/'import.json').read_text()) if os.environ.get('FPS_FRONT_FILTER') and (O/'import.json').exists() else {};imported=0
for weapon in ['m4','akm']:
 for variant in ['vertical','prism']:
  if os.environ.get('FPS_FRONT_FILTER') and weapon+':'+variant not in os.environ['FPS_FRONT_FILTER'].split(','):continue
  d=O/weapon/variant;build=json.loads((d/('animation_build.json' if weapon=='m4' else 'build.json')).read_text());assert len(build)==9
  mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='m4' else P+'/Attachments/SK_AKM_MannyNative');dest='/Game/Weapons/M4VerticalGripOpposed/'+variant.title() if weapon=='m4' else P+'/GripOpposed/'+variant
  for clip,info in build.items():
   name=f'A_{weapon.upper()}_{variant.title() if weapon=="m4" else variant}_{clip}';opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['sample_rate'])
   t=u.AssetImportTask();t.filename=str(d/(name+'.fbx'));t.destination_path=dest;t.destination_name=name;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);a=u.load_asset(dest+'/'+name);assert a
   a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));u.AKMAnimationAuditLibrary.finish_animation_compression(a);assert L.save_loaded_asset(a,False);assert abs(a.get_play_length()-info['duration'])<.0001
   report[a.get_path_name()]={'duration':a.get_play_length(),'sample_rate':info['sample_rate'],'source':str(d/(name+'.fbx'))};(O/'import.json').write_text(json.dumps(report,indent=2));imported+=1;u.log('FRONT_IMPORTED '+name)
u.log('FRONT_IMPORT_PASS '+str(imported))
