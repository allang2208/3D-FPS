"""Read authoring dimensions from the saved mesh without starting gameplay."""
import json
from pathlib import Path
import unreal as u

mesh = u.load_asset('/Game/Items/Consumables/Baguette20261003/SM_Baguette')
if not isinstance(mesh, u.StaticMesh):
    raise RuntimeError('The saved baguette mesh is unavailable')
bounds = mesh.get_bounds()
def vector(v):
    return [v.x, v.y, v.z]
source = {'mesh': mesh.get_path_name(), 'origin_cm': vector(bounds.origin),
          'dimensions_cm': [v * 2 for v in vector(bounds.box_extent)],
          'playing': u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None}
Path('D:/FPS3D/FPSGAME/SourceAssets/Baguette20261003/fit_source.json').write_text(
    json.dumps(source, indent=2), encoding='utf-8')
u.log('BAGUETTE_FIT_SOURCE ' + json.dumps(source))
