"""Render actual native skin and the existing editable Kukri, offline only."""
import bpy,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix,Quaternion
OUT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=500;scene.render.resolution_y=620;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('PreviewWorld');scene.world.color=(.055,.065,.085)
scene.render.image_settings.file_format='PNG'
with bpy.data.libraries.load(str(OUT.parent/'Kukri20261020/Kukri_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n=='SM_Kukri']
knife=dst.objects[0];scene.collection.objects.link(knife);knife.color=(.24,.29,.36,1)
knife_points=np.array([v.co[:] for v in knife.data.vertices])*100
knife.rotation_euler=(0,0,0);knife.location=(0,0,0);knife.scale=(1,1,1)
bpy.ops.object.camera_add(location=(2.6,-6.8,2.7));camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,1.05))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=2.3;scene.camera=camera
manifest=json.loads((OUT/'preview-manifest.json').read_text());folder=OUT/'NativePreview';folder.mkdir(exist_ok=True)
mirror=np.array([1.,-1.,1.])
for label in ('jason','kaitlin'):
    data=np.load(OUT/(label+'-preview.npz'));vertices=data['vertices'];triangles=data['triangles'];mounts=data['blade']
    mesh=bpy.data.meshes.new(label);mesh.from_pydata((vertices[0]*mirror*.01).tolist(),[],triangles[:,::-1].tolist());mesh.update()
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);obj.color=(.57,.66,.74,1)
    for poly in mesh.polygons:poly.use_smooth=True
    for e in [e for e in manifest['samples'] if e['body']==label]:
        k=e['index'];mesh.vertices.foreach_set('co',(vertices[k]*mirror*.01).reshape(-1));mesh.update()
        m=mounts[k];q=Quaternion((float(m[6]),*map(float,m[3:6])))
        knife_v=np.array([tuple(q@Vector(v)) for v in knife_points])+m[:3]
        knife.data.vertices.foreach_set('co',(knife_v*mirror*.01).reshape(-1));knife.data.update()
        name=f'{label}_{e["version"]}_{k:02d}.png';e['file']=name
        scene.render.filepath=str(folder/name);bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
(OUT/'preview-manifest.json').write_text(json.dumps(manifest,indent=2))
print('NATIVE_PREVIEW_RENDERED')
