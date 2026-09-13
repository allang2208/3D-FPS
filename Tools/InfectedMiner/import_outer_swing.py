"""Import the corrected exterior attack arc into the existing miner BP."""
import unreal,json
from pathlib import Path

ROOT=Path(unreal.Paths.project_dir())/'SourceAssets/InfectedMiner20260913/OuterSwing/Delivery'
DEST='/Game/Monsters/InfectedMiner/OuterSwing20260913'
mesh=unreal.load_asset('/Game/Monsters/InfectedMiner/DragGround20260913/SK_InfectedMiner_DragGround')
options=unreal.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
options.skeleton=mesh.skeleton;options.import_mesh=False;options.import_animations=True
options.import_materials=False;options.import_textures=False
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
name='A_Miner_OuterSwing_Attack'
task=unreal.AssetImportTask();task.filename=str(ROOT/'A_Miner_Attack.fbx')
task.destination_path=DEST;task.destination_name=name;task.options=options
task.automated=True;task.replace_existing=True;task.save=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
clip=unreal.load_asset(DEST+'/'+name)
if not clip:raise RuntimeError('Import failed: '+name)
unreal.AnimationLibrary.remove_all_animation_notify_tracks(clip)
clip.set_preview_skeletal_mesh(mesh)
unreal.EditorAssetLibrary.save_loaded_asset(clip,False)
bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner')
cdo=unreal.get_default_object(bp.generated_class());cdo.set_editor_property('attack_clip',clip)
unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
report=json.loads((ROOT/'rebuild.json').read_text())
report['clips']['Attack']['path']=clip.get_path_name()
(ROOT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MINER_OUTER_SWING_IMPORTED '+clip.get_path_name())
