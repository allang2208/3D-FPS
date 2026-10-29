"""Close palm/back views, including deployment and recovery intermediates."""
import bpy,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
OUT=Path(__file__).resolve().parent
version=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=420;scene.render.resolution_y=420;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('World');scene.world.color=(.055,.065,.085)
scene.render.image_settings.file_format='PNG'
with bpy.data.libraries.load(str(OUT.parent/'Kukri20261020/Kukri_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n=='SM_Kukri']
knife=dst.objects[0];scene.collection.objects.link(knife);knife.color=(.19,.32,.44,1)
knife_points=np.array([v.co[:] for v in knife.data.vertices])*100
knife.rotation_euler=(0,0,0);knife.location=(0,0,0);knife.scale=(1,1,1)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
folder=OUT/'DetailFrames';folder.mkdir(exist_ok=True);mirror=np.array([1.,-1.,1.])
for label in ('jason','kaitlin'):
    data=np.load(OUT/f'{label}-{version}-detail.npz');vertices=data['vertices']
    mesh=bpy.data.meshes.new(label);mesh.from_pydata((vertices[0]*mirror*.01).tolist(),[],data['triangles'][:,::-1].tolist())
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);obj.color=(.59,.68,.75,1)
    for poly in mesh.polygons:poly.use_smooth=True
    isolated={}
    for side in 'rl':
        am=bpy.data.meshes.new(label+'_'+side);am.from_pydata((vertices[0]*mirror*.01).tolist(),[],data['arm_'+side][:,::-1].tolist())
        ao=bpy.data.objects.new(label+'_'+side,am);scene.collection.objects.link(ao);ao.color=obj.color;ao.hide_render=True
        for poly in am.polygons:poly.use_smooth=True
        isolated[side]=ao
    for k,t in enumerate(data['times']):
        mesh.vertices.foreach_set('co',(vertices[k]*mirror*.01).reshape(-1));mesh.update()
        m=data['blade'][k];q=Quaternion((float(m[6]),*map(float,m[3:6])))
        knife_v=np.array([tuple(q@Vector(v)) for v in knife_points])+m[:3]
        knife.data.vertices.foreach_set('co',(knife_v*mirror*.01).reshape(-1));knife.data.update()
        for side,si in [('r',0),('l',1)]:
            hand=data['hands'][k,si];along=data['longitudinal'][k,si];normal=data['normal'][k,si]
            center=hand+along*3. if side=='l' else hand+(data['elbows'][k,si]-hand)*.14
            center=Vector(center*mirror*.01)
            for view,sign in [('palm',1),('back',-1)]:
                obj.hide_render=view=='palm';ao=isolated[side];ao.hide_render=view!='palm'
                ao.data.vertices.foreach_set('co',(vertices[k]*mirror*.01).reshape(-1));ao.data.update()
                knife.hide_render=side=='l' and view=='palm'
                direction=normal*sign-along*.18
                camera.location=center+Vector(direction*mirror)
                camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
                camera.data.ortho_scale=.35 if side=='l' else .57
                scene.render.filepath=str(folder/f'{label}-{version}-{side}-{view}-{k:02d}.png')
                bpy.ops.render.render(write_still=True)
                ao.hide_render=True
    knife.hide_render=False
    for ao in isolated.values():bpy.data.objects.remove(ao,do_unlink=True)
    bpy.data.objects.remove(obj,do_unlink=True)
print('DETAIL_RENDER_COMPLETE',version)
