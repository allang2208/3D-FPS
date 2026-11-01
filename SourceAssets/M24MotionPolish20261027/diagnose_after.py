import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_MotionPolish_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
left=[v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name.endswith('_l'))>.5]
def pose(role,f):
 a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
def angle(row,side):
 u,l,h=[row[x+'_'+side] for x in ('upperarm','lowerarm','hand')]
 actual=(l.translation-u.translation).cross(h.translation-l.translation).normalized()
 native=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).cross(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
 wanted=u.to_quaternion()@rest['upperarm_'+side].to_quaternion().inverted()@native
 return math.degrees(wanted.angle(actual))
out={}
for role,frames in [('aim',[0]),('sprint_enter',[0,5,10,15]),('sprint_loop',[0,7,15,23,30]),('fire',[16,20,25,28,35,39]),('reload_empty',[68,77,87,91]),('cycle',[20,29,39,43])]:
 rows=[]
 for f in frames:
  pose(role,f);row={b.name:b.matrix.copy() for b in r.pose.bones}
  e=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh()
  pts=[C@me.vertices[i].co for i in left]
  visible=[p for p in pts if p.x>1 and abs(p.y)<p.x*math.tan(math.radians(75/2))*16/9 and abs(p.z)<p.x*math.tan(math.radians(75/2))]
  rowout={'frame':f,'left_visible_vertices':len(visible),'left_wrist_camera_cm':list(C@row['hand_l'].translation),'left_hinge_error_deg':angle(row,'l'),
          'right_hand_in_bolt': [list(x) for x in row['WPN_BoltHandle'].inverted()@row['hand_r']]}
  rows.append(rowout);e.to_mesh_clear()
 out[role]=rows
(O/'after.json').write_text(json.dumps(out,indent=2))
for role,rows in out.items():print(role,[(x['frame'],x['left_visible_vertices'],round(x['left_hinge_error_deg'],1),[round(v,1) for v in x['left_wrist_camera_cm']]) for x in rows],flush=True)
for ob in s.objects:
 if ob.type=='MESH':ob.color=(.63,.69,.76,1) if ob==skin else (.16,.19,.22,1)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True
s.world=bpy.data.worlds.new('Diagnosis');s.world.color=(.05,.06,.08)
s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.use_compositing=False;s.render.use_sequencer=False
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75/2)));cam.data.clip_start=.01
cam.rotation_euler=(math.pi/2,0,0)
cs=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))
r.matrix_world=cs@C
pose('sprint_loop',7);s.render.filepath=str(O/'after_sprint.png');bpy.ops.render.render(write_still=True)
r.matrix_world=Matrix.Identity(4);pose('fire',28)
target=r.pose.bones['WPN_BoltHandle'].matrix.translation
cam.location=target+Vector((.28,-.12,.20));cam.rotation_euler=(target+Vector((.04,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.35
s.render.filepath=str(O/'after_bolt.png');bpy.ops.render.render(write_still=True)
