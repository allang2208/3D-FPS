import bpy,math
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'selected_models.blend'))
s=bpy.context.scene;s.render.resolution_x=1000;s.render.resolution_y=560;s.cycles.samples=16
meshes=[o for o in s.objects if o.type=='MESH']
for side,x in [('stone',-.68),('dust',.68)]:
    root=bpy.data.objects.new(side+'_turntable',None);bpy.context.collection.objects.link(root);root.location=(x,0,0);bpy.context.view_layer.update()
    for o in meshes:
        mean=sum(v.co.x for v in o.data.vertices)/len(o.data.vertices)
        if (mean<0)==(x<0):o.parent=root;o.matrix_parent_inverse=root.matrix_world.inverted()
    root.rotation_euler.z=0;root.keyframe_insert(data_path='rotation_euler',frame=1)
    root.rotation_euler.z=math.tau;root.keyframe_insert(data_path='rotation_euler',frame=37)
    # Blender 5 layered actions expose channels through slot channelbags.
    for layer in root.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
s.frame_start=1;s.frame_end=36;s.render.fps=8;s.render.image_settings.file_format='PNG'
frames=P/'turntable_frames';frames.mkdir(exist_ok=True);s.render.filepath=str(frames/'frame_')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'turntable_editable.blend'))
bpy.ops.render.render(animation=True)
