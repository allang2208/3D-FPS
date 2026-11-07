"""Bind the packed PBR maps, export the portable GLB and photograph the material."""
from pathlib import Path
import math, tempfile
import bpy
from mathutils import Vector

out=Path(__file__).resolve().parents[1]
work=Path(tempfile.gettempdir())/'M24MeshyCarbon1105124237_finish'
bpy.ops.wm.open_mainfile(filepath=str(work/'prepared.blend'))
obj=bpy.context.active_object
mesh=obj.data
mat=bpy.data.materials.new('Xuanji | carbon twill, cheek, recoil rubber, satin neck')
mat.use_nodes=True
nodes=mat.node_tree.nodes
link=mat.node_tree.links.new
bsdf=nodes.get('Principled BSDF')
bsdf.location=(380,180)
nodes.get('Material Output').location=(740,180)
def texture(kind,location,space):
    p=out/'Textures'/('T_Xuanji_'+kind+'_4K.png')
    image=bpy.data.images.load(str(p))
    image.colorspace_settings.name=space
    t=nodes.new('ShaderNodeTexImage')
    t.label=kind+'  /  4096'
    t.image=image
    t.location=location
    t.width=250
    image.pack()
    return t
base=texture('BaseColor',(-560,460),'sRGB')
orm=texture('ORM',(-560,140),'Non-Color')
normal=texture('NormalGL',(-560,-220),'Non-Color')
sep=nodes.new('ShaderNodeSeparateColor');sep.location=(-210,100)
link(orm.outputs['Color'],sep.inputs['Color'])
link(base.outputs['Color'],bsdf.inputs['Base Color'])
link(sep.outputs['Green'],bsdf.inputs['Roughness'])
link(sep.outputs['Blue'],bsdf.inputs['Metallic'])
ng=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
ng.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
occ=nodes.new('ShaderNodeGroup');occ.node_tree=ng;occ.location=(90,-60)
link(sep.outputs['Red'],occ.inputs['Occlusion'])
nm=nodes.new('ShaderNodeNormalMap');nm.location=(-150,-220);nm.uv_map='FinishUV'
link(normal.outputs['Color'],nm.inputs['Color']);link(nm.outputs['Normal'],bsdf.inputs['Normal'])
mesh.materials.clear();mesh.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(out/'M24_Xuanji_CarbonStock_PBR.glb'),export_format='GLB',
    use_selection=True,export_texcoords=True,export_normals=True,export_tangents=True,
    export_animations=False,export_cameras=False,export_lights=False)
# Soft, neutral studio with a continuous cyclorama to keep silhouette legible.
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.cycles.adaptive_threshold=.023
scene.cycles.max_bounces=5
scene.render.threads_mode='FIXED';scene.render.threads=9
scene.world=bpy.data.worlds.new('Neutral studio ambient')
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background')
bg.inputs[0].default_value=(.72,.77,.84,1);bg.inputs[1].default_value=.22
floor_z=-.3274
profile=[(-50,floor_z),(1.0,floor_z)]
for i in range(1,33):
    u=math.pi*i/64
    profile.append((1.+1.5*math.sin(u),floor_z+1.5*(1-math.cos(u))))
profile.append((2.5,30))
verts=[(x,y,z) for y,z in profile for x in (-50,50)]
faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(profile)-1)]
back=bpy.data.meshes.new('Studio sweep');back.from_pydata(verts,[],faces);back.update()
sweep=bpy.data.objects.new('Studio | seamless sweep',back);scene.collection.objects.link(sweep)
for face in back.polygons: face.use_smooth=True
paper=bpy.data.materials.new('Studio | warm grey');paper.diffuse_color=(.58,.59,.60,1);paper.use_nodes=True
p=paper.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value=(.60,.60,.60,1);p.inputs['Roughness'].default_value=.9
back.materials.append(paper)
def aim(o,point):
    o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
def panel(name,pos,target,power,wide,tall,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='RECTANGLE'
    data.size=wide;data.size_y=tall;data.color=color
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=pos;aim(o,target)
panel('01 | long upper key',(-1.0,-1.15,2.65),(0,0,0),150,2.8,.96,(1,.98,.95))
panel('02 | broad fill',(.85,-2.6,.8),(.1,0,0),33,2.3,1.3,(.87,.93,1))
panel('03 | contour strip',(.28,1.35,1.75),(.22,0,.08),135,2.5,.40,(.91,.96,1.0))
panel('04 | left softbox',(-2.35,-.2,.74),(-.7,0,.05),42,.65,1.25,(1,.96,.90))
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.render.resolution_percentage=100
scene.render.resolution_x=2000;scene.render.resolution_y=1000
def camera(name,target,direction,width):
    cam=bpy.data.cameras.new(name);cam.type='ORTHO';cam.ortho_scale=width;cam.clip_start=.01
    o=bpy.data.objects.new(name,cam);scene.collection.objects.link(o)
    o.location=Vector(target)+Vector(direction).normalized()*5.;aim(o,target)
    return o
hero=camera('Camera | three-quarter',(0,0,-.005),(.29,-1,.24),2.2)
side=camera('Camera | side elevation',(0,0,.005),(0,-1,0),2.17)
detail=camera('Camera | surface detail',(.36,-.085,.065),(.10,-1,.15),1.04)
def capture(cam,name):
    scene.camera=cam;scene.render.filepath=str(out/'Renders'/name)
    bpy.ops.render.render(write_still=True)
scene.camera=hero
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.color_type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'M24_Xuanji_CarbonStock_Studio.blend'))
capture(hero,'01_Studio.png')
capture(side,'02_Orthographic.png')
capture(detail,'03_SurfaceDetail.png')
