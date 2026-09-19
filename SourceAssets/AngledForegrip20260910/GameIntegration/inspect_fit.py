import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4ContactImpact20260910/M4_Hand_MAT_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
print('ACTIONS',[(a.name,list(a.frame_range)) for a in bpy.data.actions if a.name.startswith('M4')])
a=bpy.data.actions['M4_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
names=['WPN_root','WPN_RearSight','WPN_FrontSight','hand_l','lowerarm_l','upperarm_l','clavicle_l']+[f'{d}_{j:02}_l' for d in ['thumb','index','middle','ring','pinky'] for j in [1,2,3]]
data={n:{'pose':[list(row) for row in r.pose.bones[n].matrix],'rest':[list(row) for row in r.data.bones[n].matrix_local],'tail':list(r.pose.bones[n].tail),'basis':[list(row) for row in r.pose.bones[n].matrix_basis]} for n in names}
(O/'baseline_pose.json').write_text(json.dumps(data,indent=2))
for o in s.objects:o.hide_render=o.type!='MESH' or o.parent!=r
for pos in [(-.7,-.3,.8),(.8,.5,.8)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=80;d.size=1;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(r.pose.bones['hand_l'].head-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.5;d.clip_start=.002
focus=r.pose.bones['hand_l'].head
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=800;s.render.resolution_percentage=100
for i,off in enumerate([(-.35,-.3,.2),(.35,-.3,.2),(0,.4,.2)]):
 cam.location=focus+Vector(off);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'before_{i}.png');bpy.ops.render.render(write_still=True)
