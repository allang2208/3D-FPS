import bpy
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'HardSurface39/LMG201_HardSurface39.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local.copy()
for ob in list(bpy.data.objects):
 if ob.name not in ['Receiver','TopRail','RearSightBase_Fitted','TopCover_ReferenceRepair38','TriggerGuard_Fitted','PistolGrip']:bpy.data.objects.remove(ob,do_unlink=True);continue
 ob.hide_set(False);ob.hide_render=False;xf=root.inverted()@ob.matrix_world;ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)
old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/Before_RearSight.fbx'),use_anim=False)
for ob in set(bpy.data.objects)-old:
 if ob.type=='MESH':ob.location+=Vector((.0008,.04252,.0855))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1500;scene.render.resolution_y=900;scene.render.resolution_percentage=100;s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.4,.4,.4);s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.background_type='WORLD';scene.world=scene.world or bpy.data.worlds.new('Modeling');scene.world.color=(.12,.12,.12)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.clip_end=5
for name,pos,target,scale in [('rear_joint',(-.28,.26,.18),(0,.02,.075),.18),('right_handle',(-.5,.09,.16),(-.025,.045,.055),.11),('cover_side',(-.5,-.16,.11),(0,-.165,.044),.22)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'_source.png'));bpy.ops.render.render(write_still=True)
