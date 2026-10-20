import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;suffix='_'+sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '';data=json.loads((O/('charge_scene'+suffix+'.json')).read_text())
for variant,d in data.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=900;scene.render.resolution_y=800;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new('World');scene.world.color=(.18,.18,.18)
 scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
 for kind,color in [('hand',(.68,.43,.29,1)),('gun',(.16,.18,.21,1))]:
  mesh=bpy.data.meshes.new(kind);mesh.from_pydata([[x*.01 for x in v] for v in d[kind+'_vertices']],[],d[kind+'_faces']);mesh.update()
  obj=bpy.data.objects.new(kind,mesh);scene.collection.objects.link(obj);mat=bpy.data.materials.new(kind);mat.diffuse_color=color;mesh.materials.append(mat)
  for p in mesh.polygons:p.use_smooth=kind=='hand'
 camera=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(cam);scene.camera=cam;camera.type='ORTHO';camera.ortho_scale=.35;camera.clip_start=.001
 focus=Vector(data['after']['focus'])*.01;up=Vector((0,0,1))
 side=(Vector(data['after']['hand_center'])-Vector(data['after']['focus'])).normalized()
 for label,direction in [('side',side),('above',side+up*1.5),('reverse',-side+up*.7)]:
  direction.normalize();forward=-direction;right=forward.cross(up).normalized();camup=right.cross(forward).normalized()
  cam.location=focus+direction;cam.rotation_euler=Matrix((right,camup,-forward)).transposed().to_euler()
  scene.render.filepath=str(O/(variant+'_'+label+suffix+'.png'));bpy.ops.render.render(write_still=True)
