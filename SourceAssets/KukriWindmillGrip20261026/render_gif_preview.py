"""Background Blender preview: compressed skin, world turn and locked heading."""
import bpy,json
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
OUT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=520;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('PreviewWorld');scene.world.color=(.055,.065,.085)
scene.render.image_settings.file_format='PNG'
with bpy.data.libraries.load(str(OUT.parent/'Kukri20261020/Kukri_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n=='SM_Kukri']
knife=dst.objects[0];scene.collection.objects.link(knife);knife.color=(.19,.32,.44,1)
knife_points=np.array([v.co[:] for v in knife.data.vertices])*100
knife.rotation_euler=(0,0,0);knife.location=(0,0,0);knife.scale=(1,1,1)
bpy.ops.mesh.primitive_plane_add(size=7,location=(0,0,-.025))
floor=bpy.context.object;floor.color=(.14,.16,.19,1)
for axis in (0,1):
    for k in range(-4,5):
        bpy.ops.mesh.primitive_cube_add(size=1,location=((k*.5,0,-.024) if axis==0 else (0,k*.5,-.024)))
        obj=bpy.context.object;obj.scale=(.004,4,.001) if axis==0 else (4,.004,.001)
        obj.color=(.21,.23,.27,1)
bpy.ops.object.camera_add(location=(2.7,-6.8,2.7));camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=2.7;scene.camera=camera
folder=OUT/'GifFrames';folder.mkdir(exist_ok=True)
mirror=np.array([1.,-1.,1.])
for label in ('jason','kaitlin'):
    camera.location=(2.7,-6.8,2.7)
    camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=2.7
    data=np.load(OUT/(label+'-gif-preview.npz'))
    vertices=data['vertices'];triangles=data['triangles'];mounts=data['blade']
    mesh=bpy.data.meshes.new(label);mesh.from_pydata((vertices[0]*mirror*.01).tolist(),[],triangles[:,::-1].tolist());mesh.update()
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);obj.color=(.59,.68,.75,1)
    for poly in mesh.polygons:poly.use_smooth=True
    for k in range(len(vertices)):
        m=mounts[k];q=Quaternion((float(m[6]),*map(float,m[3:6])))
        knife_v=np.array([tuple(q@Vector(v)) for v in knife_points])+m[:3]
        for view in ('world','locked'):
            yaw=np.radians(data['yaw'][k] if view=='world' else 0.)
            rot=np.array([[np.cos(yaw),-np.sin(yaw),0],[np.sin(yaw),np.cos(yaw),0],[0,0,1]])
            mesh.vertices.foreach_set('co',((vertices[k]@rot.T)*mirror*.01).reshape(-1));mesh.update()
            knife.data.vertices.foreach_set('co',((knife_v@rot.T)*mirror*.01).reshape(-1));knife.data.update()
            scene.render.filepath=str(folder/f'{label}_{view}_{k:03d}.png')
            bpy.ops.render.render(write_still=True)
    for k in [int(round(u*(len(vertices)-1))) for u in (.15,.29,.43,.60,.73,.88)]:
        m=mounts[k];q=Quaternion((float(m[6]),*map(float,m[3:6])))
        knife_v=np.array([tuple(q@Vector(v)) for v in knife_points])+m[:3]
        mesh.vertices.foreach_set('co',(vertices[k]*mirror*.01).reshape(-1));mesh.update()
        knife.data.vertices.foreach_set('co',(knife_v*mirror*.01).reshape(-1));knife.data.update()
        for hand,side in enumerate(('r','l')):
            center=Vector(data['hands'][k,hand]*mirror*.01)
            camera.location=center+Vector((-1.5 if side=='r' else 1.5,-2.,1.))
            camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            camera.data.ortho_scale=.75
            scene.render.filepath=str(folder/f'{label}_hand_{side}_{k:03d}.png')
            bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
print('V16_GIF_RENDER_COMPLETE',flush=True)
