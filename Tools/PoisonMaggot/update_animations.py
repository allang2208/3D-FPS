import unreal
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');src=root/'SourceAssets/PoisonMaggot20260911/delivery';dest='/Game/Monsters/PoisonMaggot';lib=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools();mesh=unreal.load_asset(dest+'/SK_PoisonMaggot')
for name in ['Idle','Move','Spit','Death','Hit']:
 opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
 t=unreal.AssetImportTask();t.filename=str(src/f'A_PoisonMaggot_{name}.fbx');t.destination_path=dest;t.destination_name=f'A_PoisonMaggot_{name}';t.automated=True;t.replace_existing=True;t.save=True;t.options=opt;tools.import_asset_tasks([t])
pa=unreal.PoisonMaggotMonster.create_physics_asset(mesh);assert pa;lib.save_loaded_asset(pa,False);lib.save_loaded_asset(mesh,False);lib.save_loaded_asset(mesh.skeleton,False)
unreal.log('MAGGOT_FINAL_ANIMATIONS_IMPORTED')
