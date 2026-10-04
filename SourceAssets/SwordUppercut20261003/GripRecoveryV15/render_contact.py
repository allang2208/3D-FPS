"""Offline pose diagnosis: V7 skin and a clearly labeled hilt proxy, no game."""
from pathlib import Path
P=Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))
out=P/'PoseReview';out.mkdir(exist_ok=True)
for version,frame in [('V14',220),('V15',220),('V15',135),('V15',175)]:
    folder=ROOT/'trash/sword-uppercut-retired-20261004/SourceAssets/SwordUppercut20261003/StrideRhythmV14' if version=='V14' else P
    bpy.ops.wm.open_mainfile(filepath=str(folder/'Standard'/('Sword_Uppercut'+version+'_Editable.blend')))
    scene=bpy.context.scene
    scene.frame_set(frame)
    data=json.loads((folder/'Standard/editable_keys.json').read_text('utf-8'))
    pose={n:canonical(m) for n,m in globalize({n:native(k) for n,k in data['samples'][frame]['bones'].items()}).items()}
    weapon=mat(pose['WPN_root'].translation,pose['WPN_root'].to_quaternion())
    for obj in scene.objects:
        if obj.type=='MESH':obj.color=(.58,.32,.19,1.)
    for name,scale,center,color in [('Grip_proxy',(.014,.014,.115),(0,0,-.112),(.1,.18,.25,1)),
                                  ('Guard_proxy',(.080,.018,.012),(0,0,.012),(.4,.5,.6,1)),
                                  ('Blade_proxy',(.028,.004,.43),(0,0,.454),(.6,.65,.72,1))]:
        if name.startswith('Grip'):
            bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=1.,depth=2.)
        else:bpy.ops.mesh.primitive_cube_add(size=2.)
        obj=bpy.context.object;obj.name=name;obj.matrix_world=weapon@Matrix.Translation(Vector(center))
        obj.scale=scale;obj.color=color
    bpy.ops.object.camera_add(location=(0.,0.,0.))
    cam=bpy.context.object
    cam.rotation_euler=Vector((0,1,-.15)).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=18.;cam.data.clip_start=.01;cam.data.clip_end=10.
    scene.camera=cam
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO'
    scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH'
    scene.display.shading.background_type='WORLD'
    if not scene.world:scene.world=bpy.data.worlds.new('PoseReviewWorld')
    scene.world.color=(.055,.055,.065)
    scene.render.resolution_x=960;scene.render.resolution_y=640;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(out/(version+'_'+str(frame)+'_hilt_proxy.png'))
    bpy.ops.render.render(write_still=True)
print('POSE_REVIEW_SAVED offline V7 arm skin; proxy sword/hilt; not an in-game capture')
