"""Scoped elbow diagnosis on the existing skinned model, not gameplay acceptance."""
import bpy,math
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
sources={'before':ROOT/'SourceAssets/RuneSwordWristLocked20260920/Standard/Sword_Overhead_WristLockedV4.blend',
         'after':P/'Standard/Sword_Overhead_DowncutReachV5.blend'}
for revision,path in sources.items():
    bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene;rig=bpy.data.objects['SK_RuneSword_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export']
    action=bpy.data.actions[('WristLockedV4' if revision=='before' else 'DowncutReachV5')+'_Standard_Overhead']
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    for ob in scene.objects:ob.hide_render=ob not in (rig,arms,bpy.data.objects.get('RuneSword_Blade'))
    arms.color=(.52,.66,.76,1);scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD';scene.world.color=(.045,.05,.065)
    scene.render.resolution_x=960;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    camera=bpy.data.objects.new('DowncutDiagnosis',bpy.data.cameras.new('DowncutDiagnosis'));scene.collection.objects.link(camera);scene.camera=camera
    camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=24;camera.data.lens=24/(2*math.tan(math.radians(75/2)));camera.data.clip_start=.005
    camera.location=(0,0,0);camera.rotation_euler=(math.pi/2,0,0)
    for label,frame in [('descent',149),('fold',152),('contact',157)]:
        scene.frame_set(frame);scene.render.filepath=str(P/(revision+'_fp_'+label+'.png'));bpy.ops.render.render(write_still=True)
    camera.location=(1.15,.15,.23);target=__import__('mathutils').Vector((0,.24,-.12));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=1.05
    scene.frame_set(152);scene.render.filepath=str(P/(revision+'_side_fold.png'));bpy.ops.render.render(write_still=True)
print('DOWNCUT_MODEL_DIAGNOSIS_RENDERED',flush=True)
