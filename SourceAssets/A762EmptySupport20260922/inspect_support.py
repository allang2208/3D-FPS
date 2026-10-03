"""Inspect the actual A762 receiver and the installed empty-reload tail."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
sources=json.loads((O/'sources.json').read_text())
job=sources['animations'][0]
bpy.ops.wm.open_mainfile(filepath=str(Path(job['source'][0]).with_suffix('.blend')))
r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
for ob in scene.objects:
    if ob.type=='MESH':ob.hide_render=ob.name!='SK_Manny_Arms_Export'
geometry=S/'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
with bpy.data.libraries.load(str(geometry),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith('A762_')]
weapon=[]
for ob in dst.objects:
    if ob.type!='MESH':continue
    if ob.hide_render or 'Before' in ob.name:continue
    if not any(m.type=='ARMATURE' for m in ob.modifiers):continue
    if ob.name not in scene.objects:scene.collection.objects.link(ob)
    world=ob.matrix_world.copy();ob.parent=r;ob.matrix_world=world
    for m in ob.modifiers:
        if m.type=='ARMATURE':m.object=r
    ob.hide_set(False);ob.hide_render=False;ob.color=(.50,.40,.23,1);weapon.append(ob)
skin=bpy.data.objects['SK_Manny_Arms_Export'];skin.hide_set(False);skin.hide_render=False;skin.color=(.27,.46,.68,1)
out=O/'Diagnosis';out.mkdir(exist_ok=True)
report={'action':r.animation_data.action.name,'fps':scene.render.fps/scene.render.fps_base,
        'frames':list(r.animation_data.action.frame_range),'weapon_objects':[o.name for o in weapon],'poses':{}}
for f in range(240,501,10):
    scene.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.inverted()
    report['poses'][str(f)]={n:[list(row) for row in root@r.pose.bones[n].matrix] for n in ('hand_l','hand_r','lowerarm_l','upperarm_l','WPN_bolt','WPN_SOCKET_Magazine')}
(O/'source_motion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('A762_SUPPORT_SOURCE',report['action'],report['fps'],report['frames'],report['weapon_objects'],flush=True)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.render.resolution_x=900;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=86
cam=bpy.data.objects.new('SupportDiagnosisCamera',bpy.data.cameras.new('SupportDiagnosisCamera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=.50
for f in (280,320,360,400,440):
    scene.frame_set(f);bpy.context.view_layer.update()
    root=r.pose.bones['WPN_root'].matrix
    center=(r.pose.bones['hand_l'].matrix.translation+root@Vector((0,-.16,.04)))/2
    cam.location=center+root.to_3x3()@Vector((.70,.25,.35))
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/f'before_{f}.jpg');bpy.ops.render.render(write_still=True)
scene.frame_set(360)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Support_Working.blend'))
