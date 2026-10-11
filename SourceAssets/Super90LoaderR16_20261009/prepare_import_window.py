"""End an existing PIE session only to replace the requested loader assets."""
import unreal as u,json
s=u.get_editor_subsystem(u.LevelEditorSubsystem)
playing=s.is_in_play_in_editor()
if playing:s.editor_request_end_play()
print(json.dumps(dict(pie_was_active=playing,end_requested=playing)),flush=True)
