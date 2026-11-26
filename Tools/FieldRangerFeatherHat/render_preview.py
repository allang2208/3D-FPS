"""User-requested three-angle render of the saved Blender production model."""
import json,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Quaternion
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerFeatherHat20261021'
OUT=R/'Preview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'Exports/FieldRangerFeatherHat_Detailed.blend'))
scene=bpy.context.scene;model=bpy.data.objects['FieldRangerFeatherHat_GameLOD0']
dg=bpy.context.evaluated_depsgraph_get();evaluated=model.evaluated_get(dg)
mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=dg)
points=np.array([v.co[:] for v in mesh.vertices]);center=Vector((points.min(0)+points.max(0))*.5)
for v in mesh.vertices:v.co-=center
for ob in scene.objects:ob.hide_render=True
collection=bpy.data.collections.new('Requested_Render_Only');scene.collection.children.link(collection)
camera_data=bpy.data.cameras.new('PreviewCamera');camera_data.type='ORTHO';camera_data.ortho_scale=1.42
camera=bpy.data.objects.new('PreviewCamera',camera_data);collection.objects.link(camera);camera.location=(0,-3,.01)
camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();scene.camera=camera
target=camera.rotation_euler.to_quaternion()
views=[('01_THREE_QUARTER',(-.47,0,.035),(2.5,-2.7,1.6)),('02_FEATHER_SIDE',(0,0,.035),(3.,.3,.65)),('03_INSIDE',(.47,0,.035),(1.1,-.4,-3.))]
for name,location,direction in views:
    ob=bpy.data.objects.new(name,mesh);collection.objects.link(ob);ob.location=location
    q=(-Vector(direction)).to_track_quat('-Z','Y');ob.rotation_mode='QUATERNION';ob.rotation_quaternion=target@q.inverted()
    ob['Source']='Saved production Blender mesh and packed PBR maps'
    text=bpy.data.curves.new(name+'_Label','FONT');text.body=name.replace('01_','01  /  ').replace('02_','02  /  ').replace('03_','03  /  ').replace('_',' ');text.align_x='CENTER';text.size=.014;text.extrude=0
    label=bpy.data.objects.new(text.name,text);collection.objects.link(label);label.location=(location[0],-.05,-.17);label.rotation_euler=(math.pi/2,0,0)
    mat=bpy.data.materials.get('PreviewLabel') or bpy.data.materials.new('PreviewLabel');mat.diffuse_color=(.13,.13,.12,1);text.materials.append(mat)
for name,location,power,size in [('Key',(-.6,-1.0,1.1),35.,1.5),('Fill',(.9,-.6,.25),12.,1.4),('Rim',(.1,.45,.9),25.,1.0)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
    ob=bpy.data.objects.new(name,light);collection.objects.link(ob);ob.location=location;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('NeutralPreviewWorld');world.use_nodes=True
world.node_tree.nodes.clear();background=world.node_tree.nodes.new('ShaderNodeBackground');output=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(background.outputs[0],output.inputs['Surface'])
background.inputs[0].default_value=(.22,.215,.20,1);background.inputs[1].default_value=.22;scene.world=world
scene.render.engine='CYCLES';scene.cycles.samples=192;scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.008
scene.render.resolution_x=2400;scene.render.resolution_y=860;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.2
scene.render.filepath=str(OUT/'FieldRangerFeatherHat_ModelPreview02.png')
bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FieldRangerFeatherHat_Preview.blend'))
(OUT/'receipt.json').write_text(json.dumps(dict(source=str(R/'Exports/FieldRangerFeatherHat_Detailed.blend'),render=scene.render.filepath,views=[v[0] for v in views],size=[2400,860],renderer='Blender Cycles',engine_screenshot=False),indent=2),encoding='utf-8')
print('RANGER_HAT_PREVIEW_RENDERED',scene.render.filepath,flush=True)
