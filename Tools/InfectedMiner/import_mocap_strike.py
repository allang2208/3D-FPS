"""Bind the validated human capture to the existing accepted miner mesh."""
import unreal,json,hashlib
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME');S=R/'SourceAssets/InfectedMiner20260912/Candidates/CMU02_07';D='/Game/Monsters/InfectedMiner/CMU02_07';contract=json.loads((S/'attack-authoring.json').read_text())
lib=unreal.EditorAssetLibrary;bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner');cdo=unreal.get_default_object(bp.generated_class());mesh=cdo.visual_mesh
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;o.skeleton=mesh.skeleton;o.import_mesh=False;o.import_animations=True;o.import_materials=False;o.import_textures=False;o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
t=unreal.AssetImportTask();t.filename=str(S/'A_Miner_Attack.fbx');t.destination_path=D;t.destination_name='A_Miner_CMUStrike';t.options=o;t.automated=True;t.save=True;unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=unreal.load_asset(D+'/A_Miner_CMUStrike');assert a and abs(a.get_play_length()-contract['seconds'])<.002
a.set_preview_skeletal_mesh(mesh);assert lib.save_loaded_asset(a,False)
cdo.set_editor_property('attack_clip',a);cdo.set_editor_property('contact_time',contract['contact_time']);cdo.set_editor_property('contact_end',contract['contact_end']);cdo.set_editor_property('attack_range',150.0);assert lib.save_loaded_asset(bp,False)
report={'source':'CMU 02_07 optical human capture','clip':a.get_path_name(),'mesh_preserved':mesh.get_path_name(),'seconds':a.get_play_length(),'contact_time':cdo.contact_time,'contact_end':cdo.contact_end,'range_cm':cdo.attack_range,'sha256':hashlib.sha256((S/'A_Miner_Attack.fbx').read_bytes()).hexdigest(),'saved':True}
(R/'Saved/InfectedMiner/mocap-import.json').write_text(json.dumps(report,indent=2));unreal.log('MINER_MOCAP_IMPORTED '+json.dumps(report))
