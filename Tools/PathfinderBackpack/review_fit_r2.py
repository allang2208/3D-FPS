"""Offline reference-pose contact views requested for the backpack repair."""
import bpy
import json
import math
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
inputs=read(R/'BodyInputs/manifest.json')
rows=read(R/('review_progress.json' if '--progress' in sys.argv else 'manifest.json'))['variants']
source=np.load(R/'Authored/worn_body.npz')
out=R/'Review';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'PathfinderBackpack_source.blend'))
original=next(o for o in bpy.context.scene.objects if o.type=='MESH')
pack_material=original.data.materials[0]

def material(name,color,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Roughness'].default_value=.72;bsdf.inputs['Metallic'].default_value=metal
    return m
skin=material('ReferenceBody',(.25,.29,.32))
cloth=material('ReferenceClothes',(.20,.29,.37))
fabric=material('Harness',(.16,.18,.12))
hardware=material('Hardware',(.28,.30,.32),.7)

def mesh(name,positions,faces,materials,slots=None,uv=None):
    me=bpy.data.meshes.new(name);me.from_pydata((np.asarray(positions)/100).tolist(),[],np.asarray(faces).tolist());me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob)
    for m in materials:me.materials.append(m)
    if slots is not None:
        for p,s in zip(me.polygons,slots):p.material_index=int(s)
    if uv is not None:
        tex=me.uv_layers.new(name='UVMap')
        flat=np.asarray(uv).reshape(-1,2).copy();flat[:,1]=1-flat[:,1]
        tex.data.foreach_set('uv',flat.ravel())
    for p in me.polygons:p.use_smooth=True
    return ob

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1440;scene.render.resolution_y=620;scene.render.resolution_percentage=100
scene.render.film_transparent=False
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
world=bpy.data.worlds.new('ReviewWorld');world.use_nodes=True;next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.07,.08,.10,1)
next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.6;scene.world=world
for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
for position,power,size in [((-2,-3,4),500,3),((3,0,3),400,3),((0,2,3),500,2)]:
    data=bpy.data.lights.new('Studio','AREA');data.energy=power;data.size=size
    ob=bpy.data.objects.new('Studio',data);scene.collection.objects.link(ob);ob.location=position
    ob.rotation_euler=(Vector((0,0,1.2))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',data);scene.collection.objects.link(cam)
cam.location=(0,-7,1.21);cam.rotation_euler=(Vector((0,0,1.21))-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=3.45;scene.camera=cam
for row in rows:
    # A matrix of bare, padded shirt and robe views covers each native body.
    if row['fit_profile'] not in ['bare','knit_sweater','mage_robe']:continue
    recipe=inputs['rigs'][row['rig']]
    body=read(R/'BodyInputs'/recipe['body'])
    garment=read(R/'BodyInputs'/recipe['shirts'][row['shirt']]['base']) if row['shirt'] else None
    harness=read(Path(row['source']))
    from mathutils import Quaternion
    q=row['rigid_rotation_quat'];rot=np.asarray(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
    bag=source['positions']@rot.T+row['rigid_location']
    made=[]
    for column,angle in enumerate([0.,math.pi/2,math.pi]):
        objects=[]
        for tag,data in [('Body',body),('Clothes',garment)]:
            if not data:continue
            v=np.asarray(data['positions']);f=np.asarray(data['triangles'],int)
            # Crop the unused lower legs from the contact inspection.
            f=f[np.all(v[f,2]>77,axis=1)]
            objects.append(mesh(tag,v,f[:,[0,2,1]],[skin if tag=='Body' else cloth]))
        objects.append(mesh('Pack',bag,source['triangles'],[pack_material],uv=source['uv']))
        objects.append(mesh('Harness',harness['positions'],harness['triangles'],[pack_material,hardware,fabric],harness['triangle_materials'],harness['uv']))
        for ob in objects:
            ob.rotation_euler.z=angle;ob.location.x=(column-1)*1.15
        made.extend(objects)
    scene.render.filepath=str(out/(row['profile']+'.png'));bpy.ops.render.render(write_still=True)
    for ob in made:
        me=ob.data;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(me)
print('PATHFINDER_REFERENCE_VIEWS_COMPLETE',flush=True)
