import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;d=json.loads((O/'contact_scene.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.world=bpy.data.worlds.new('ContactWorld')
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD';scene.world.color=(.15,.15,.15)
for name,vertices,faces,color in [('V9',d['skin_vertices'],d['skin_triangles'],(.67,.43,.29,1)),('Magazine',d['mag_vertices'],d['mag_triangles'],(.13,.16,.20,1))]:
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([[x*.01 for x in p] for p in vertices],[],faces);mesh.update()
 obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
 mat=bpy.data.materials.new(name);mat.diffuse_color=color;mesh.materials.append(mat)
 for polygon in mesh.polygons:polygon.use_smooth=name=='V9'
camdata=bpy.data.cameras.new('ContactCamera');cam=bpy.data.objects.new('ContactCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';camdata.ortho_scale=.30;camdata.clip_start=.001
axes=Matrix(d['axes']);up=axes.col[0];wide=axes.col[1];thin=axes.col[2];focus=Vector(d['focus'])*.01
for label,side in [('palm',thin+wide*.35),('back',-thin+wide*.35),('front',wide+thin*.25),('rear',-wide-thin*.25)]:
 side.normalize();forward=-side;right=forward.cross(up).normalized();camup=right.cross(forward).normalized()
 cam.location=focus+side;cam.rotation_euler=Matrix((right,camup,-forward)).transposed().to_euler()
 scene.render.filepath=str(O/('contact_'+label+'.png'));bpy.ops.render.render(write_still=True)
