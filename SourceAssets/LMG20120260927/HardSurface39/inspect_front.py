import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'ReferenceRepair38/LMG201_ReferenceRepair38.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local.copy()
keep=['Barrel','GasTube','GasFrontHardware','Handguard','FrontSightBase_Fitted','FrontSight_Fitted','FlashHider','Receiver','TopRail','TopCover_ReferenceRepair38']
palette={'Barrel':(.55,.60,.65),'GasTube':(.20,.60,.85),'GasFrontHardware':(.90,.55,.12),'Handguard':(.40,.72,.30),'FrontSightBase_Fitted':(.60,.32,.72),'FrontSight_Fitted':(.70,.48,.78),'FlashHider':(.58,.64,.70)}
for ob in list(bpy.data.objects):
 if ob.name not in keep:bpy.data.objects.remove(ob,do_unlink=True)
for ob in list(bpy.data.objects):
 ob.hide_set(False);ob.hide_render=False;ob.modifiers.clear();xf=root.inverted()@ob.matrix_world;ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.normals_split_custom_set(ns)
 ob.color=(*palette.get(ob.name,(.55,.55,.55)),1)
 me=ob.data;me.calc_loop_triangles();np.savez_compressed(O/(ob.name+'.npz'),v=np.array([v.co[:] for v in me.vertices]),f=np.array([p.vertices[:] for p in me.loop_triangles]),mid=np.array([me.polygons[p.polygon_index].material_index for p in me.loop_triangles]))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1300;scene.render.resolution_y=750;scene.render.resolution_percentage=100;scene.world=scene.world or bpy.data.worlds.new('DiagnosticWorld')
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.1,.11,.13)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.005;cam.data.clip_end=5
def shot(name,pos,target,scale):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
shot('front_ownership',(-1,-.49,.14),(0,-.49,.04),.39)
shade.color_type='SINGLE';shade.single_color=(.35,.36,.39)
shot('front_before',(-1,-.49,.14),(0,-.49,.04),.39)
shot('front_below_before',(-.5,-.48,-.28),(0,-.48,.026),.30)
shot('receiver_before',(-.5,-.16,.17),(0,-.14,.043),.31)
