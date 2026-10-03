"""Measure the reported bore seating defect on native shared poses only."""
import bpy,bmesh,json,bisect,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
S=Matrix.Diagonal((1,-1,1,1));cm=Matrix.Diagonal((.01,.01,.01,1))
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
def value(tr,t):
 times=tr['times'];vv=tr['values'];i=max(0,min(len(times)-1,bisect.bisect_right(times,t)-1));a=vv[10*i:10*i+10]
 if i==len(times)-1:return a
 b=vv[10*i+10:10*i+20];w=(t-times[i])/(times[i+1]-times[i]);q=Quaternion((a[6],*a[3:6])).slerp(Quaternion((b[6],*b[3:6])),w)
 return [*Vector(a[:3]).lerp(Vector(b[:3]),w),q.x,q.y,q.z,q.w,*Vector(a[7:]).lerp(Vector(b[7:]),w)]
report={}
fit=json.loads((O/'fit_contract.json').read_text())
for revision in ('before','after'):
 base=O/'BeforeAuthored/SourceAssets/RSH12Integration20261003' if revision=='before' else B
 family_results={}
 for family,folder in [('single','Single'),('r','Dual/r'),('l','Dual/l')]:
  src=base/folder;D=json.loads((B/'Donor'/family/'motion.json').read_text());meta=json.loads((src/'authoring.json').read_text());profile=json.loads((src/'profile.json').read_text())
  bpy.ops.wm.open_mainfile(filepath=str(src/('RSH12_'+family+'_Editable.blend')))
  r=next(o for o in bpy.data.objects if o.type=='ARMATURE');r.animation_data_clear();r.data.pose_position='POSE';rest={b.name:b.matrix_local.copy() for b in r.data.bones};root=rest['WPN_root'];ra=root@Matrix(meta['alignment'])
  newrest={n:m.copy() for n,m in rest.items()}
  for n,p in meta['markers'].items():newrest[n].translation=ra@Vector(p)
  states=[]
  for kind,when in [('idle',0),('single_0_5',2.3),('single_0_5',3.4),('single_0_5',4.5),('single_0_5',5.6),('single_0_5',6.7)]:
   row=min(D['clips'][kind]['samples'],key=lambda row:abs(row['time']-when));t=row['time'];local={n:matrix(v) for n,v in row['local'].items()};entry=next(c for c in profile['clips'] if c['kind']==kind)
   for tr in entry['tracks']:
    n=tr['bone'];v=value(tr,t);p,q,s=local[n].decompose();local[n]=Matrix.LocRotScale(p+Vector(v[:3]),Quaternion((v[6],*v[3:6]))@q,s+Vector(v[7:]))
   world={}
   for n,v in D['rest'].items():
    parent=D['parents'][n]
    if n in local:world[n]=world[parent]@local[n] if parent in world else local[n]
    else:world[n]=matrix(row['world'].get(n,v))
   pose={n:r.matrix_world.inverted()@S@cm@world[n]@S for n in rest if n in world}
   cyl=pose['WPN_Cylinder']@newrest['WPN_Cylinder'].inverted()@ra
   offsets=[]
   for i in range(5):
    x,z,_=fit['chambers'][i]['center_xz_radius'];hole=Vector((x,fit['rear_plane_m'],z))
    oldp=Vector(meta['markers']['WPN_Case_'+str(i)])
    point=Vector((oldp.x,.096 if revision=='before' else fit['rear_plane_m']+1e-5,oldp.z))
    case=pose['WPN_Case_'+str(i)]@newrest['WPN_Case_'+str(i)].inverted()@ra
    # Express the animated cartridge center in the animated cylinder's original source coordinates.
    actual=cyl.inverted()@(case@point);delta=actual-hole
    offsets.append(dict(chamber=i,radial_mm=1000*math.hypot(delta.x,delta.z),axial_mm=1000*delta.y))
   states.append(dict(kind=kind,time=t,seats=offsets))
   if family=='single' and when==6.7:
    for n,m in pose.items():
     par=r.data.bones[n].parent.name if r.data.bones[n].parent else None
     lr=rest[par].inverted()@rest[n] if par else rest[n]
     lp=pose[par].inverted()@m if par in pose else m
     r.pose.bones[n].matrix_basis=lr.inverted()@lp
    bpy.context.view_layer.update()
    for ob in bpy.data.objects:
     if ob.type!='MESH':continue
     arm_slots={i for i,m in enumerate(ob.data.materials) if m and 'Manny' in m.name}
     bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in arm_slots],context='FACES');bm.to_mesh(ob.data);bm.free()
     for mat in ob.data.materials:
      if mat:mat.diffuse_color=(.42,.42,.45,1)
     for i in range(5):
      # Local diagnostic colors separate the five cartridge seats from the cylinder.
      mat=bpy.data.materials.new('Seat_'+str(i));mat.diffuse_color=(.7,.43,.12,1);ob.data.materials.append(mat);idx=len(ob.data.materials)-1
      groups={g.index for g in ob.vertex_groups if g.name in ('WPN_Case_'+str(i),'WPN_Round_'+str(i))}
      ids={v.index for v in ob.data.vertices if any(g.group in groups and g.weight>.5 for g in v.groups)}
      for poly in ob.data.polygons:
       if all(j in ids for j in poly.vertices):poly.material_index=idx
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
    scene.world=bpy.data.worlds.new('DiagnosticWorld');scene.world.color=(.12,.12,.12);scene.display.shading.background_type='WORLD'
    cdata=bpy.data.cameras.new('Diagnostic');cam=bpy.data.objects.new('Diagnostic',cdata);bpy.context.collection.objects.link(cam);scene.camera=cam
    frame=r.matrix_world@cyl;target=frame@Vector((fit['cylinder_axis_xz_radius'][0],fit['rear_plane_m'],fit['cylinder_axis_xz_radius'][1]))
    cam.location=frame@Vector((.14,.29,.125));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cdata.type='ORTHO';cdata.ortho_scale=.17*frame.to_scale().length/math.sqrt(3);cdata.clip_start=.00001;cdata.clip_end=100
    scene.render.filepath=str(O/(revision+'_reload_seats.png'));bpy.ops.render.render(write_still=True)
  family_results[family]=states
 report[revision]=family_results
(O/'pose_fit_diagnosis.json').write_text(json.dumps(report,indent=2))
for revision,families in report.items():
 for family,states in families.items():
  print(revision,family,'idle',[(round(v['radial_mm'],5),round(v['axial_mm'],5)) for v in states[0]['seats']])
