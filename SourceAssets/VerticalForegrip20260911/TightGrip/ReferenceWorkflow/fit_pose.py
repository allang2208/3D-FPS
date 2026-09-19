import bpy,math,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4ContactImpact20260910/M4_Hand_MAT_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest=r.data.bones
a=bpy.data.actions['M4_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
old={b.name:b.matrix.copy() for b in r.pose.bones};basis={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
root=old['WPN_root'];rear=old['WPN_RearSight'];front=old['WPN_FrontSight']
forward=(front.translation-rear.translation).normalized();up=Vector((0,0,1));side=forward.cross(up).normalized()
M=Matrix((forward,-side,up)).transposed().to_4x4();M.translation=rear.translation+forward*.245-up*.075
# Asset visual scale and top-contact pivot, independent of original oversized study units.
G=M@Matrix.Diagonal((.105,.105,.13125,1))@Matrix.Translation((0,0,-.595))
with bpy.data.libraries.load(str(O.parent/'AngledForegrip_M4_Editable.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('FG_')]
parts=[]
for ob in dst.objects:
 local=ob.matrix_basis.copy();s.collection.objects.link(ob);ob.matrix_world=G@local;parts.append(ob)
# Pure flexion about verified local Z. Metacarpals retain rest alignment.
digits=['index','middle','ring','pinky']
for digit in digits:
 r.pose.bones[digit+'_metacarpal_l'].matrix_basis=Matrix.Identity(4)
 for j,ang in enumerate([0,60,35],1):r.pose.bones[f'{digit}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
bpy.context.view_layer.update()
# Palm basis from the actual rig's unposed metacarpal positions.
f=(rest['middle_01_l'].head_local-rest['hand_l'].head_local).normalized()
ac=(rest['pinky_01_l'].head_local-rest['index_01_l'].head_local).normalized();ac=(ac-f*ac.dot(f)).normalized();n=f.cross(ac).normalized()
src=Matrix((f,ac,n)).transposed()
A=(forward*.55-up*.835).normalized();F=side*.85+forward*.53;F=(F-A*F.dot(A)).normalized();N=F.cross(A).normalized();dst=Matrix((F,A,N)).transposed()
Q=dst@src.transposed();H=(Q@rest['hand_l'].matrix_local.to_3x3()).to_4x4()
# Place middle MCP at the rear rim of the opening, fingers crossing its side plane.
middle=G@Vector((.16,0,.035));middle-=side*.022
H.translation=middle-Q@(rest['middle_01_l'].head_local-rest['hand_l'].head_local)
def update():bpy.context.view_layer.update()
# Analytic two-bone reach; minimal swing from native arm avoids rebuilding its roll.
un,fn,hn='upperarm_l','lowerarm_l','hand_l';A0=old[un].translation;target=H.translation
l1=(rest[fn].head_local-rest[un].head_local).length;l2=(rest[hn].head_local-rest[fn].head_local).length
delta=target-A0;dist=delta.length;axis=delta.normalized()
shift=axis*max(0,dist-(l1+l2-.015));A0+=shift
clav=old['clavicle_l'].copy();clav.translation+=shift;r.pose.bones['clavicle_l'].matrix=clav;update()
delta=target-A0;dist=delta.length;axis=delta.normalized();pole=old[fn].translation-A0;pole-=axis*pole.dot(axis);pole.normalize()
desired=H.to_3x3()@rest[hn].matrix_local.to_3x3().inverted()@(rest[hn].head_local-rest[fn].head_local).normalized()
ideal=target-desired*l2;natural=ideal-A0;natural-=axis*natural.dot(axis)
pole=natural.normalized().lerp(pole,.2).normalized()
along=(l1*l1-l2*l2+dist*dist)/(2*dist);elbow=A0+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
u=(elbow-A0).normalized();v=(target-elbow).normalized();ou=(old[fn].translation-old[un].translation).normalized();ov=(old[hn].translation-old[fn].translation).normalized()
upper=Matrix.LocRotScale(A0,ou.rotation_difference(u)@old[un].to_quaternion(),Vector((1,1,1)))
lower=Matrix.LocRotScale(elbow,ov.rotation_difference(v)@old[fn].to_quaternion(),Vector((1,1,1)))
for name,mat in [(un,upper),(fn,lower)]:r.pose.bones[name].matrix=mat;update()
for name in ['upperarm_twist_01_l','upperarm_twist_02_l']:r.pose.bones[name].matrix=upper@old[un].inverted()@old[name];update()
neutral=lower.to_quaternion()@rest[fn].matrix_local.to_quaternion().inverted()@rest[hn].matrix_local.to_quaternion();q=H.to_quaternion()@neutral.inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
for name,fraction in [('lowerarm_twist_02_l',.55),('lowerarm_twist_01_l',.95)]:
 base=lower@rest[fn].matrix_local.inverted()@rest[name].matrix_local;r.pose.bones[name].matrix=Matrix.LocRotScale(base.translation,Quaternion(v,twist*fraction)@base.to_quaternion(),Vector((1,1,1)));update()
r.pose.bones[hn].matrix=H;update()
tb=r.pose.bones['thumb_01_l'];tq=tb.rotation_quaternion.copy();best=None
for degrees in [-20,-10,0,10,20]:
 tb.rotation_quaternion=tq@Quaternion((0,1,0),math.radians(degrees));update()
 point=G.inverted()@r.pose.bones['thumb_03_l'].tail
 error=(point-Vector((-.55,.28,.015))).length+abs(degrees)*.001
 if best is None or error<best[0]:best=(error,tb.rotation_quaternion.copy(),degrees)
tb.rotation_quaternion=best[1];update()
# Keep thumb's existing native local rotations; it stays outside the frame.
for ob in s.objects:ob.hide_render=not(ob in parts or (ob.type=='MESH' and ob.parent==r))
data={'grip_matrix':[list(row) for row in G],'mount_matrix':[list(row) for row in M],'grip_in_root':[list(row) for row in root.inverted()@G],'hand_in_root':[list(row) for row in root.inverted()@H],'old':{n:[list(row) for row in b] for n,b in old.items()},'basis':{b.name:[list(row) for row in b.matrix_basis] for b in r.pose.bones},'shoulder_shift':shift.length,'twist':math.degrees(twist)}
data['finger_points']={n:[list(G.inverted()@r.pose.bones[f'{n}_{j:02}_l'].head) for j in [1,2,3]] for n in digits+['thumb']}
(O/'fit_pose.json').write_text(json.dumps(data,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Foregrip_Pose.blend'))
for pos in [(-.7,-.3,.8),(.8,.5,.8)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=70;d.size=1;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(H.translation-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.34;d.clip_start=.002
focus=middle;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=800;s.render.resolution_percentage=100
for i,off in enumerate([(-.35,-.15,.12),(.35,-.15,.12),(0,.4,.0)]):
 cam.location=focus+Vector(off);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'fit_{i}.png');bpy.ops.render.render(write_still=True)
print('FIT_DONE',data['shoulder_shift'],data['twist'])
