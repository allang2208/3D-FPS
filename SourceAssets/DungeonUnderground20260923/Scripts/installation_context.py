import json
import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
print(json.dumps({'editor_world':world.get_path_name() if world else None,
                  'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
                  'dirty_content':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if 'Dungeon' in p.get_name()]},ensure_ascii=False),flush=True)
