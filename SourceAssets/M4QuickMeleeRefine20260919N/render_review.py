import bpy, math, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['M']
revision=args[0]; profile=args[1] if len(args)>1 else 'Base'
source_root=P.parent
if revision in ('J', 'L', 'M'):
    source_root=P.parent.parent/'trash/quick-melee-retired-20260919/SourceAssets'
source=source_root/f'M4QuickMeleeRefine20260919{revision}'/profile/f'M4_QuickCombat_{profile}_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_M4_Infima']; scene=bpy.context.scene
for ob in scene.objects:
    if ob.type in ('MESH','ARMATURE','FONT'):
        keep=ob==rig or (ob.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in ob.modifiers))
        ob.hide_render=not keep
        if ob.name in bpy.context.view_layer.objects: ob.hide_set(not keep)
        if keep and ob.type=='MESH': ob.color=(.55,.63,.72,1) if 'Arms' in ob.name else (.16,.19,.21,1)
camera=bpy.data.cameras.new('WristReview'); cam=bpy.data.objects.new('WristReview',camera)
camera.clip_start=.001
scene.collection.objects.link(cam); scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'
scene.display.shading.color_type='OBJECT'; scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True; scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD'; scene.world.color=(.075,.075,.075)
scene.render.resolution_x=800; scene.render.resolution_y=450; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
out=P/'Review'; out.mkdir(exist_ok=True)
frames=[0,8,12,20,32,72,96,108] if revision!='M' else [0,12,20,32]
motion='motion' in args
if motion: frames=list(range(0,109,4))
elif profile!='Base': frames=[12,20,72]
for frame in frames:
    scene.frame_set(frame); bpy.context.view_layer.update()
    for view in (('fp',) if motion else ('fp','wrist')):
        if view=='fp':
            cam.location=(-.07,0,.07); cam.rotation_euler=(math.pi/2,0,0); camera.type='PERSP'; camera.lens=13.2
        else:
            wrist=rig.matrix_world @ rig.pose.bones['hand_r'].matrix.translation
            center=wrist+Vector((.02,-.07,-.035))
            cam.location=center+Vector((.55,-.40,.23)); cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
            camera.type='ORTHO'; camera.ortho_scale=.52
        scene.render.filepath=str(out/f'{revision}_{profile}_{view}_{frame:03}.png')
        bpy.ops.render.render(write_still=True)
print('REVIEW_RENDERED',revision,profile,flush=True)
