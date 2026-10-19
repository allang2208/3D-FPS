import bpy
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KDetail20261018')
bpy.ops.wm.open_mainfile(filepath=str(O/'Preview/ActualReview.blend'));scene=bpy.context.scene;ob=bpy.data.objects['Saiga12K_Ext12_SurfaceRebuilt'];bpy.data.objects['Saiga12K_SurfaceRebuilt'].hide_render=True;ob.hide_render=False
coords=[ob.matrix_world@Vector(p) for p in ob.bound_box];centre=sum(coords,Vector())/8;span=max(v.z for v in coords)-min(v.z for v in coords);camera=scene.camera;camera.location=centre+Vector((100,0,0));camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=span*1.2;scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.film_transparent=True;scene.render.filepath=str(O/'Preview/Ext12_IconSource.png');bpy.ops.render.render(write_still=True)
