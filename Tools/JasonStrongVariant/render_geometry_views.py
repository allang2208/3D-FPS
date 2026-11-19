"""Render the authored geometry candidate with a shared neutral material."""
import bpy,math,sys
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Jason_StrongTall_R2_Geometry.blend'))
scene=bpy.context.scene
scene.cycles.samples=32
scene.cycles.device='CPU'
scene.render.resolution_x=1600;scene.render.resolution_y=1200
objects=[bpy.data.objects[name] for name in ('Jason_Original','Jason_OriginalHead','Jason_StrongTall_R2','Jason_UnchangedHead','Jason_NativeSkeleton')]
for name,angle in [('geometry_front',0),('geometry_three_quarter',-35),('geometry_back',180),('geometry_side',-90)]:
    if '--front-only' in sys.argv and angle!=0:continue
    for ob in objects:ob.rotation_euler.z=math.radians(angle)
    scene.render.filepath=str(OUT/'Previews'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print('JASON_STRONG_GEOMETRY_VIEWS_SAVED',flush=True)
