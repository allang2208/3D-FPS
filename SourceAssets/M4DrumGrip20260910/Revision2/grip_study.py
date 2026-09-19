import bpy, math, json, sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT.parent))
from preview_setup import setup
r,s,drum=setup()
a=bpy.data.actions['M4_HK416_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(95);bpy.context.view_layer.update()
snapshot={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
for n,m in snapshot.items():r.pose.bones[n].matrix_basis=m
bpy.context.view_layer.update()
data=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(data['source_to_component']);center=Vector(data['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
hand=r.pose.bones['hand_l'];fingers=[b for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))]
rest=r.data.bones
forward=(rest['middle_01_l'].head_local-rest['hand_l'].head_local).normalized()
across=(rest['pinky_01_l'].head_local-rest['index_01_l'].head_local).normalized()
normal=forward.cross(across).normalized()
# Positive finger flexion is about local Z; use it to orient the palm inward.
flex=rest['middle_01_l'].matrix_local.to_3x3().col[1]
if normal.dot(flex)<0:normal.negate()
across=normal.cross(forward).normalized()
src=Matrix((forward,across,normal)).transposed()
goal_forward=Vector((0,-1,0));goal_normal=Vector((1,0,0));goal_across=goal_normal.cross(goal_forward)
dst=Matrix((goal_forward,goal_across,goal_normal)).transposed()
rotation=D.to_3x3()@dst@src.transposed()
wrist=Matrix.LocRotScale(D@Vector((-.090,.090,-.085)),(rotation@rest['hand_l'].matrix_local.to_3x3()).to_quaternion(),Vector((1,1,1)))
hand.matrix=wrist;bpy.context.view_layer.update()
for b in fingers:
 b.rotation_mode='QUATERNION';b.location=Vector();b.scale=Vector((1,1,1));b.rotation_quaternion=Quaternion()
 if 'metacarpal' not in b.name:
  digit,joint,_=b.name.split('_');joint=int(joint)
  deg={'index':[-23,60,10],'middle':[-32,60,10],'ring':[-32,60,10],'pinky':[-22,60,10],'thumb':[35,10,0]}[digit][joint-1]
  b.rotation_quaternion=Quaternion((0,0,1),math.radians(deg))
bpy.context.view_layer.update()
# Isolate only the selected hand vertices for a clear grip study.
hm=bpy.data.objects['SK_Manny_Arms_Export'];left_groups={g.index for g in hm.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky'))}
import bmesh
bm=bmesh.new();bm.from_mesh(hm.data);layer=bm.verts.layers.deform.active
remove=[v for v in bm.verts if sum(w for g,w in v[layer].items() if g in left_groups)<.05]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(hm.data);bm.free()
for ob in s.objects:
 if ob.type=='MESH' and ob not in [hm,drum]:ob.hide_render=True
s.render.resolution_x=900;s.render.resolution_y=800
focus=D@Vector((-.02,0,-.085));s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.38
for name,offset in [('front',(-.35,.50,.2)),('back',(-.35,-.5,.2)),('side',(-.55,.02,.02))]:
 s.camera.location=focus+D.to_3x3()@Vector(offset);s.camera.rotation_euler=(focus-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(OUT/('study_'+name+'.png'));bpy.ops.render.render(write_still=True)
result={'wrist_in_drum':[list(v) for v in D.inverted()@hand.matrix],'fingers':{b.name:[list(v) for v in b.matrix_basis] for b in fingers},'landmarks':{b.name:list(D.inverted()@b.head) for b in fingers},'palm_rest_axes':[list(forward),list(across),list(normal)]}
(OUT/'study_pose.json').write_text(json.dumps(result,indent=2))
