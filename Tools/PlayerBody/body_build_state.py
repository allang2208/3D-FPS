"""Read the active editor's unsaved state before the required native rebuild."""
from pathlib import Path
import json
import os
import unreal as u

if Path(u.Paths.project_dir()).resolve() != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected project")
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print(json.dumps({"project": str(Path(u.Paths.project_dir()).resolve()), "pid": os.getpid(),
                  "play_world": world.get_path_name() if world else None,
                  "dirty_content": [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
                  "dirty_maps": [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}))
