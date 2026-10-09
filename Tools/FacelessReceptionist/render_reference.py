"""Render the delivered V01 model for the user's requested reference preview."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007')
OUT=ROOT/'Preview20261008'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring'/'FacelessReceptionist_V01.blend'))
s=bpy.context.scene
s.frame_set(0)
for ob in s.objects:
    if ob.type=='ARMATURE' and ob.animation_data:
        ob.animation_data.action=None
        for tr in ob.animation_data.nla_tracks: tr.mute=True
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
sources=[o for o in s.objects if o.type=='MESH' and not o.hide_render]
static=[]
bounds=[]
for ob in sources:
    ev=ob.evaluated_get(dg)
    me=bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    me.transform(ob.matrix_world)
    for v in me.vertices: bounds.append(v.co.copy())
    static.append((ob.name,me))
lo=Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
hi=Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
cx,cy=(lo.x+hi.x)/2,(lo.y+hi.y)/2
height=hi.z-lo.z
for ob in list(s.objects):
    bpy.data.objects.remove(ob,do_unlink=True)
span=max(hi.x-lo.x,hi.y-lo.y)
gap=span*1.18
for idx,angle in enumerate([0,-math.pi/2,math.pi]):
    transform=Matrix.Translation(Vector(((idx-1)*gap,0,-lo.z))) @ Matrix.Rotation(angle,4,'Z') @ Matrix.Translation(Vector((-cx,-cy,0)))
    for name,me in static:
        ob=bpy.data.objects.new(['Front_','Side_','Back_'][idx]+name,me)
        s.collection.objects.link(ob);ob.matrix_world=transform
def aim(ob,pt): ob.rotation_euler=(Vector(pt)-ob.location).to_track_quat('-Z','Y').to_euler()
def material(name,color):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.85
    return mat
groundmat=material('Preview_Studio_Ground',(.32,.34,.36))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012))
ground=bpy.context.object;ground.name='Preview_Ground';ground.data.materials.append(groundmat)
s.world=bpy.data.worlds.new('Preview_Studio_World');s.world.use_nodes=True
bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.55,.59,.65,1);bg.inputs['Strength'].default_value=.55
for name,loc,power,size,color in [
    ('Key',(-3,-4,4.5),950,5,(1,.92,.84)),
    ('Fill',(4,-2,3),700,4,(.8,.9,1)),
    ('Rim',(0,3,4),1100,4,(1,1,1)),
]:
    dat=bpy.data.lights.new(name,'AREA');dat.energy=power;dat.shape='DISK';dat.size=size;dat.color=color
    ob=bpy.data.objects.new(name,dat);s.collection.objects.link(ob);ob.location=loc;aim(ob,(0,0,height*.55))
textmat=material('Preview_Label',(.065,.077,.09))
for idx,label in enumerate(['FRONT','SIDE','BACK']):
    dat=bpy.data.curves.new('Label_'+label,'FONT');dat.body=label;dat.align_x='CENTER';dat.size=.067;dat.space_character=1.25
    ob=bpy.data.objects.new('Label_'+label,dat);s.collection.objects.link(ob)
    ob.location=((idx-1)*gap,-.48,height+.145);ob.rotation_euler=(math.pi/2,0,0);dat.materials.append(textmat)
camdat=bpy.data.cameras.new('Preview_Camera');cam=bpy.data.objects.new('Preview_Camera',camdat);s.collection.objects.link(cam)
cam.location=(0,-10,height*.53);aim(cam,(0,0,height*.53));camdat.type='ORTHO';camdat.sensor_fit='HORIZONTAL'
s.render.resolution_x=3200;s.render.resolution_y=1500;s.render.resolution_percentage=100
camdat.ortho_scale=max((gap*2+span)*1.1,(height+.44)*s.render.resolution_x/s.render.resolution_y)
s.camera=cam;s.render.engine='BLENDER_EEVEE'
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
s.view_settings.view_transform='AgX';s.view_settings.exposure=0;s.view_settings.gamma=1
s.render.filepath=str(OUT/'FacelessReceptionist_V01_ThreeView.png')
bpy.ops.render.render(write_still=True)
(OUT/'preview_receipt.json').write_text(json.dumps({'source':str(ROOT/'Authoring'/'FacelessReceptionist_V01.blend'),'output':s.render.filepath,'mesh_parts':len(static),'pose':'bind pose','height_m':height,'engine':'BLENDER_EEVEE'},indent=2),encoding='utf-8')
print('PREVIEW_SAVED '+s.render.filepath)
