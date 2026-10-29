"""Diagnostic rendering of the native Jason presentation and current shirts."""
import bpy,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
OUT=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:];version=args[0] if args else 'after'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.color=(.05,.06,.08)
scene.render.image_settings.file_format='PNG'
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
folder=OUT/'OutfitFrames';folder.mkdir(exist_ok=True);mirror=np.array([1.,-1.,1.])
for item in ('ue_st6_sleeves','ue_field_sweater_charcoal','ue_chainmail_shirt'):
    d=np.load(OUT/f'outfit-{version}-{item}.npz');objects=[]
    for key,color in [('body',(.72,.42,.34,1)),('cloth',(.21,.39,.58,1))]:
        vertices=d[key];tri=d[key+'_triangles'];mesh=bpy.data.meshes.new(key)
        mesh.from_pydata((vertices[0]*mirror*.01).tolist(),[],tri[:,::-1].tolist());mesh.update()
        obj=bpy.data.objects.new(key,mesh);scene.collection.objects.link(obj);obj.color=color
        for poly in mesh.polygons:poly.use_smooth=True
        objects.append(obj)
    for k in (1,2,4,5):
        for key,obj in zip(('body','cloth'),objects):
            obj.data.vertices.foreach_set('co',(d[key][k]*mirror*.01).reshape(-1));obj.data.update()
        for view,eye in [('front',(0,-5,1.8)),('quarter',(-3.3,-4,1.8))]:
            camera.location=eye;camera.rotation_euler=(Vector((0,0,1.05))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.9
            scene.render.filepath=str(folder/f'{version}-{item}-{view}-{k:02d}.png');bpy.ops.render.render(write_still=True)
    for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
print('OUTFIT_RENDERED',version)
