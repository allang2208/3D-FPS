import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True);report={};objs=[]
for key in ['BipodBase','BipodLegA','BipodLegB']:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('Before_'+key+'.fbx')),use_anim=False)
 ob=next(q for q in bpy.data.objects if q not in old and q.type=='MESH');ob.name=key;me=ob.data;me.calc_loop_triangles();v=np.array([(ob.matrix_world@q.co)[:] for q in me.vertices]);f=np.array([q.vertices[:] for q in me.loop_triangles]);m=np.array([me.polygons[q.polygon_index].material_index for q in me.loop_triangles])
 report[key]={'bounds':[v.min(0).tolist(),v.max(0).tolist()],'matrix':[list(row) for row in ob.matrix_world]};np.savez_compressed(O/(key+'.npz'),v=v,f=f,m=m);objs.append(ob)
(O/'bipod_geometry.json').write_text(json.dumps(report,indent=2));print('BIPOD_BOUNDS',json.dumps(report),flush=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1400;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.world=scene.world or bpy.data.worlds.new('Diag');s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.35,.36,.39);s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.background_type='WORLD';scene.world.color=(.1,.11,.13)
for ob in objs:ob.hide_render=ob.name!='BipodBase'
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.0001;cam.data.clip_end=1000
v=np.load(O/'BipodBase.npz')['v'];center=(v.min(0)+v.max(0))/2;extent=float(np.max(v.max(0)-v.min(0)));cam.location=Vector(center)+Vector((extent*2,0,extent*.4));cam.rotation_euler=(Vector(center)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=extent*1.3;scene.render.filepath=str(O/'bipod_base_before.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Bipod_Before.blend'))
