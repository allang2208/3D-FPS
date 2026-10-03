"""Limited source close-ups for the reported index-finger intersection."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent; BASE=O.parent
data=json.loads((BASE/'fit_input.json').read_text())
data['magazines'].update(json.loads((BASE/'FingerContactV3/extra_magazines.json').read_text()))
stage='after' if '--after' in sys.argv else 'before'
source=O if stage=='after' else BASE/'FingerContactV3'
fits=json.loads((source/'selected_grasp.json').read_text())
for gun,pose in fits.items():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    for label,verts,faces,color in [('Glove',pose['skin'],data['faces'],(.30,.46,.67,1)),
                                  ('Magazine',data['magazines'][gun]['vertices'],data['magazines'][gun]['faces'],(.52,.37,.17,1))]:
        me=bpy.data.meshes.new(label);me.from_pydata(verts,[],faces);me.update()
        ob=bpy.data.objects.new(label,me);s.collection.objects.link(ob);ob.color=color
        for p in me.polygons:p.use_smooth=True
    center=Vector(pose['joints']['index_02_l']).lerp(Vector(pose['joints']['middle_02_l']),.3)
    cam=bpy.data.objects.new('ContactCamera',bpy.data.cameras.new('ContactCamera'));s.collection.objects.link(cam);s.camera=cam
    cam.data.type='ORTHO';cam.data.ortho_scale=.15
    s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
    s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True
    s.render.resolution_x=700;s.render.resolution_y=600;s.render.resolution_percentage=100
    s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=88
    s.render.film_transparent=False
    out=O/'Diagnosis';out.mkdir(exist_ok=True)
    for view,offset in [('front',(.32,-.30,.08)),('edge',(.30,.28,.06))]:
        cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        s.render.filepath=str(out/f'{stage}_{gun}_{view}.jpg');bpy.ops.render.render(write_still=True)
