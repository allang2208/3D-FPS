"""Scoped offline before/after culling and wrist coverage inspection."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector

O=Path(__file__).parent; R=O.parents[1]
OUT=O/'Review';OUT.mkdir(exist_ok=True)
profile='M4'
skin=json.loads((O/'Read/M4_2d7cb8ab.json').read_text())
before=json.loads((O/'Before/M4_ue_hardknuckle_gloves.json').read_text())
after=json.loads((O/'Authored/M4_ue_hardknuckle_gloves.json').read_text())
texture=R/'SourceAssets/BenelliM4Super9020261006/Original/Source/textures/glove_hardknuckle_Base_color.png'
C=np.array([.01,-.01,.01]) # reflection from UE to Blender preserves the UE front face
w=np.array(skin['bones']['hand_r']['position'])
axis=np.array(skin['bones']['lowerarm_r']['position'])-w;axis/=np.linalg.norm(axis)
width=np.array(skin['bones']['index_01_r']['position'])-skin['bones']['pinky_01_r']['position'];width-=axis*np.dot(axis,width);width/=np.linalg.norm(width)
back=np.cross(axis,width)

def make_mesh(name,d,material,skin_only=False,bend=0):
    p=np.array(d['positions']);f=np.array(d['triangles'])
    if bend:
        rot=np.array([[0,-width[2],width[1]],[width[2],0,-width[0]],[-width[1],width[0],0]])
        rot=np.eye(3)+math.sin(bend)*rot+(1-math.cos(bend))*(rot@rot)
        related={n for n in skin['bones'] if n.endswith('_r') and (n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')))}
        factors=np.array([sum(v for n,v in ws.items() if n in related) for ws in d['weights']])
        p+=( (p-w)@rot.T+w-p)*factors[:,None]
    keep=[i for i,tri in enumerate(f) if np.mean(p[tri],axis=0)[0]>20 and (not skin_only or d['triangle_materials'][i]!=2)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata((p*C).tolist(),[],f[keep].tolist());mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='UVMap')
    for polygon,fi in zip(mesh.polygons,keep):
        polygon.use_smooth=True
        for li,uv in zip(polygon.loop_indices,d['uv'][fi]):layer.data[li].uv=(uv[0],1-uv[1])
    return obj

bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
def material(name,color,textured=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nt=mat.node_tree;b=nt.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=.8
    if textured:
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(texture));nt.links.new(tex.outputs['Color'],b.inputs['Base Color'])
    geo=nt.nodes.new('ShaderNodeNewGeometry');mix=nt.nodes.new('ShaderNodeMixShader');trans=nt.nodes.new('ShaderNodeBsdfTransparent')
    nt.links.new(geo.outputs['Backfacing'],mix.inputs[0]);nt.links.new(b.outputs[0],mix.inputs[1]);nt.links.new(trans.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],nt.nodes['Material Output'].inputs['Surface'])
    return mat
glove_material=material('Original glove atlas',(.1,.1,.1),True)
skin_material=material('Visible native skin',(.53,.32,.2))
cam_data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cam_data);sc.collection.objects.link(cam);sc.camera=cam;cam_data.type='ORTHO';cam_data.ortho_scale=.19
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.render.resolution_x=640;sc.render.resolution_y=640;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('World');sc.world.color=(.3,.3,.3);sc.render.film_transparent=False
for i,direction in enumerate((back*30+axis*10,width*25-back*15)):
    ld=bpy.data.lights.new('Area'+str(i),'AREA');ld.energy=35 if i==0 else 20;ld.size=.3
    lo=bpy.data.objects.new(ld.name,ld);sc.collection.objects.link(lo);lo.location=(w+direction)*C;lo.rotation_euler=(Vector(w*C)-lo.location).to_track_quat('-Z','Y').to_euler()
for label,d in (('before',before),('after',after)):
    for view,bend,eyevec in (('wrist',0,back*26+axis*10),('flex',math.radians(40),back*26-axis*3)):
        a=make_mesh('Glove',d,glove_material,bend=bend);b=make_mesh('Skin',skin,skin_material,True,bend)
        target=w+axis*.5
        cam.location=(w+eyevec)*C;cam.rotation_euler=(Vector(target*C)-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=str(OUT/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
        if label=='after' and view=='wrist':bpy.ops.wm.save_as_mainfile(filepath=str(O/'HardKnuckle_M4_Repair.blend'))
        bpy.data.objects.remove(a,do_unlink=True);bpy.data.objects.remove(b,do_unlink=True)
print('HARDKNUCKLE_SCOPED_REVIEW_RENDERED')
