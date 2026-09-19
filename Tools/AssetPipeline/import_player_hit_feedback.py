from pathlib import Path
import unreal
root = Path(unreal.Paths.project_dir())
task = unreal.AssetImportTask()
task.filename = str(root / 'SourceAssets/PlayerHitFeedback20260914/S_Player_MonsterHit.wav')
task.destination_path = '/Game/Audio/PlayerHitFeedback20260914'
task.destination_name = 'S_Player_MonsterHit'
task.automated = True
task.replace_existing = True
task.save = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Player hit feedback import failed')
unreal.log('PLAYER_HIT_FEEDBACK_IMPORTED')
