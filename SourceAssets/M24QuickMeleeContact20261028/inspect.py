from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import numpy as np
from mathutils.bvhtree import BVHTree
skin=bpy.data.objects['M24_V9_BareArms'];r.matrix_world=Matrix.Identity(4)
def set_pose(row):
 r.animation_data_clear()
 for n,m in row.items():
  loc=row[parents[n]].inverted()@m if parents[n] else m;r.pose.bones[n].matrix_basis=local_rest[n].inverted()@loc
 bpy.context.view_layer.update()
native_pose=pose
code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text();exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'));pose=native_pose
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
node=next(n for n in ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full');exec(compile(ast.unparse(node),'morphs','exec'))
s.render.resolution_x=900;s.render.resolution_y=600
for n in ('M24_silencer','M24_ExtraScope_Lowpoly','M24_Laser_Lowpoly','M24_LaserHolder_Lowpoly','M24_bullet','M24_Magazine10'):bpy.data.objects[n].hide_render=True
bpy.data.objects['M24_clip'].hide_render=False
gn=[g.name for g in skin.vertex_groups];ids=[];category=[]
for v in skin.data.vertices:
 group=max(v.groups,key=lambda g:g.weight);name=gn[group.group]
 if name.endswith('_r'):
  ids.append(v.index);category.append('fingers' if any(name.startswith(d) for d in ('thumb','index','middle','ring','pinky')) else 'palm' if name=='hand_r' else 'forearm' if name.startswith('lowerarm') else 'upperarm')
gun=bpy.data.objects['M24_base'];gun.data.calc_loop_triangles();bv=BVHTree.FromPolygons([v.co for v in gun.data.vertices],[t.vertices[:] for t in gun.data.loop_triangles],all_triangles=True)
folder=O/'Before';folder.mkdir(exist_ok=True);records=[];idle,_=pose('idle',0);G=idle['WPN_root'].inverted()@idle['hand_r']
for t in (0,.05,.10,.15,.20,.225,.25,.275,.325,.40,.46,.55,.68,.8,.9):
 row,_=pose('quick_melee',t);r.matrix_world=Matrix.Identity(4);set_pose(row);morphs_full()
 ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();inv=rest['WPN_root']@row['WPN_root'].inverted();stats={key:[] for key in ('fingers','palm','forearm','upperarm')}
 for i,cat in zip(ids,category):
  v=inv@me.vertices[i].co;point,normal,_,distance=bv.find_nearest(v)
  if distance<.07 and (v-point).dot(normal)<-.0005:stats[cat].append(distance*1000)
 ob.to_mesh_clear();rel=row['WPN_root'].inverted()@row['hand_r'];records.append({'t':t,'right_grip_mm':(rel.translation-G.translation).length*1000,'right_grip_degrees':math.degrees(rel.to_quaternion().rotation_difference(G.to_quaternion()).angle),'nearest_surface_signed_proxy':{k:{'count':len(v),'max_mm':max(v,default=0)} for k,v in stats.items()},'right_camera_cm':{n:list(C@row[n].translation) for n in ('upperarm_r','lowerarm_r','hand_r')}})
 for view in ('fps','right'):
  if view=='fps':
   r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
  else:
   r.matrix_world=Matrix.Identity(4);target=(row['hand_r'].translation+row['middle_02_r'].translation)*.5;cam.location=target+Vector((.20,-.08,.12));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.25
  s.render.filepath=str(folder/(f'{t:.3f}_{view}.png'));bpy.ops.render.render(write_still=True)
(O/'before_geometry.json').write_text(json.dumps(records,indent=2));print('M24_MELEE_CONTACT_SOURCE_INSPECTED',flush=True)
