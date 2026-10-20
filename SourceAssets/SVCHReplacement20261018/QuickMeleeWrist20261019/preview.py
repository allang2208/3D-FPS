"""Render actual saved V9-weighted candidate poses, with neutral materials."""
from pathlib import Path
import sys,json,gzip
import bpy
import numpy as np
from mathutils import Vector
OUT=Path(__file__).resolve().parent
data=json.load(gzip.open(OUT/'preview-meshes.json.gz','rt'))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1400;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('NeutralStudio');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.17,.19,.23,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.6
scene.view_settings.view_transform='AgX'

def material(name,color,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=.48;bs.inputs['Metallic'].default_value=metal
    return m
skinmat=material('V9 neutral surface',(.58,.32,.19))
gunmat=material('Weapon neutral surface',(.045,.055,.07),.5)

def make_mesh(label,verts,tris,mat):
    mesh=bpy.data.meshes.new(label);mesh.from_pydata(verts,[],tris);mesh.update()
    ob=bpy.data.objects.new(label,mesh);scene.collection.objects.link(ob);mesh.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
    return ob

# Side-by-side poses at identical world positions translated apart for comparison.
frame=68
for column,key in enumerate(('before','after')):
    offset=np.array([column*90.,0.,0.])
    skin_vertices=np.asarray(data[key]['skin'])*[1,-1,1]+offset
    make_mesh(key+' NativeV9',skin_vertices.tolist(),[list(reversed(t)) for t in data['skin_triangles']],skinmat)
    vv=np.asarray(data[key]['gun'])*[1,-1,1]+offset
    make_mesh(key+' SVCH',vv.tolist(),[list(reversed(t)) for t in data['gun_triangles']],gunmat)
    font=bpy.data.curves.new(key,'FONT');font.body=key.upper()+' / 0.567 s';font.size=4
    label=bpy.data.objects.new(key+' label',font);scene.collection.objects.link(label)
    label.location=(column*90.-15,-35,35);label.rotation_euler=(np.pi/2,0,0)

target=Vector((45,8,-2))
camera_data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camera_data);scene.collection.objects.link(camera)
camera.location=(45,-155,35);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=180;camera_data.clip_end=1000;scene.camera=camera
for name,pos,energy,size in [('Key',(50,70,100),180000,70),('Fill',(-90,-20,50),100000,65)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'wrist-comparison.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SVCH_QuickMelee_SurfaceReview.blend'))
bpy.ops.render.render(write_still=True)
