"""Diagnostic images only, using the original skin and controlled source poses."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
OUT=ROOT/'Frames';OUT.mkdir(exist_ok=True)
# Read the existing fitting helpers into memory, stopping before production writes.
author=BASE/'LibraryMotionV7/author_library_motion.py'
prefix=author.read_text(encoding='utf-8').split("report={'movement':{}")[0]
ns={'__file__':str(author),'__name__':'diagnostic_helpers'}
exec(compile(prefix,str(author),'exec'),ns)
rig=ns['rig'];meshes=ns['meshes'];scene=ns['scene'];apply=ns['apply'];sample=ns['sample']
# Rendering evaluates the scene again: remove the loaded Idle action so that
# these direct diagnostic poses survive that evaluation.
rig.animation_data_clear()
original_rest={b.name:Matrix.Identity(4) for b in rig.pose.bones}
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=320;scene.render.resolution_y=384
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
scene.world.color=(.04,.04,.04)
for ob in meshes:ob.color=(.53,.59,.60,1)
cam_data=bpy.data.cameras.new('AuditCamera');cam=bpy.data.objects.new('AuditCamera',cam_data)
scene.collection.objects.link(cam);scene.camera=cam
cam.location=(3.5,-6,2.0);target=Vector((0,0,.95))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.type='ORTHO';cam_data.ortho_scale=2.22
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.004));plane=bpy.context.object
plane.name='DiagnosticFloor';plane.color=(.13,.15,.17,1)

def render(folder,index):
    out=OUT/folder;out.mkdir(exist_ok=True)
    scene.render.filepath=str(out/f'{index:03d}.png')
    bpy.ops.render.render(write_still=True)

# Isolated bend probes on the unmodified original skin, no library motion involved.
for i,(name,degrees,axis) in enumerate([(None,0,(1,0,0)),('LeftForeArm',90,(1,0,0)),('LeftLeg',90,(1,0,0)),('LeftArm',60,(0,1,0))]):
    apply(original_rest)
    if name:
        m=rig.matrix_world@rig.pose.bones[name].matrix
        rig.pose.bones[name].matrix=rig.matrix_world.inverted()@Matrix.LocRotScale(
            m.translation,Quaternion(axis,math.radians(degrees))@m.to_quaternion(),m.to_scale())
    bpy.context.view_layer.update();render('JointProbes',i)

# Same native-retargeted source poses and same skin. Toggle only the authoring
# gaze/ground adjustments to expose where coordinated head/body motion changed.
seconds=ns['metadata']['Walk_A']['seconds'];fps=8;frames=round(seconds*fps)
apply(sample('Walk_A',0));p0=ns['point']('Hips').copy()
apply(sample('Walk_A',seconds));drift=ns['point']('Hips')-p0
metrics=[]
for i in range(frames):
    t=i/fps
    apply(sample('Walk_A',t));ns['move_hips'](Vector((-drift.x*t/seconds,-drift.y*t/seconds,0)))
    # Both columns get identical skin grounding, to isolate the gaze modifier.
    ns['ground']();render('SourceHeadMotion',i)
    before={n:list((rig.matrix_world@rig.pose.bones[n].matrix).to_quaternion()) for n in ['neck','Head']}
    ns['gaze']();render('CurrentLockedHead',i)
    metrics.append(dict(t=t,before=before,after={n:list((rig.matrix_world@rig.pose.bones[n].matrix).to_quaternion()) for n in ['neck','Head']}))
(ROOT/'diagnostic_render.json').write_text(json.dumps(dict(fps=fps,frames=frames,seconds=seconds,
    scope='same skin and body animation; only gaze on/off; diagnostic, not new installed assets',metrics=metrics),indent=2),encoding='utf-8')
print('SPITTER_DIAGNOSTIC_RENDERS_DONE',flush=True)
