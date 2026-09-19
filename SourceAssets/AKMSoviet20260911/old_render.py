import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AKMIntegration20260910/EquipCharge/AKM_EquipCharge_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();inv=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted();out={}
for o in list(s.objects):
 if o.type=='MESH':
  if not o.name.startswith('AKMR'):o.hide_render=True;continue
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev);ob=bpy.data.objects.new('Flat_'+o.name,me);s.collection.objects.link(ob);ob.matrix_world=inv@o.matrix_world;o.hide_render=True
  pts=[ob.matrix_world@v.co for v in me.vertices];out[o.name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
(O/'idle_bounds.json').write_text(json.dumps(out,indent=2))
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1400;s.render.resolution_y=700;s.render.resolution_percentage=100
d=bpy.data.cameras.new('FlatCam');cam=bpy.data.objects.new('FlatCam',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=1.1;target=Vector((0,-.14,0));cam.location=target+Vector((2,0,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'old_side.png');bpy.ops.render.render(write_still=True)
