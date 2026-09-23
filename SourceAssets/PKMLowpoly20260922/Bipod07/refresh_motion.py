"""Refresh authored hand actions without rebaking unchanged weapon surfaces."""
import bpy,json,math,pathlib
from mathutils import Matrix,Vector
O=pathlib.Path(__file__).parent;R=O.parent;E=O/'Exports'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Gameplay_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];s.render.fps=60
names=['PKM_Idle','PKM_Reload_Normal','PKM_Reload_Empty']
for a in list(bpy.data.actions):
 if a.name in names or a.name.startswith('PKM_Game_'):bpy.data.actions.remove(a,do_unlink=True)
with bpy.data.libraries.load(str(O/'PKM_Manny_Reload_Editable.blend'),link=False) as (src,dst):dst.actions=names
source=(O/'author_gameplay.py').read_text();source=source[source.index('def action(a):'):]
start=source.index('# Material sections');end=source.index("action(bpy.data.actions['PKM_Idle'])")
source=source[:start]+"sections=json.loads((O/'authoring.json').read_text())['sections']\n"+source[end:]
exec(compile(source,str(O/'author_gameplay.py'),'exec'))
