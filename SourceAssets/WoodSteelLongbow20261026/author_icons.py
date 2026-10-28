"""Author the game's inventory icon and the three new factory-part icon sources."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'WoodSteelLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.scale_length=1
names=['SK_WoodSteelLongbow_Original','SM_WoodSteelLongbow_Grip','SM_WoodSteelLongbow_Rest']
subjects=[bpy.data.objects[n] for n in names]
for obj in list(bpy.data.objects):
    if obj not in subjects:bpy.data.objects.remove(obj,do_unlink=True)
for obj in subjects:
    obj.hide_render=False;obj.hide_set(False);obj.parent=None;obj.modifiers.clear()
    obj.data.transform(Matrix.Scale(.01,4));obj.matrix_world=Matrix.Identity(4)
for im in bpy.data.images:
    path=P/'Textures'/(im.name.split('.')[0]+'.png')
    if path.exists():im.filepath=str(path);im.reload()
info=json.loads((P/'authoring.json').read_text())
stringmat=bpy.data.materials.new('IconString');stringmat.use_nodes=True
bs=stringmat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.035,.028,.021,1);bs.inputs['Roughness'].default_value=.8
def point(k):
    a=info[k];return Vector((a[0],-a[1],a[2]))*.01
for key in ['nock_upper_cm','nock_lower_cm']:
    a,b=point(key),point('brace_nock_cm');d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0009,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.name='String_'+key;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
    o.data.materials.append(stringmat);subjects.append(o)
camera=bpy.data.cameras.new('IconCamera');camera.type='ORTHO';camera.clip_start=.001;camera.clip_end=100
cam=bpy.data.objects.new('IconCamera',camera);scene.collection.objects.link(cam);scene.camera=cam
scene.world=bpy.data.worlds.new('IconStudio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.32,.32,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
lights=[]
for name,offset,power,size in [('Key',(-1,1.5,1.8),110,2),('Fill',(1.5,1,.5),65,1.5),('Edge',(0,-1,1),85,1.2)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);lights.append((o,Vector(offset)))
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.look='None';scene.view_settings.exposure=.5
def render(selected,name,width,height,turn=False,direction=Vector((0,1,0))):
    for obj in subjects:obj.hide_render=obj not in selected
    saved={o:o.matrix_world.copy() for o in selected}
    if turn:
        rotation=Matrix.Rotation(-math.pi/2,4,'Y')
        for obj in selected:obj.matrix_world=rotation@obj.matrix_world
    cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    axes=[cam.matrix_world.to_3x3()@Vector(v) for v in [(1,0,0),(0,1,0),(0,0,1)]]
    points=[obj.matrix_world@v.co for obj in selected for v in obj.data.vertices]
    lo=[min(p.dot(a) for p in points) for a in axes];hi=[max(p.dot(a) for p in points) for a in axes]
    center=sum((axis*((a+b)*.5) for axis,a,b in zip(axes,lo,hi)),Vector())
    cam.location=center+direction.normalized()*3
    camera.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*width/height)/.86
    for o,offset in lights:o.location=center+offset;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.filepath=str(P/'Icons'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    for obj,matrix in saved.items():obj.matrix_world=matrix
render(subjects,'bow_woodsteel',640,320,True)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale(subjects);neutral_output(scene)
for slot,obj in zip(['riser','grip','arrow_rest'],subjects[:3]):
    render([obj],'factory_'+slot,1024,1024,slot=='riser',Vector((-.2,1,.12)).normalized())
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WoodSteelLongbow_Icons.blend'))
(P/'icon-authoring.json').write_text(json.dumps({'inventory':'bow_woodsteel.png','factory':['riser','grip','arrow_rest'],
    'source':'WoodSteelLongbow_Editable.blend','gameplay_tested':False},indent=2),encoding='utf-8')
print('WOOD_STEEL_ICON_SOURCES_SAVED')
