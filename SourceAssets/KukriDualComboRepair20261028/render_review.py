"""Render real skinned body and both knives for the requested diagnostic."""
import bpy,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
OUT=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
version=args[0] if args else 'before'
labels=args[1:] if len(args)>1 else ['jason','kaitlin']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=480;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.color=(.05,.06,.08)
scene.render.image_settings.file_format='PNG'
with bpy.data.libraries.load(str(OUT.parent/'Kukri20261020/Kukri_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n=='SM_Kukri']
knife=dst.objects[0];scene.collection.objects.link(knife);knife.color=(.25,.43,.55,1)
points=np.array([v.co[:] for v in knife.data.vertices])*100
knife.rotation_euler=(0,0,0);knife.location=(0,0,0);knife.scale=(1,1,1)
left=knife.copy();left.data=knife.data.copy();scene.collection.objects.link(left)
bpy.ops.mesh.primitive_plane_add(size=7,location=(0,0,-.025));bpy.context.object.color=(.14,.16,.18,1)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
folder=OUT/'ReviewFrames';folder.mkdir(exist_ok=True);mirror=np.array([1.,-1.,1.])
for label in labels:
    d=np.load(OUT/f'{label}-{version}-review.npz');v=d['vertices'];tri=d['triangles']
    mesh=bpy.data.meshes.new(label);mesh.from_pydata((v[0]*mirror*.01).tolist(),[],tri[:,::-1].tolist());mesh.update()
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);obj.color=(.62,.70,.74,1)
    for poly in mesh.polygons:poly.use_smooth=True
    for k in range(len(v)):
        mesh.vertices.foreach_set('co',(v[k]*mirror*.01).reshape(-1));mesh.update()
        for j,blade in enumerate((knife,left)):
            m=d['blades'][k,j];q=Quaternion((float(m[6]),*map(float,m[3:6])))
            blade.data.vertices.foreach_set('co',((np.array([tuple(q@Vector(p)) for p in points])+m[:3])*mirror*.01).reshape(-1));blade.data.update()
        for view,eye,focus,scale in [('front',(0,-5.,2.3),(0,0,.95),2.55),('side',(-5,-.25,2.0),(0,0,.95),2.4)]:
            camera.location=eye;camera.rotation_euler=(Vector(focus)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
            scene.render.filepath=str(folder/f'{label}-{version}-{view}-{k:02d}.png');bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
print('DUAL_REVIEW_RENDERED',version)
