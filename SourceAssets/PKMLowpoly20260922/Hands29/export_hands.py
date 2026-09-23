"""Re-export current PKM assembly with shared primary UVs; no pose/geometry edits."""
import bpy
import sys
from pathlib import Path

O = Path(__file__).parent
R = O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'HandleFinish27/PKM_HandleFinish_Editable.blend'), use_scripts=False)
sys.path.insert(0, str(R/'Belt08'))
from mesh_export import export_mesh
(O/'Exports').mkdir(exist_ok=True)
export_mesh(bpy.data.objects['PKM_Manny_Rig'], O/'Exports/SK_PKM_Manny_Modular.fbx')
print('PKM29_UV_EXPORT_COMPLETE', flush=True)
