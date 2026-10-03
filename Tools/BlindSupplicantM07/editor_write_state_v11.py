"""Read only the current editor's write prerequisites, without PIE/preview."""
import json
import unreal as u
print('M07_V11_EDITOR_WRITE_STATE '+json.dumps({
    'project':u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path()),
    'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
    'body_authoring_available':hasattr(u,'BlindSupplicantPhysicsAuthoring'),
    'cloth_authoring_available':hasattr(u,'BlindSupplicantAuthoring'),
}),flush=True)
