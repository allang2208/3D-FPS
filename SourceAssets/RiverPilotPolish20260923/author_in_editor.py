"""Save the river polish through the existing editor's serialized MCP batch."""
from pathlib import Path
import unreal as u

expected=Path('D:/FPS3D/FPSGAME').resolve()
actual=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if actual!=expected:
    raise RuntimeError('River authoring requires FPSGAME, found '+str(actual))
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.is_in_play_in_editor():
    raise RuntimeError('River asset authoring requires PIE to end before replacing emitter graphs.')
script=expected/'Tools/Fluids/author_river_pilot.py'
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),
     {'__file__':str(script),'__name__':'__main__'})
