"""Attach baked PBR maps and produce the three in-menu PNG assets."""
import bpy,math,shutil,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;ROOT=P.parents[1]
bpy.context.preferences.filepaths.save_version=0
for key in ['shock_wrap','swift_grip','long_twohand']:
    out=P/key;name='SM_FrostGrip_'+key
    bpy.ops.wm.open_mainfile(filepath=str(out/(name+'_Editable.blend')))
    obj=bpy.data.objects[name];scene=bpy.context.scene
    leather=next(m for m in obj.data.materials if m.name.startswith('M_Grip_Leather'))
    n=leather.node_tree.nodes;l=leather.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    for k,field in [('base_color','Base Color'),('roughness','Roughness'),('normal','Normal')]:
        im=bpy.data.images.load(str(P/'Textures'/(k+'.png')),check_existing=True)
        if k!='base_color':im.colorspace_settings.name='Non-Color'
        tex=n.new('ShaderNodeTexImage');tex.image=im
        if k=='normal':
            normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs[field])
        else:l.new(tex.outputs['Color'],bs.inputs[field])
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'_Editable.blend')))
    scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX'
    scene.world=bpy.data.worlds.new('Grip UI studio');scene.world.use_nodes=True
    bg=next((x for x in scene.world.node_tree.nodes if x.type=='BACKGROUND'),None)
    if not bg:
        bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');wout=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],wout.inputs[0])
    bg.inputs[0].default_value=(.16,.16,.16,1);bg.inputs[1].default_value=.45
    center=Vector((0,0,sum((min(v.co.z for v in obj.data.vertices),max(v.co.z for v in obj.data.vertices)))/2))
    camera=bpy.data.objects.new('Grip option camera',bpy.data.cameras.new('Grip option camera'));scene.collection.objects.link(camera)
    camera.location=center+Vector((.055,-.32,.012));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=(max(v.co.z for v in obj.data.vertices)-min(v.co.z for v in obj.data.vertices))/.84;camera.data.clip_start=.001;scene.camera=camera
    for nm,loc,energy,size in [('Key',(-.12,-.16,.10),12,.12),('Fill',(.15,-.06,.01),4,.14),('Rim',(.05,.09,.08),8,.1)]:
        o=bpy.data.objects.new(nm,bpy.data.lights.new(nm,'AREA'));scene.collection.objects.link(o);o.location=center+Vector(loc);o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    for o in scene.objects:o.hide_render=o.type not in {'LIGHT','CAMERA'} and o!=obj
    scene.render.filepath=str(out/'grip_icon.png');bpy.ops.wm.save_as_mainfile(filepath=str(out/'GripIcon_Editable.blend'));bpy.ops.render.render(write_still=True)
    target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/('ue_frost_crystal_sword_grip_'+key+'.png')
    if target.exists() and not (P/'Before'/target.name).exists():shutil.copy2(target,P/'Before'/target.name)
    shutil.copy2(out/'grip_icon.png',target)
    (out/'icon_authoring.json').write_text(json.dumps({'source':name,'destination':str(target),'size':[1024,1024],'purpose':'gunsmith UI icon production; not an acceptance render'},indent=2))
    print('GRIP_PBR_AND_ICON_WRITTEN '+key,flush=True)
