"""Requested image/model deliverable: actual Blender asset studio views."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

O=Path(__file__).resolve().parent
P=O/'Preview';P.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'RSH12_HeavyGrip_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU';scene.cycles.samples=48
scene.cycles.use_denoising=True;scene.cycles.max_bounces=5
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
parts=list(bpy.data.collections['EDITABLE_HeavyGrip_Parts'].objects)
reference=bpy.data.collections['REFERENCE_Host_DoNotExport']
reference.hide_render=False;reference.hide_viewport=False
refs=list(reference.objects)
for o in parts+refs:o.hide_set(False);o.hide_render=False
bpy.data.collections['GAME_Exports'].hide_render=True
bpy.data.collections['INTERFACE_OriginalGrip'].hide_render=True

world=bpy.data.worlds.new('HeavyGrip_StudioWorld');world.use_nodes=True
world.node_tree.nodes.clear()
bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg.outputs['Background'],out.inputs['Surface'])
bg.inputs['Color'].default_value=(.3,.31,.33,1);bg.inputs['Strength'].default_value=.45
scene.world=world
stage=bpy.data.collections.new('PREVIEW_Studio');scene.collection.children.link(stage)
def stage_object(ob):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    stage.objects.link(ob)

camera_data=bpy.data.cameras.new('Studio_Camera')
camera=bpy.data.objects.new('Studio_Camera',camera_data);stage.objects.link(camera)
camera_data.type='ORTHO';camera_data.clip_start=.001;camera_data.clip_end=100
scene.camera=camera
bpy.ops.mesh.primitive_plane_add(size=20)
floor=bpy.context.object;floor.name='Studio_Floor';stage_object(floor)
mat=bpy.data.materials.new('Studio_Gray');mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Base Color'].default_value=(.105,.12,.14,1);p.inputs['Roughness'].default_value=.77
floor.data.materials.append(mat)
specs=[((.38,-.22,.55),60,.42),((-.23,.15,.3),45,.34),((.05,.5,.45),65,.26),((.4,.1,.05),20,.3)]
lights=[]
for i,(offset,energy,size) in enumerate(specs):
    d=bpy.data.lights.new('Studio_Area_'+str(i),'AREA');d.shape='DISK'
    ob=bpy.data.objects.new(d.name,d);stage.objects.link(ob);lights.append(ob)

def render(name,objects,direction,resolution):
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
    lo=Vector(tuple(min(p[k] for p in points) for k in range(3)))
    hi=Vector(tuple(max(p[k] for p in points) for k in range(3)))
    target=(lo+hi)*.5;span=max(hi-lo)
    direction=Vector(direction).normalized()
    rotation=(-direction).to_track_quat('-Z','Y')
    right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0))
    xp=[(p-target).dot(right) for p in points];yp=[(p-target).dot(up) for p in points]
    target+=right*((min(xp)+max(xp))*.5)+up*((min(yp)+max(yp))*.5)
    camera.location=target+direction*span*3;camera.rotation_euler=rotation.to_euler()
    aspect=resolution[0]/resolution[1]
    dx=max(xp)-min(xp);dy=max(yp)-min(yp)
    camera_data.ortho_scale=(max(dx,dy*aspect) if aspect>=1 else max(dy,dx/aspect))*1.18
    floor.location.z=lo.z-.0003
    scale=span/.53
    for light,(offset,energy,size) in zip(lights,specs):
        light.location=target+Vector(offset)*scale
        light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
        light.data.energy=energy*scale*scale*.095;light.data.size=size*scale
    scene.render.resolution_x,scene.render.resolution_y=resolution
    scene.render.filepath=str(P/(name+'.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(P/(name+'.blend')))
    print('RENDER_START',name,flush=True)
    bpy.ops.render.render(write_still=True)
    print('RENDER_SAVED',name,flush=True)

render('RSH12_HeavyGrip_Mounted',parts+refs,(1,-.20,.12),(1800,1080))
reference.hide_render=True;reference.hide_viewport=True
render('RSH12_HeavyGrip_Detail',parts,(1,.65,.30),(1500,1500))
render('RSH12_HeavyGrip_Rear',parts,(.28,1,.16),(1100,1500))
(P/'preview_receipt.json').write_text(json.dumps(dict(renderer='Blender Cycles',
    source=str(O/'RSH12_HeavyGrip_Editable.blend'),
    scope='Requested design/model images; actual 3D mesh renders',
    images=['RSH12_HeavyGrip_Mounted.png','RSH12_HeavyGrip_Detail.png','RSH12_HeavyGrip_Rear.png'],
    ue_opened=False,gameplay_tested=False),indent=2),encoding='utf8')
