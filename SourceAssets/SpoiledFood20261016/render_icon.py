"""Resume the requested icon production from the saved editable asset."""
import bpy,json
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'SpoiledFood_Editable.blend'))
scene=bpy.context.scene;obj=bpy.data.objects['SM_SpoiledFood']
source=(OUT/'author_asset.py').read_text()
exec(compile(source[source.index('# Render the requested transparent inventory icon'):],str(OUT/'author_asset.py'),'exec'))
