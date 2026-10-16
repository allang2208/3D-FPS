"""Render real fitted model geometry as the shape reference for framed icons."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;P=O.parents[1]
sys.path.insert(0,r'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
sources={'shotgun_duckbill':'Super90Duckbill20261016/ShotgunDuckbill01_Editable.blend'}
(O/'References').mkdir(exist_ok=True)
rows=[]
for key,relative in sources.items():
    source=P/'SourceAssets'/relative
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version=0
    parts=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.convert(target='MESH');bpy.ops.object.join()
    obj=bpy.context.object
    obj.data.transform(obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    for other in list(bpy.context.scene.objects):
        if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
    apply_grayscale([obj])
    lo=Vector([min(v.co[i] for v in obj.data.vertices) for i in range(3)])
    hi=Vector([max(v.co[i] for v in obj.data.vertices) for i in range(3)])
    obj.data.transform(Matrix.Scale(2.4/max(hi-lo),4)@Matrix.Translation(-(hi+lo)*.5))
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    neutral_output(s)
    s.world=bpy.data.worlds.new('Neutral reference studio');s.world.use_nodes=True
    nodes=s.world.node_tree.nodes;nodes.clear()
    bg=nodes.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(1,1,1,1);bg.inputs['Strength'].default_value=.35
    out=nodes.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs[0],out.inputs['Surface'])
    data=bpy.data.cameras.new('Level front-left icon camera');cam=bpy.data.objects.new('Camera',data);s.collection.objects.link(cam)
    cam.location=(2.4,4,1.6);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=3.2;s.camera=cam
    for location,energy,size in [((2,3,4),430,4),((-3,2,1),180,3),((1,-2,2),220,3)]:
        data=bpy.data.lights.new('Softbox','AREA');data.energy=energy;data.size=size
        light=bpy.data.objects.new('Softbox',data);s.collection.objects.link(light);light.location=location
        light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
    output=O/'References'/f'{key}_actual_model.png';s.render.filepath=str(output)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'References'/f'{key}_reference.blend'))
    bpy.ops.render.render(write_still=True)
    rows.append({'id':key,'source':str(source),'reference':str(output),'forward':'+X projects left','up':'+Z','camera_eye':[2.4,4,1.6],'resolution':[1024,1024]})
(O/'references.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('SHOTGUN_ICON_SHAPE_REFERENCES_SAVED',flush=True)
