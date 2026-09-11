import bpy, json, math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;report={}
for clip,frames in [('idle',[0]),('reload',[0,5,116,126]),('reload_empty',[0,150,162]),('equip',[0,30,38]),('drum_reload_empty',[148])]:
 bpy.ops.wm.open_mainfile(filepath=str(O/('A_M4_Foregrip_'+clip+'.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['A_M4_Foregrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for ob in s.objects:ob.hide_render=not(ob.name.startswith('FG_') or (ob.type=='MESH' and ob.parent==r and not ob.name.startswith('Drum')))
 d=bpy.data.cameras.new('ContactReview');cam=bpy.data.objects.new('ContactReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.50;d.clip_start=.001
 for pos in [(-.6,-.2,.9),(.8,.6,.7)]:
  light=bpy.data.lights.new('ContactReview','AREA');light.energy=70;light.size=1;ob=bpy.data.objects.new('ContactReview',light);s.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,.35,-.08))-ob.location).to_track_quat('-Z','Y').to_euler()
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=720;s.render.resolution_percentage=100
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
  grip=root@Matrix(json.loads((O/'fit_pose.json').read_text())['grip_in_root']);focus=grip@Vector((0,0,0))
  cam.location=focus+Vector((.4,-.12,.10));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'review_{clip}_{f}.png');bpy.ops.render.render(write_still=True)
  report[f'{clip}_{f}']={n:list(grip.inverted()@r.pose.bones[n].head) for n in ['hand_l','index_01_l','middle_01_l','ring_01_l','pinky_01_l','thumb_03_l']}
 (O/'review_pose.json').write_text(json.dumps(report,indent=2))
