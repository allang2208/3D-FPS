"""User-requested color inspection images of the current V2; no asset modifications."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;P.mkdir(parents=True,exist_ok=True)
source=P.parent/'StaticField_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene
model=bpy.data.objects['SM_ThunderGodHammer_grip_static_field_V2']
for o in scene.objects:
    if o.type=='MESH':o.hide_render=(o!=model)
    elif o.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(o,do_unlink=True)
model.hide_render=False;model.hide_set(False)
scene.render.engine='CYCLES';scene.cycles.samples=96;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.render.resolution_percentage=100;scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.world=bpy.data.worlds.new('InspectionNeutral');scene.world.use_nodes=True
back=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
back.inputs[0].default_value=(.065,.075,.085,1);back.inputs[1].default_value=.40
camdata=bpy.data.cameras.new('InspectionCamera');camdata.type='ORTHO';camdata.lens=70
cam=bpy.data.objects.new('InspectionCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
lights=[]
def light(name,offset,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);lights.append((o,Vector(offset)))
light('LargeSoftKey',(-.30,-.38,.40),32,.36)
light('BroadFill',(.34,-.25,.05),9,.45)
light('EdgeReflection',(.17,.22,.32),23,.28)
def shot(name,target,camera,scale,resolution):
    target=Vector(target);cam.location=Vector(camera);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale
    for o,offset in lights:
        o.location=target+offset;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x,scene.render.resolution_y=resolution
    scene.render.filepath=str(P/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_SAVED',name,flush=True)
# The exported mesh pivot is the upper mating land. Only presentation transforms change.
model.matrix_world=Matrix.Rotation(math.radians(67),4,'Y')@Matrix.Translation((0,0,.245))
shot('01_full_grip',(0,0,0),(0,-.85,.12),.61,(1800,850))
model.matrix_world=Matrix.Translation((0,0,.405))
shot('02_collar_inlay',(-.00045,-.00105,.376),(.038,-.18,.399),.076,(1600,1300))
shot('03_leather_stitch',(-.00045,-.00105,.172),(.032,-.17,.185),.067,(1400,1400))
(P/'preview_receipt.json').write_text(json.dumps(dict(source=str(source),revision='StaticFieldGripV2',images=['01_full_grip.png','02_collar_inlay.png','03_leather_stitch.png'],renderer='Blender Cycles',color='Current source PBR, no grayscale conversion',engine_screenshot=False,asset_modified=False,decimated=False),indent=2),encoding='utf-8')
print('REQUESTED_PREVIEW_COMPLETE',flush=True)
