import unreal,json,shutil
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909');DEST='/Game/Weapons/M4Drum'
mesh=unreal.load_asset('/Game/Weapons/M4FoldingSights/SK_M4_FoldingSights');assert mesh
report=[]
for source_name,frames in [('A_M4_DrumReload',189),('A_M4_DrumReloadEmpty',229)]:
 name=source_name+'_Smooth'
 shutil.copyfile(OUT/(source_name+'.fbx'),OUT/(name+'.fbx'))
 o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;o.import_mesh=False;o.import_as_skeletal=False;o.import_animations=True;o.skeleton=mesh.skeleton;o.import_materials=False;o.import_textures=False
 o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 t=unreal.AssetImportTask();t.filename=str(OUT/(name+'.fbx'));t.destination_path=DEST;t.automated=True;t.replace_existing=True;t.save=True;t.options=o
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=unreal.load_asset(DEST+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False),name+' failed to save'
 assert a.get_editor_property('number_of_sampled_keys')==frames
 assert abs(a.get_play_length()-(frames-1)/60)<.0001
 report.append(dict(name=name,frames=frames,duration=a.get_play_length()))
(OUT/'reload-import.json').write_text(json.dumps(report,indent=2));unreal.log('M4_DRUM_RELOAD_IMPORT_PASS')
