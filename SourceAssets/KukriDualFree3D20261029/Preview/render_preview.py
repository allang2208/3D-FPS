"""Background native-body preview of the saved first two dual slashes."""
import bpy,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=480;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('PreviewWorld');scene.world.color=(.035,.045,.065)
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
with bpy.data.libraries.load(str(ROOT/'SourceAssets/Kukri20261020/Kukri_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n=='SM_Kukri']
knife=dst.objects[0];scene.collection.objects.link(knife);knife.color=(.24,.52,.78,1)
points=np.array([v.co[:] for v in knife.data.vertices])*100
knife.rotation_euler=(0,0,0);knife.location=(0,0,0);knife.scale=(1,1,1)
left=knife.copy();left.data=knife.data.copy();scene.collection.objects.link(left);left.color=(.91,.50,.17,1)
bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,-.025));bpy.context.object.color=(.11,.13,.16,1)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
folder=OUT/'Frames';folder.mkdir(exist_ok=True);mirror=np.array([1.,-1.,1.])
def object_mesh(name,vertices,triangles,color):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata((vertices*mirror*.01).tolist(),[],triangles[:,::-1].tolist());mesh.update()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.color=color
    for poly in mesh.polygons:poly.use_smooth=True
    return obj
for role in ('Dual.Slash1','Dual.Slash2'):
    d=np.load(OUT/(role+'.npz'));v=d['vertices'];h=d['head']
    body=object_mesh('Jason',v[0],d['triangles'],(.58,.67,.75,1))
    head=object_mesh('JasonHead',h[0],d['head_triangles'],(.58,.67,.75,1))
    frames=range(len(v)) if '--layout' not in sys.argv else (0,7,17,24)
    for k in frames:
        for obj,verts in [(body,v[k]),(head,h[k])]:
            obj.data.vertices.foreach_set('co',(verts*mirror*.01).reshape(-1));obj.data.update()
        for j,blade in enumerate((knife,left)):
            m=d['blades'][k,j];q=Quaternion((float(m[6]),*map(float,m[3:6])))
            rotation=np.asarray(q.to_matrix())
            blade.data.vertices.foreach_set('co',((points@rotation.T+m[:3])*mirror*.01).reshape(-1));blade.data.update()
        for view,eye in [('front',(1.5,-6.,2.25)),('side',(-6.,-.3,2.15))]:
            camera.location=eye;camera.rotation_euler=(Vector((0,0,.98))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=2.48
            scene.render.filepath=str(folder/f'{role}-{view}-{k:03d}.png');bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(body,do_unlink=True);bpy.data.objects.remove(head,do_unlink=True)
    print('PREVIEW_RENDERED',role,flush=True)
