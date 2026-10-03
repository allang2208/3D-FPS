"""Source-pose close-ups for the explicitly requested grasp diagnosis."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
data=json.loads((O/'fit_input.json').read_text())
name='draft_fit' if '--draft' in sys.argv else 'grasp_fit'
fit=json.loads((O/(name+'.json')).read_text())
if '--extended' in sys.argv:fit={'A762_extended':fit['A762']}
for gun,pose in fit.items():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    for label,verts,faces,color in [('Glove',pose['skin'],data['faces'],(.30,.46,.67,1)),
                                   ('Magazine',data['magazines'][gun]['vertices'],data['magazines'][gun]['faces'],(.52,.37,.17,1))]:
        me=bpy.data.meshes.new(label);me.from_pydata(verts,[],faces);me.update()
        ob=bpy.data.objects.new(label,me);s.collection.objects.link(ob);ob.color=color
        for p in me.polygons:p.use_smooth=True
    center=sum((Vector(pose['joints'][n]) for n in ['index_02_l','middle_02_l','ring_02_l','pinky_02_l']),Vector())/4
    cam=bpy.data.objects.new('ContactCamera',bpy.data.cameras.new('ContactCamera'));s.collection.objects.link(cam);s.camera=cam
    cam.data.type='ORTHO';cam.data.ortho_scale=.24
    s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
    s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True
    s.render.resolution_x=600;s.render.resolution_y=600;s.render.resolution_percentage=100
    s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=88
    s.render.film_transparent=False
    out=O/'Diagnosis';out.mkdir(exist_ok=True)
    for view,offset in [('front',(.32,-.30,.08)),('back',(-.32,.30,.04)),('edge',(.30,.28,.06))]:
        cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        s.render.filepath=str(out/f'{name}_{gun}_{view}.jpg');bpy.ops.render.render(write_still=True)
