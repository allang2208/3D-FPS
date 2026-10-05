import bpy,math
from pathlib import Path
from mathutils import Vector
SOURCE=Path(r"D:\FPS3D\FPSGAME\SourceAssets\Monsters\LurkerM08\BackRebuildV01_20261004\M08_BackRebuilt_V01.glb")
OUT=SOURCE.parent/"PreviewRequested"
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
corners=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
lo=Vector(tuple(min(p[i] for p in corners) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in corners) for i in range(3)))
center=(lo+hi)*.5
extent=hi-lo
max_dim=max(extent)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1400
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('PreviewWorld')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.55,.60,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'
def area(name,pos,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.location=center+Vector(pos)*max_dim
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
area('Key',(1.6,-1.5,2.3),500,3.5)
area('Fill',(-1.5,.7,1.3),380,3)
area('Top',(.1,1.5,2.7),450,3)
data=bpy.data.cameras.new('PreviewCamera')
cam=bpy.data.objects.new('PreviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam
data.type='ORTHO';data.clip_start=.01;data.clip_end=100
for name,d in {'front':(0,-1,0),'side':(1,0,0),'back':(0,1,0),'angle':(1,-1,.6)}.items():
    cam.location=center+Vector(d).normalized()*max_dim*4
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    inv=cam.rotation_euler.to_matrix().transposed()
    ps=[inv@(p-center) for p in corners]
    width=max(p.x for p in ps)-min(p.x for p in ps)
    height=max(p.y for p in ps)-min(p.y for p in ps)
    data.ortho_scale=max(width,height*1.4)*1.12
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    print('M08_PREVIEW_SAVED '+str(OUT/(name+'.png')),flush=True)
