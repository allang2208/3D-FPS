import runpy
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/Tools/PoisonMaggot')
for script in ['update_physics.py','update_collision.py','substrate_materials.py','compile_materials.py','inspect_runtime_assets.py','place_village.py']:
 runpy.run_path(str(root/script),run_name='__main__')
