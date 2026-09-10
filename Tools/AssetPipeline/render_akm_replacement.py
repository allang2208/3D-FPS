import bpy,math,json
from pathlib import Path
from mathutils import Vector
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'SK_AKM_Replacement_Source.blend'))
rig=bpy.data.objects['SK_AKM_Viewmodel'];scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.world.color=(.12,.14,.17)
scene.view_settings.look='AgX - Medium High Contrast'
camera_data=bpy.data.cameras.new('AKMR_PreviewCamera');camera=bpy.data.objects.new('AKMR_PreviewCamera',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera
camera_data.lens=56;camera_data.clip_start=.001
for name,co,power,color in [('Key',(1,-.4,1),150,(1,.87,.72)),('Fill',(-.8,0,.5),90,(.62,.77,1)),('Rim',(.2,1,.7),150,(.8,.9,1))]:
    data=bpy.data.lights.new('AKMR_'+name,'AREA');data.energy=power;data.size=2;data.color=color
    light=bpy.data.objects.new(data.name,data);bpy.context.collection.objects.link(light);light.location=co;light.rotation_euler=(Vector((0,.3,-.1))-light.location).to_track_quat('-Z','Y').to_euler()
def set_pose(clip,f):
    action=bpy.data.actions[('AKMR_' if clip in ['fire','aim_fire','equip'] else 'AKM_')+clip]
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(f);bpy.context.view_layer.update()
def render(name):
    scene.render.filepath=str(OUT/('akm_replacement_'+name+'.png'));bpy.ops.render.render(write_still=True)
def center():
    pts=[];deps=bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type=='MESH' and o.parent==rig and not o.hide_render:
            e=o.evaluated_get(deps);m=e.to_mesh();pts.extend(e.matrix_world@v.co for v in m.vertices);e.to_mesh_clear()
    mn=Vector([min(p[i]for p in pts)for i in range(3)]);mx=Vector([max(p[i]for p in pts)for i in range(3)])
    return (mn+mx)*.5
for clip,f in [('idle',1),('reload',15),('reload',35),('reload',52),('reload_empty',75),('reload_empty',88),('fire',5),('equip',23)]:
    set_pose(clip,f);c=center();camera_data.type='PERSP';camera_data.lens=56
    camera.location=c+Vector((.85,-1.15,.55));camera.rotation_euler=(c-camera.location).to_track_quat('-Z','Y').to_euler()
    render(f'{clip}_{f:03d}')
set_pose('idle',1);camera_data.lens=35;camera.location=(0,0,0);camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();render('hip')
set_pose('aim',1)
rear=(rig.matrix_world@rig.pose.bones['WPN_RearSight'].matrix).translation
front=(rig.matrix_world@rig.pose.bones['WPN_FrontSight'].matrix).translation
forward=(front-rear).normalized();camera_data.lens=50;camera.location=rear-forward*.30;camera.rotation_euler=forward.to_track_quat('-Z','Y').to_euler();render('ads_anchor')
# Side silhouette verifies rigid fit independently from camera sway.
set_pose('idle',1)
for o in bpy.data.objects:
    if o.type=='MESH' and o.parent==rig and not o.name.startswith('AKMR_'):o.hide_render=True
camera_data.type='ORTHO';camera_data.ortho_scale=1.02
c=Vector((.06,.28,-.135));camera.location=c+Vector((1,0,.08));camera.rotation_euler=(c-camera.location).to_track_quat('-Z','Y').to_euler();render('side')
print('AKM_REPLACEMENT_RENDER_COMPLETE')
