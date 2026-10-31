"""Cut away the enclosing tower shell for the top layout evidence view."""
import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parent/'Audit/after'
rows=json.loads((R/'components.json').read_text('utf8'))['components']
bpy.ops.wm.open_mainfile(filepath=str(R/'SavedGeometry_Diagnostic.blend'))
for ob in bpy.data.objects:
    if 'source_index' not in ob:continue
    row=rows[ob['source_index']];actor=row['actor']
    furniture=actor.startswith(('BP_','AP_Bed2_','AP7_Bed2_','AP_Container_Bed2_')) or actor in {'AP13_Control_Bed2','AP_Planter3','AP_Foliage3','AP_Floor_Bed2','Door_Bed2'}
    ob.hide_render=row['hidden'] or not furniture
bpy.context.scene.camera.data.ortho_scale=15.2
bpy.context.scene.render.filepath=str(R/'top.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'SavedGeometry_Diagnostic.blend'))
