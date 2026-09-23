"""Read only the package ownership needed for the necessary native build."""
import unreal as u,json
from pathlib import Path
packages=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()+u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
result={'dirty_packages':[p.get_name() for p in packages],'map':u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name()}
Path(__file__).with_name('build_editor_state.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
