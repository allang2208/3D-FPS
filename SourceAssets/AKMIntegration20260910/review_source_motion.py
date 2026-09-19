import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent/'SourceReview';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent.parent/'ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend'))
r=bpy.data.objects['SK_AKM_Viewmodel'];s=bpy.context.scene
for ob in s.objects:
    if ob.type=='MESH':ob.hide_render=not(ob.name.startswith('AKMR_') or ob.name=='SK_ArmsRepair_WRAD')
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
d=bpy.data.cameras.new('SourceReview');cam=bpy.data.objects.new('SourceReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.9
report={}
for clip,f in [('idle',1),('reload',15),('reload',30),('reload_empty',53),('reload_empty',72)]:
    a=bpy.data.actions['AKM_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
    p={b.name:r.matrix_world@b.matrix for b in r.pose.bones};report[f'{clip}_{f}']={n:[list(row) for row in m] for n,m in p.items()}
    target=p['hand_l'].translation.lerp(p['hand_r'].translation,.5)
    cam.location=target+Vector((.65,-.6,.38));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{clip}_{f}.png');bpy.ops.render.render(write_still=True)
(O/'poses.json').write_text(json.dumps(report));print('SOURCE_REVIEW_PASS')
