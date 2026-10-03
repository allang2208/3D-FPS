import bpy,json,math,bisect
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003';SA=O.parent/'RSH12SingleAction20261003'
S=Matrix.Diagonal((1,-1,1,1));cm=Matrix.Diagonal((.01,.01,.01,1))
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
def packed(m):
 p,q,s=m.decompose();return [*p,q.x,q.y,q.z,q.w,*s]
def track_at(tr,t):
 times=tr['times'];vv=tr['values'];i=max(0,min(len(times)-1,bisect.bisect_right(times,t)-1));a=vv[10*i:10*i+10]
 if i==len(times)-1:return a
 b=vv[10*i+10:10*i+20];w=(t-times[i])/(times[i+1]-times[i]);q=Quaternion((a[6],*a[3:6])).slerp(Quaternion((b[6],*b[3:6])),w)
 return [*Vector(a[:3]).lerp(Vector(b[:3]),w),q.x,q.y,q.z,q.w,*Vector(a[7:]).lerp(Vector(b[7:]),w)]
def applied(local,entry,t=0):
 result={n:m.copy() for n,m in local.items()}
 for tr in entry['tracks']:
  n=tr['bone'];v=track_at(tr,t);p,q,s=result[n].decompose();result[n]=Matrix.LocRotScale(p+Vector(v[:3]),Quaternion((v[6],*v[3:6]))@q,s+Vector(v[7:]))
 return result
def load(family='single'):
 source=B/('Single' if family=='single' else 'Dual/'+family)
 bpy.ops.wm.open_mainfile(filepath=str(source/('RSH12_'+family+'_Editable.blend')))
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.animation_data_clear();rig.data.pose_position='POSE'
 return rig,json.loads((SA/(family+'_sources.json')).read_text()),json.loads((SA/family/'profile.json').read_text()),json.loads((source/'authoring.json').read_text())
def native_pose(rig,D,local):
 world={}
 for n in D['rest']:world[n]=world[D['parents'][n]]@local[n] if D['parents'][n] in world else local[n]
 return {n:rig.matrix_world.inverted()@S@cm@world[n]@S for n in rig.data.bones.keys()}
def set_pose(rig,p):
 rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
 for n,m in p.items():
  par=rig.data.bones[n].parent;pn=par.name if par else None
  lr=rest[pn].inverted()@rest[n] if pn else rest[n];lp=p[pn].inverted()@m if pn else m
  rig.pose.bones[n].matrix_basis=lr.inverted()@lp
 bpy.context.view_layer.update()
def source_pose(rig,D,profile,kind='idle'):
 entry=next(e for e in profile['clips'] if e['kind']==kind)
 return native_pose(rig,D,applied({n:matrix(v) for n,v in D['clips'][kind]['samples'][0]['local'].items()},entry))
def render(rig,p,meta,name,camera_kind='hip',reference=None,aim_weight=None):
 set_pose(rig,p)
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
 scene.world=bpy.data.worlds.new('GripDiagnostic');scene.world.color=(.12,.15,.19);scene.display.shading.background_type='WORLD'
 # Map component Blender coordinates into a Blender camera with the actual UE -90-degree pistol basis.
 cv=Matrix(((0,1,0,0),(-1,0,0,0),(0,0,1,0),(0,0,0,1)))
 hip=Matrix.Translation((.01,.032,-.07))@Matrix.Rotation(-math.pi/2,4,'Z')@S
 frame=cv@hip
 if camera_kind=='aim' or aim_weight is not None:
  ra=rig.data.bones['WPN_root'].matrix_local@Matrix(meta['alignment'])
  root=(reference or p)['WPN_root']@rig.data.bones['WPN_root'].matrix_local.inverted()@ra
  rear=S@(root@Vector(meta['markers']['WPN_RearSight']));front=S@(root@Vector(meta['markers']['WPN_FrontSight']));up=S.to_3x3()@(root.to_quaternion()@Vector((0,0,1)))
  f=(front-rear).normalized();z=(up-f*up.dot(f)).normalized();y=z.cross(f).normalized();rot=Matrix((f,y,z)).transposed().to_4x4().inverted()
  aim_location=Vector((.38,0,0))-(rot@rear)
  if aim_weight is None:frame=cv@Matrix.Translation(aim_location)@rot@S
  else:
   location=Vector((.01,.032,-.07)).lerp(aim_location,aim_weight)
   rotation=Matrix.Rotation(-math.pi/2,4,'Z').to_quaternion().slerp(rot.to_quaternion(),aim_weight)
   frame=cv@Matrix.LocRotScale(location,rotation,Vector((1,1,1)))@S
 for ob in list(bpy.data.objects):
  if ob.type=='CAMERA':bpy.data.objects.remove(ob,do_unlink=True)
 # Transform the evaluated meshes only, avoiding modifications to the author skeleton.
 deps=bpy.context.evaluated_depsgraph_get()
 for ob in list(bpy.data.objects):
  if ob.type!='MESH':continue
  ev=ob.evaluated_get(deps);mesh=bpy.data.meshes.new_from_object(ev);view=bpy.data.objects.new('Diagnostic_'+ob.name,mesh);bpy.context.collection.objects.link(view);view.matrix_world=frame@ob.matrix_world;ob.hide_render=True
  for mat in mesh.materials:
   if mat:mat.diffuse_color=(.66,.4,.24,1) if 'Manny' in mat.name else (.3,.33,.36,1)
 camera_data=bpy.data.cameras.new('GripView');camera=bpy.data.objects.new('GripView',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera
 camera.rotation_euler=(Vector((0,-1,0))).to_track_quat('-Z','Y').to_euler();camera_data.type='PERSP';camera_data.clip_start=.01;camera_data.clip_end=20
 fov=75+(55-75)*aim_weight if aim_weight is not None else (75 if camera_kind=='hip' else 55)
 camera_data.sensor_fit='VERTICAL';camera_data.sensor_height=24;camera_data.lens=12/math.tan(math.radians(fov)/2)
 scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
 return frame
