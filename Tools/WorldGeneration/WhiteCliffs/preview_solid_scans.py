import bpy
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME/SourceAssets/HillsLandscapeRepair20261117/SolidScansR9')
for name in ('CliffA','CliffB'):
    bpy.ops.wm.open_mainfile(filepath=str(root/(name+'.blend')))
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    lo=Vector([min(v[i] for v in points) for i in range(3)])
    hi=Vector([max(v[i] for v in points) for i in range(3)])
    center=(lo+hi)*.5;span=max(hi-lo)
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.6
    scene=bpy.context.scene;scene.camera=cam;scene.render.engine='BLENDER_WORKBENCH'
    scene.world=bpy.data.worlds.new('Review');scene.world.color=(.12,.12,.12)
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE'
    scene.display.shading.single_color=(.45,.43,.39);scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
    scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    for label,offset in [('front',(1.5,-2,1)),('back',(-1.5,2,1))]:
        cam.location=center+Vector(offset)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(root/(name+'-'+label+'.png'));bpy.ops.render.render(write_still=True)
