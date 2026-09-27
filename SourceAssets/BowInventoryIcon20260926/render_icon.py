"""Produce the bow's catalog/equipment icon from its current installed models.

Only an independent icon scene and PNG are authored. No weapon meshes, imported
assets, materials, animation, editor session or gameplay state are modified.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix

ROOT=Path('D:/FPS3D/FPSGAME');P=Path(__file__).parent
WOOD=ROOT/'SourceAssets/DarkBow20260925/WoodLongbow20260925'
SIGHT=ROOT/'SourceAssets/BowWoodSight20260926'
bow=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8-sig'))['bow_dark']
width=max(256,round(320*bow['grid_w']/max(1,bow['grid_h'])));height=320;FILL=.91
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.

def append_mesh(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        if name not in source.objects:raise RuntimeError('Missing current model '+name)
        target.objects=[name]
    obj=target.objects[0];scene.collection.objects.link(obj)
    obj.hide_render=False;obj.hide_viewport=False;obj.hide_set(False)
    # Source files use two unit conventions; normalize only the icon copies.
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    extent=max(max(v[i] for v in points)-min(v[i] for v in points) for i in range(3))
    factor=.01 if extent>5 else 1.
    transform=Matrix.Scale(factor,4)@obj.matrix_world
    obj.data=obj.data.copy();obj.data.transform(transform);obj.matrix_world=Matrix.Identity(4)
    return obj

body=append_mesh(WOOD/'WoodLongbow_Editable.blend','SM_DarkBow_WoodLongbow')
sight=append_mesh(SIGHT/'Bow_CarvedWoodSight.blend','SM_Bow_CarvedWoodSight')

def texture(nodes,filename,normal=False):
    n=nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(WOOD/'Textures'/filename),check_existing=True)
    n.image.colorspace_settings.name='Non-Color' if normal else 'sRGB'
    return n

def wood_material(name,carved=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
    base=texture(nodes,'Image_0.png');orm=texture(nodes,'Image_1.png',True);normal=texture(nodes,'Image_2.png',True)
    links.new(base.outputs['Color'],bsdf.inputs['Base Color'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(orm.outputs['Color'],split.inputs['Color'])
    if carved:
        rough=nodes.new('ShaderNodeMath');rough.operation='MAXIMUM';rough.inputs[1].default_value=.42
        links.new(split.outputs['Green'],rough.inputs[0]);links.new(rough.outputs[0],bsdf.inputs['Roughness'])
        bsdf.inputs['Metallic'].default_value=0
    else:
        links.new(split.outputs['Green'],bsdf.inputs['Roughness']);links.new(split.outputs['Blue'],bsdf.inputs['Metallic'])
    nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.55 if carved else 1.
    links.new(normal.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
    return mat

body.data.materials.clear();body.data.materials.append(wood_material('Icon_CurrentLongbowPBR'))
for face in body.data.polygons:face.material_index=0
wood=wood_material('Icon_CurrentCarvedWoodPBR',True)
for i,mat in enumerate(sight.data.materials):
    if mat.name.startswith('CarvedBowWood'):sight.data.materials[i]=wood
    elif mat.name.startswith('WaxedLinen'):mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.84
    # WaxedLinen and PaleWoodInlay already carry the same constants used by
    # the V12 UE importer. They have no image-dependent shader conversion.

def ue_cm(key):
    p=[float(v) for v in bow[key].split(',')];return Vector((p[0],-p[1],p[2]))*.01

# The unloaded catalog pose uses the same rest string endpoints as gameplay.
# No extra arrow or hands are shown as part of the equipment itself.
string_mat=bpy.data.materials.new('Icon_BowString');string_mat.use_nodes=True
shader=string_mat.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value=(.035,.026,.016,1);shader.inputs['Roughness'].default_value=.74
subjects=[body,sight]
for key in ['nock_upper_cm','nock_lower_cm']:
    a,b=ue_cm(key),ue_cm('brace_nock_cm');d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=bow['bow_part_string_radius_cm']*.01,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.name='Icon_String_'+key;o.rotation_mode='QUATERNION'
    o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized());o.data.materials.append(string_mat)
    for f in o.data.polygons:f.use_smooth=True
    subjects.append(o)

# Lie the bow's long axis horizontally to match its 4x2 authored footprint
# and the equipment card. This is a real 3D rotation, not a mirrored bitmap.
turn=Matrix.Rotation(-math.pi/2,4,'Y')
for obj in subjects:obj.matrix_world=turn@obj.matrix_world
bpy.context.view_layer.update()

data=bpy.data.cameras.new('BowEquipmentCamera');data.type='ORTHO';data.clip_start=.01;data.clip_end=100
cam=bpy.data.objects.new('BowEquipmentCamera',data);scene.collection.objects.link(cam);scene.camera=cam
cam.location=(0,3,0);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
rotation=cam.matrix_world.to_3x3();right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0));back=rotation@Vector((0,0,1))
points=[o.matrix_world@v.co for o in subjects for v in o.data.vertices]
axes=[right,up,back];low=[min(p.dot(a) for p in points) for a in axes];high=[max(p.dot(a) for p in points) for a in axes]
center=sum((a*((lo+hi)*.5) for a,lo,hi in zip(axes,low,high)),Vector())
cam.location=center+back*3
data.ortho_scale=max(high[0]-low[0],(high[1]-low[1])*width/height)/FILL

def light(name,offset,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
    ob.location=center+Vector(offset);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()

light('NeutralKey',(-1,1.4,1.5),55,2)
light('SoftFill',(1,1.3,.2),30,1.5)
light('Edge',(0,-1,1.2),45,1)
world=bpy.data.worlds.new('NeutralTransparentStudio');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.30,.30,.30,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=96;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
scene.render.resolution_x=width*2;scene.render.resolution_y=height*2;scene.render.resolution_percentage=100
scene.render.use_compositing=False;scene.render.use_sequencer=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.filepath=str(P/'bow_dark_2x.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_EquipmentIcon.blend'))
bpy.ops.render.render(write_still=True)
(P/'authoring.json').write_text(json.dumps({'definition':'bow_dark','catalog_size':[width,height],
    'grid':[bow['grid_w'],bow['grid_h']],'fill':FILL,'background':'transparent','composition':'horizontal long axis, orthographic side view',
    'sources':[str(WOOD/'WoodLongbow_Editable.blend'),str(SIGHT/'Bow_CarvedWoodSight.blend')],
    'runtime_meshes':[bow['bow_part_riser_mesh'],bow['bow_part_sight_mesh']],
    'material_source':'current longbow texture set and WoodSightV12 material constants',
    'string_endpoints_cm':{k:bow[k] for k in ['nock_upper_cm','nock_lower_cm','brace_nock_cm']},
    'render':'catalog asset production only','gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_EQUIPMENT_ICON_RENDERED',flush=True)
