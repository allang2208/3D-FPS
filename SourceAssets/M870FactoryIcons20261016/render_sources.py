"""Render actual M870 factory components for the shared framed-icon artwork."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix

ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'SourceAssets/M870Tactical20261015'
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'Original/Source/source/M870_Tactical.fbx'))
source=next(o for o in bpy.context.scene.objects if o.type=='MESH')
source.data.transform(source.matrix_world);source.matrix_world=Matrix.Identity(4)
islands=json.loads((SOURCE/'source_geometry.json').read_text())[0]['islands']
groups={'stock':[], 'pump':[], 'muzzle':[0,1,18,19,20,21,22], 'magazine':[34,35,36], 'optic':[]}
for i,c in enumerate(islands):
    lo,hi=c['lo'],c['hi']
    if hi[1]<=-1.60:groups['stock'].append(i)
    if (lo[1]>=1.209 and hi[1]<=3.088 and hi[2]<=.604) or (lo[1]>=.175 and hi[1]<=1.627 and lo[2]>=.445 and hi[2]<=.548):groups['pump'].append(i)
    if lo[1]>=-1.2 and hi[1]<=-.75 and lo[2]>=.78:groups['optic'].append(i)

mat=bpy.data.materials.new('Actual M870 texture surface');mat.use_nodes=True
nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
source.data.materials.clear();source.data.materials.append(mat)
for role,stem in [('Base Color','Albedo'),('Metallic','Metalic'),('Roughness','Roughness'),('Normal','Normal')]:
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SOURCE/'Original/Source/textures'/('M870_Tactical_'+stem+'.png')))
    tex.image.colorspace_settings.name='sRGB' if role=='Base Color' else 'Non-Color';tex.image.pack()
    if role=='Normal':
        normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs[role])
    else:links.new(tex.outputs['Color'],shader.inputs[role])
objects={};report={}
for name,indices in groups.items():
    ids={v for i in indices for v in islands[i]['ids']}
    ob=source.copy();ob.data=source.data.copy();bpy.context.collection.objects.link(ob);ob.name='M870 factory '+name
    bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(ob.data);bm.free()
    for p in ob.data.polygons:p.material_index=0
    # Source +Y muzzle points left; +Z remains screen up, no image mirror.
    rotation=Matrix(((0,-1,0),(1,0,0),(0,0,1))).to_4x4()
    center=sum((v.co for v in ob.data.vertices),Vector())/len(ob.data.vertices)
    ob.data.transform(rotation@Matrix.Translation(-center))
    extent=Vector([max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in range(3)])
    ob.data.transform(Matrix.Scale(1.6/max(extent),4))
    apply_grayscale([ob]);ob.hide_render=True;objects[name]=ob
    report[name]={'source_islands':indices,'vertices':len(ob.data.vertices),'source_mesh':'/Game/Weapons/M870/Tactical20261015/Parts/SM_M870',
        'orientation':'source +Y muzzle -> image left, source +Z -> image up; 3D camera only',
        'source_fbx':str(SOURCE/'Original/Source/source/M870_Tactical.fbx')}
bpy.data.objects.remove(source,do_unlink=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25
cam=bpy.data.objects.new('Part camera',bpy.data.cameras.new('Part camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
for loc,power,size in [((-2,-3,4),220,3),((2,-2,1),80,2),((0,2,3),150,2)]:
    lamp=bpy.data.lights.new('Neutral softbox','AREA');lamp.energy=power;lamp.size=size
    ob=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
neutral_output(scene)
for name,ob in objects.items():
    ob.hide_render=False
    cam.location=Vector((-3,-4,.3)) if name=='optic' else Vector((-.7,-4,.25)) if name=='muzzle' else Vector((0,-4,.12))
    cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    points=[cam.matrix_world.inverted()@(ob.matrix_world@v.co) for v in ob.data.vertices]
    low=Vector([min(v[k] for v in points) for k in range(3)]);high=Vector([max(v[k] for v in points) for k in range(3)])
    cam.data.ortho_scale=max(high.x-low.x,high.y-low.y)/.82
    cam.location+=cam.matrix_world.to_3x3()@Vector(((low.x+high.x)/2,(low.y+high.y)/2,0))
    scene.render.filepath=str(OUT/'Sources'/(name+'.png'));bpy.ops.render.render(write_still=True)
    report[name]['camera_location']=list(cam.location);report[name]['camera_rotation']=list(cam.rotation_euler)
    ob.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M870_FactoryIconSources.blend'))
(OUT/'source_manifest.json').write_text(json.dumps(report,indent=2))
print('M870_FACTORY_SOURCES_SAVED',list(report))
