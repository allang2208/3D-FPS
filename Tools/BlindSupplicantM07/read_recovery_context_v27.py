"""Read only the editor state needed to safely save the recovery repair."""
import unreal as u
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
dirty = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_path_name().startswith('/Game/Monsters/BlindSupplicantM07/')]
print('M07_RECOVERY_CONTEXT '+str(dict(pie=level.is_in_play_in_editor(), dirty_m07=dirty)))
