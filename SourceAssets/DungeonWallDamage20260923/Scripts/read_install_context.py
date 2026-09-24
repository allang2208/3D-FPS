"""Read the current world and unsaved package ownership before installation."""
import os
import unreal as u
print('process_id',os.getpid())
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
for label,world in [('editor',sub.get_editor_world()),('game',sub.get_game_world())]:
    print(label,world.get_path_name() if world else None)
print('dirty_maps',[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
print('dirty_dungeons',[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith('/Game/Dungeons/')])
