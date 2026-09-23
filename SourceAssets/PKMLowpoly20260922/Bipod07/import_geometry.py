from pathlib import Path
import unreal as u
O=Path(__file__).parent
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Stop PIE before replacing PKM assets.')
for name in ['import_surfaces.py','reimport_mesh.py','import_bipod.py']:
 p=O/name;exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
print('PKM07 geometry/material assets saved.')
