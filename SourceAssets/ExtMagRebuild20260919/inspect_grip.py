import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
current='--current' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_ExtMag_reload_Editable.blend' if current else O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_ExtMag_reload' if current else 'M4_MAT_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
s.frame_set(76);bpy.context.view_layer.update()
hand=bpy.data.objects['SK_Manny_Arms_Export'];mag=bpy.data.objects['M4_Magazine Light.003_Export']
dg=bpy.context.evaluated_depsgraph_get();ev=mag.evaluated_get(dg);m=ev.to_mesh();points=[ev.matrix_world@v.co for v in m.vertices];tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear()
report={n:{'surface_distance_mm':tree.find_nearest(r.matrix_world@r.pose.bones[n].matrix.translation)[3]*1000} for n in ['thumb_03_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l']}
report['mag_rest_bounds']=[[min((mag.matrix_world@v.co)[k] for v in mag.data.vertices) for k in range(3)],[max((mag.matrix_world@v.co)[k] for v in mag.data.vertices) for k in range(3)]]
(O/('grip_current.json' if current else 'grip_inspection.json')).write_text(json.dumps(report,indent=2));print(report)
for ob in s.objects: ob.hide_render=ob not in [hand,mag]
for ob in [hand,mag]:ob.hide_set(False);ob.hide_render=False
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;hand.color=(.22,.3,.45,1);mag.color=(.7,.6,.35,1)
center=sum(points,Vector())/len(points)
cam=bpy.data.objects.new('GripDiagnosisCamera',bpy.data.cameras.new('GripDiagnosisCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.36
s.render.resolution_x=850;s.render.resolution_y=700;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
for name,offset in [('side',(-.4,0,.12)),('palm',(-.28,-.3,.08))]:
 cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(('current_grip_' if current else 'diagnosis_grip_')+name+'.png'));bpy.ops.render.render(write_still=True)
