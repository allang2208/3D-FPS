import json
import unreal as u
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
print('ARCANE_EDITOR_STATE '+json.dumps({'in_play':bool(level and level.is_in_play_in_editor())}))
