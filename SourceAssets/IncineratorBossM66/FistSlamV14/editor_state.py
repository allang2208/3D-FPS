import json,unreal as u
print('M66_EDITOR_STATE '+json.dumps({'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
    'dirty_m66':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Monsters/IncineratorBossM66')]}))
