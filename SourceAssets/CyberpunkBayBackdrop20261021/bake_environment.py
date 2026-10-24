"""Bake the approved panorama's spherical extension into six native cube faces.
This is production texture authoring, not a gameplay/acceptance render.
"""
from pathlib import Path
import json, math, hashlib
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Authored'
FACES=OUT/'CubeFaces'
FACES.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'T_CyberpunkBayNight_Environment_V01.png'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=4
scene.cycles.use_denoising=False
scene.cycles.max_bounces=0
scene.render.resolution_x=1024
scene.render.resolution_y=1024
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='8'
scene.render.film_transparent=False
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
scene.view_settings.exposure=0
scene.view_settings.gamma=1
scene.world=bpy.data.worlds.new('BlackOutsideSourceSphere')
scene.world.color=(0,0,0)

# Explicit latitude/longitude UVs avoid ambiguity in environment-texture axes.
# u=.5 faces Blender +Y, screen-right is +X, v=1 is zenith.
verts=[]; faces=[]; coords=[]
nu,nv=256,128
for j in range(nv+1):
    v=j/nv; phi=(v-.5)*math.pi
    for i in range(nu+1):
        u=i/nu; theta=(u-.5)*2*math.pi
        verts.append((1000*math.sin(theta)*math.cos(phi),
                      1000*math.cos(theta)*math.cos(phi),1000*math.sin(phi)))
        coords.append((u,v))
for j in range(nv):
    for i in range(nu):
        a=j*(nu+1)+i
        faces.append((a,a+1,a+nu+2,a+nu+1))
me=bpy.data.meshes.new('BaySphericalProjection')
me.from_pydata(verts,[],faces);me.update()
uv=me.uv_layers.new(name='EnvironmentUV')
for poly in me.polygons:
    for li in poly.loop_indices:uv.data[li].uv=coords[me.loops[li].vertex_index]
ob=bpy.data.objects.new('BaySphericalProjection',me);scene.collection.objects.link(ob)
mat=bpy.data.materials.new('BaySourceEmission');mat.use_nodes=True
n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
output=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission')
tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SOURCE))
tex.image.colorspace_settings.name='sRGB';tex.interpolation='Linear';tex.extension='REPEAT'
tex.image.pack()
l.new(tex.outputs['Color'],em.inputs['Color']);l.new(em.outputs[0],output.inputs['Surface'])
me.materials.append(mat)

camera=bpy.data.cameras.new('Cubemap capture');camera.type='PERSP'
camera.lens=18;camera.sensor_width=36;camera.clip_end=2000
cam=bpy.data.objects.new('Cubemap capture',camera);scene.collection.objects.link(cam)
scene.camera=cam
views=[('PX',(1,0,0),(0,0,1)),('NX',(-1,0,0),(0,0,1)),
       ('PY',(0,0,1),(0,-1,0)),('NY',(0,0,-1),(0,1,0)),
       ('PZ',(0,1,0),(0,0,1)),('NZ',(0,-1,0),(0,0,1))]
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CyberpunkBayEnvironment.blend'))
report=dict(stage='baking',source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            source_dimensions=list(tex.image.size),resolution=1024,faces=[],
            production_texture_bake=True,acceptance_rendered=False,game_run=False)
def record():(ROOT/'bake-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
record()
for name,forward,up in views:
    f=Vector(forward);up=Vector(up);right=f.cross(up)
    cam.rotation_euler=Matrix((right,up,-f)).transposed().to_euler()
    scene.render.filepath=str(FACES/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    report['faces'].append(dict(name=name,file=scene.render.filepath,forward=list(f),up=list(up)))
    record()
    print('BAY_CUBE_FACE_SAVED',name,flush=True)
report['stage']='six_faces_baked';record()
