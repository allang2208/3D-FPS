"""Requested defect diagnosis: cover exterior and opened visible shell only."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_ReferenceRepair38.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local.copy()
keep=['Receiver','TopCover_ReferenceRepair38','TopRail','Handguard']
for ob in list(bpy.data.objects):
 if ob.name not in keep:bpy.data.objects.remove(ob,do_unlink=True)
for ob in list(bpy.data.objects):
 ob.hide_set(False);ob.hide_render=False;ob.modifiers.clear();xf=root.inverted()@ob.matrix_world
 ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
 ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.normals_split_custom_set(ns)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world=scene.world or bpy.data.worlds.new('DiagnosticWorld')
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='SINGLE';shade.single_color=(.30,.32,.35);shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.show_specular_highlight=True;shade.background_type='WORLD';scene.world.color=(.12,.13,.15)
cam=bpy.data.objects.new('ReferenceDiagnosticCamera',bpy.data.cameras.new('ReferenceDiagnosticCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.005;cam.data.clip_end=10
def shot(name,p,target,scale):
 cam.location=p;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
shot('closed_shape',( .135,.10,.185),(0,-.155,.064),.235)
lid=bpy.data.objects['TopCover_ReferenceRepair38'];pivot=Vector((.0008,-.232,.0698));rot=Matrix.Rotation(math.radians(95),4,'X');ns=[rot.to_3x3()@n.vector for n in lid.data.corner_normals];lid.data.transform(Matrix.Translation(pivot)@rot@Matrix.Translation(-pivot));lid.data.normals_split_custom_set(ns)
shot('open_shape',(.055,.12,.185),(0,-.176,.123),.25)
for ob in bpy.data.objects:
 if ob.type=='MESH' and ob!=lid:ob.hide_render=True
shot('inside_shape',(.018,.18,.18),(0,-.23,.132),.188)
