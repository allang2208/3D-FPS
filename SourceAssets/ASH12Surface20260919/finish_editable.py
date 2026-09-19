"""Update the editable material graphs only, with no bake/export/render."""
import bpy, sys
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from working_materials import apply_regions
bpy.ops.wm.open_mainfile(filepath=str(O/'ASH12_Surface_Editable.blend'))
apply_regions(bpy.data.objects['ASH12_Export'])
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_Surface_Editable.blend'))
