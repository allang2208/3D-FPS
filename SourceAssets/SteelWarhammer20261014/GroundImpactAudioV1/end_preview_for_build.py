import unreal as u
from pathlib import Path
P=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=P.parents[2]:raise RuntimeError('Wrong project')
if u.EditorLoadingAndSavingUtils.get_dirty_content_packages() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve unsaved editor content')
# Normal PIE shutdown for the authorized formal build; no force termination.
u.EditorLevelLibrary.editor_end_play()
print('Normal end-play requested for formal build')
