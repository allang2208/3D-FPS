"""Authoring views at existing idle-pose interfaces; no game launch."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent;F=Matrix.Diagonal((1,-1,1,1));poses=json.loads((O/'pose_inputs.json').read_text())
def pm(t):
 q=t['q'];return F@Matrix.LocRotScale(Vector(t['p']),Quaternion((q[3],q[0],q[1],q[2])),Vector(t['s']))@F
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_Assembly40.blend'),use_scripts=False);rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local.copy();keep=json.loads((O/'model.json').read_text())['parts']+['TopCover_ReferenceRepair38','PistolGrip','Handguard','Stock','CarryHandle','FlashHider','FrontSight_Fitted']
for ob in list(bpy.data.objects):
 if ob.name not in keep:bpy.data.objects.remove(ob,do_unlink=True);continue
 ob.hide_set(False);ob.hide_render=False;xf=root.inverted()@ob.matrix_world;bone=next((g.name for g in ob.vertex_groups if g.name in poses['reference']),None)
 if bone:xf=pm(poses['clips']['idle']['bones'][bone])@pm(poses['reference'][bone]).inverted()@xf
 ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)
old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/SM_LMG201_A40_RearSight.fbx'),use_anim=False)
for ob in set(bpy.data.objects)-old:
 if ob.type=='MESH':ob.location+=Vector((.0008,.04252,.0855))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1400;scene.render.resolution_y=850;scene.render.resolution_percentage=100;s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.4,.4,.4);s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.background_type='WORLD';scene.world=scene.world or bpy.data.worlds.new('Modeling');scene.world.color=(.12,.12,.12)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.clip_end=5
for name,pos,target,scale in [('rear_joint',(-.28,.26,.18),(0,.02,.075),.18),('right_handle',(-.5,.09,.16),(-.025,.045,.055),.11),('cover_side',(-.5,-.16,.11),(0,-.165,.044),.22),('magazine_trigger',(.5,-.08,.015),(0,-.123,-.03),.27),('feed_side',(.5,-.16,.11),(0,-.165,.044),.22)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'_authored.png'));bpy.ops.render.render(write_still=True)
