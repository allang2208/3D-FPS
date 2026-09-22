import unreal as u
print([p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_path_name().startswith('/Game/Monsters/WitchRebuilt')])
