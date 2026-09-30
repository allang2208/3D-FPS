import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'ReferenceRepair38/Exports/SK_LMG201_R38_Installed.fbx'),use_anim=False)
rig=next(ob for ob in bpy.data.objects if ob.type=='ARMATURE');inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted();out=[]
for ob in list(bpy.data.objects):
 if ob.type!='MESH':continue
 xf=inv@ob.matrix_world;ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)
 me=ob.data;me.calc_loop_triangles();v=np.array([q.co[:] for q in me.vertices]);f=np.array([p.vertices[:] for p in me.loop_triangles]);mid=np.array([me.polygons[p.polygon_index].material_index for p in me.loop_triangles]);c=v[f].mean(1);region=(c[:,1]<-.40)&(c[:,1]>-.61)&(c[:,2]<.03)
 groups={g.index:g.name for g in ob.vertex_groups}
 for mi in np.unique(mid[region]):
  faces=f[region&(mid==mi)];ids=np.unique(faces);bones=sorted({groups[g.group] for i in ids for g in me.vertices[int(i)].groups if g.weight>.1})
  out.append({'object':ob.name,'material':me.materials[int(mi)].name,'triangles':len(faces),'bounds':np.stack([v[ids].min(0),v[ids].max(0)]).tolist(),'bones':bones})
(O/'front_ownership.json').write_text(json.dumps(out,indent=2))
for ob in list(bpy.data.objects):
 if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.world=scene.world or bpy.data.worlds.new('Diag')
s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.35,.36,.39);s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.background_type='WORLD';scene.world.color=(.1,.11,.13)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.005;cam.data.clip_end=5
def shot(name,pos,target,scale):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
shot('installed_front_before',(1,-.5,.13),(0,-.5,.022),.42)
shot('installed_front_under',(1,-.5,-.27),(0,-.5,.022),.33)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Installed_Before_Local.blend'))
