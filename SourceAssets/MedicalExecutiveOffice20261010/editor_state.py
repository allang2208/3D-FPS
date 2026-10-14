"""Report only the editor state needed to save without interrupting the user."""
import json,unreal as u
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
print('MEDICAL_OFFICE_SAVE_STATE',json.dumps(dict(
 playing=bool(ed.get_game_world()),world=str(ed.get_game_world()),dirty_maps_truth=bool(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
 dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 dirty_assets=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]),ensure_ascii=False))
