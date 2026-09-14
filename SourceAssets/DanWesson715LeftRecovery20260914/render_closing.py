"""Requested close/regrip inspection: actual skinned mesh, fixed source camera."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parent
mode = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
motion = 'motion' in sys.argv
folder = root.parent/'DanWesson715ReloadNatural20260914' if mode=='before' else root
blend = folder/('DanWesson715_ReloadNatural_Editable.blend' if mode=='before' else 'DanWesson715_LeftRecovery_Editable.blend')
try: bpy.ops.wm.open_mainfile(filepath=str(blend))
except RuntimeError as e:
    if 'Missing library override hierarchy root data' not in str(e): raise
s=bpy.context.scene; rig=bpy.data.objects['SK_DW715_Manny']
cam_data=bpy.data.cameras.new('CloseInspectionCamera');cam=bpy.data.objects.new('CloseInspectionCamera',cam_data);s.collection.objects.link(cam)
cam.location=(0,0,.05);cam.rotation_euler=(Vector((0,-.40,-.10))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=20;cam.data.clip_start=.015;s.camera=cam
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=640;s.render.resolution_y=440;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=math.radians(35)
s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD'
s.world=bpy.data.worlds.new('CloseInspectionWorld');s.world.color=(.045,.055,.070)
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
out=root/'Inspection'/(mode+'-motion' if motion else mode);out.mkdir(parents=True,exist_ok=True)
prefix='DW715_Natural_' if mode=='before' else 'DW715_LeftRecovery_'
for kind, source_times, scale in [('single_0_6',[7.90,8.10,8.37,8.60,8.80],1),('speed_0',[2.53,2.68,2.95,3.23,3.60],3.85/3.6)]:
    if motion:
        start,end=(7.74,8.90) if kind.startswith('single') else (2.39,3.70)
        source_times=[start+(end-start)*i/35 for i in range(36)]
    action=bpy.data.actions[prefix+kind];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    for i,t in enumerate(source_times):
        frame=t*scale*60;s.frame_set(int(frame),subframe=frame%1)
        s.render.filepath=str(out/f'{kind}_{i}.png');bpy.ops.render.render(write_still=True)
print('DW715_CLOSE_RENDERED',mode,flush=True)
