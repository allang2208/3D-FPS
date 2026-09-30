"""Five user-visible 201 assembly repairs, in the current game's art frame."""
from pathlib import Path
O=Path(__file__).parent;S=O.parent;(O/'Exports').mkdir(exist_ok=True)
helpers=(S/'ReferenceRepair38/model.py').read_text().split('# Restore only the bad receiver')[0]
helpers=helpers.replace('FitFinish37/LMG201_FitFinish37_Editable.blend','HardSurface39/LMG201_HardSurface39.blend').replace('M_LMG201_R38_','M_LMG201_A40_')
exec(compile(helpers,str(O/'model.py'),'exec'),globals())
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree
cx=.0008;parts=[];notes={};F=Matrix.Diagonal((1,-1,1,1))
poses=json.loads((O/'pose_inputs.json').read_text())
def posemat(t):
 q=t['q'];return F@Matrix.LocRotScale(Vector(t['p']),Quaternion((q[3],q[0],q[1],q[2])),Vector(t['s']))@F
def unpose(ob,bone):
 delta=posemat(poses['clips']['idle']['bones'][bone])@posemat(poses['reference'][bone]).inverted();xf=delta.inverted();ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.data.normals_split_custom_set(ns)
def joined(name,obs,bone='WPN_root'):
 select(obs);bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();ob=obs[0];ob.name=name
 select([ob]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
 if bone:bind(ob,bone)
 return ob
def slab(name,profile,half,mat=coat,bev=.00045):
 n=len(profile);vs=[(cx+s*half,y,z) for s in [-1,1] for y,z in profile];fs=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return shape(name,vs,fs,mat,bev)
def displaced(ob,dx):
 for v in ob.data.vertices:v.co.x+=dx
 return ob
def round_profile(y0,y1,z0,z1,r,steps=6):
 return [(y+r*math.cos(a),z+r*math.sin(a)) for y,z,begin in [(y1-r,z1-r,0),(y0+r,z1-r,90),(y0+r,z0+r,180),(y1-r,z0+r,270)] for a in np.radians(np.linspace(begin,begin+90,steps,endpoint=False))]
def ring_slab(name,outer,inner,half,mat=coat):
 n=len(outer);vs=[(cx+s*half,y,z) for s in [-1,1] for p in [outer,inner] for y,z in p];fs=[]
 for i in range(n):
  j=(i+1)%n;fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
 return shape(name,vs,fs,mat,.0005)

# Preserve the edited receiver's old UV and panel color mask. Remove only the
# fused right-side knob; do not let its old atlas normal shade the replacement.
rec=bpy.data.objects['Receiver'];localize(rec);rec.data.materials.append(coat);cut=box('A40_RemoveFusedRightKnob',(-.032,.0475,.057),(.023,.029,.037),coat,0)
cut.data.materials.clear()
for mat in rec.data.materials:cut.data.materials.append(mat)
for p in cut.data.polygons:p.material_index=len(rec.data.materials)-1
boolean(rec,cut,'DIFFERENCE');rec.data.update();ns=[n.vector.copy() for n in rec.data.corner_normals]
for p in rec.data.polygons:
 if p.material_index==2:
  for li in p.loop_indices:ns[li]=p.normal.copy()
rec.data.normals_split_custom_set(ns)

# Rail underside follows actual receiver roof samples. The crown and optical
# interfaces stay at the existing art datum; no floating uniform bottom plane.
mesh=rec.data;mesh.calc_loop_triangles();bv=BVHTree.FromPolygons([v.co for v in mesh.vertices],[t.vertices for t in mesh.loop_triangles],all_triangles=True)
railrows=[];roof_samples=[]
for y in np.linspace(-.083,.060,20):
 lows=[]
 for x in np.linspace(cx-.0125,cx+.0125,7):
  p,n,i,d=bv.ray_cast(Vector((x,float(y),.10)),Vector((0,0,-1)),.06)
  lows.append(min(.0760,p.z-.00065 if p is not None else .071))
 bottom=min(lows);roof_samples.append([float(y),bottom]);railrows.append((float(y),[(cx-.014,bottom),(cx-.014,.0756),(cx-.0119,.078),(cx+.0119,.078),(cx+.014,.0756),(cx+.014,bottom)]))
rail=[loft('A40_ConformingRailBed',railrows,coat,.00022)]
for y in np.linspace(-.0775,.0535,14):
 rail.append(loft('A40_RailTooth',[(float(y)-.00235,[(cx-.0095,.077),(cx-.012,.079),(cx-.012,.0808),(cx-.0105,.082),(cx+.0105,.082),(cx+.012,.0808),(cx+.012,.079),(cx+.0095,.077)]),(float(y)+.00235,[(cx-.0095,.077),(cx-.012,.079),(cx-.012,.0808),(cx-.0105,.082),(cx+.0105,.082),(cx+.012,.0808),(cx+.012,.079),(cx+.0095,.077)])],coat,.00018))
for name in ['TopRail','RearSightBase_Fitted','TriggerGuard_Fitted']:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
parts.append(joined('TopRail_A40',rail));notes['rail_roof_samples']=roof_samples
rearbase=[box('A40_RearClampFoot',(cx,.04252,.0813),(.027,.030,.0076),coat,.00065),slab('A40_RearClampShoulder',[(.02752,.083),(.02752,.0858),(.030,.089),(.055,.089),(.05752,.0858),(.05752,.083)],.0122,coat,.0006)]
# Seat recessed to the native hinge so the folding head does not stand on a gap.
seat=box('A40_HeadSeat',(cx,.04252,.090),(.019,.023,.009),inside,0);boolean(rearbase[1],seat,'DIFFERENCE');finish(rearbase[1],.00018)
parts.append(joined('RearSightBase_A40',rearbase))

# Rounded, bounded replacement for the fused visual right-hand knob. Original
# native operating-control tracks remain unchanged; this surface stays on root.
stem=slab('A40_KnobNeck',[(.041,.053),(.052,.053),(.052,.057),(.050,.063),(.046,.066),(.041,.062)],.0042,coat,.0007);displaced(stem,-.025-cx)
knobparts=[stem,cylinder('A40_KnobCollar',(-.0225,.047,.055),.0056,.0065,'X',coat)]
vs=[];N=48
for x,f in [(-.0255,.64),(-.027,1),(-.031,1),(-.032,.72)]:
 for i in range(N):vs.append((x,.0465+.0065*f*math.cos(i*math.tau/N),.064+.0048*f*math.sin(i*math.tau/N)))
fs=[tuple(range(N-1,-1,-1)),tuple(3*N+i for i in range(N))]+[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)]
knobparts.append(shape('A40_RoundedPullTab',vs,fs,coat,.00018));parts.append(joined('RightHandle_A40',knobparts))

# Retain the lid silhouette and its moving stamped interior. Give the visible
# receiver opening a fixed tray, side returns and a backed port, not sky-through.
station=[-.220,-.205,-.180,-.145,-.108];seams=[.0623,.0639,.0658,.0684,.0732];tops=[.079,.080,.078,.077,.079]
tray=[box('A40_FeedTrayFloor',(cx,-.161,.0447),(.046,.116,.0032),inside,.00065)]
for side in [-1,1]:
 rows=[]
 for y,top in zip(station,tops):
  x=cx+side*.0238;rows.append((y,[(x-.0012,.0415),(x-.0012,top),(x+.0012,top),(x+.0012,.0415)]))
 # Positive side preserves a small feed entrance; the opposite wall backs it.
 wall=loft('A40_TrayWall',rows,inside,.00035)
 if side==1:
  aperture=box('A40_ArtFeedEntrance',(cx+.024,-.175,.057),(.014,.043,.020),inside,.0012);boolean(wall,aperture,'DIFFERENCE');finish(wall,.00012)
 else:
  aperture=box('A40_VisibleSidePort',(cx-.024,-.121,.063),(.014,.022,.009),inside,.0007);boolean(wall,aperture,'DIFFERENCE');finish(wall,.00012)
  tray.append(box('A40_SidePortBacking',(cx-.0175,-.121,.063),(.002,.029,.016),inside,.0005))
 tray.append(wall)
for y in [-.215,-.110]:tray.append(box('A40_TrayEndReturn',(cx,y,.0565),(.047,.003,.026),inside,.0006))
for side in [-1,1]:
 rows=[]
 for y,z in zip(station,seams):
  x=cx+side*.0292;rows.append((y,[(x-.0012,z-.004),(x-.0012,z+.004),(x+.0012,z+.004),(x+.0012,z-.004)]))
 tray.append(loft('A40_CoverSeamReturn',rows,coat,.00032))
parts.append(joined('ReceiverTray_A40',tray))

# A shallow receiver socket surrounds the animated factory neck in IDLE space.
# The magazine shell and hand-contact region do not move as a rigid object.
outer=[(cx-.021,-.166),(cx-.019,-.074),(cx+.019,-.074),(cx+.021,-.166)]
upper=[(cx-.020,-.169),(cx-.0193,-.073),(cx+.0193,-.073),(cx+.020,-.169)]
inner=[(cx-.0188,-.164),(cx-.0179,-.076),(cx+.0179,-.076),(cx+.0188,-.164)]
vs=[(x,y,-.0115) for profile in [outer,inner] for x,y in profile]+[(x,y,.010) for profile in [upper,inner] for x,y in profile];fs=[];n=4
for i in range(n):
 j=(i+1)%n;fs.extend([(i,n+i,n+j,j),(2*n+i,2*n+j,3*n+j,3*n+i),(i,j,2*n+j,2*n+i),(n+i,3*n+i,3*n+j,n+j)])
parts.append(joined('MagazineSocket_A40',[shape('A40_MagazineSocket',vs,fs,coat,.0006)]))

# Rounded guard and a separate curved trigger, authored in the actual idle pose.
guard=ring_slab('A40_Guard',round_profile(-.074,-.013,-.043,-.003,.007),round_profile(-.0705,-.0165,-.0395,-.0065,.005),.0057,coat)
parts.append(joined('TriggerGuard_A40',[guard]))
trigger=slab('A40_CurvedTrigger',[(-.034,-.003),(-.034,-.008),(-.038,-.012),(-.042,-.018),(-.045,-.025),(-.045,-.030),(-.042,-.033),(-.046,-.032),(-.049,-.029),(-.049,-.023),(-.046,-.016),(-.041,-.009),(-.040,-.003)],.0033,satin,.0005)
trigger_mat=satin.copy();trigger_mat.name='M_LMG201_Trigger';trigger.data.materials[0]=trigger_mat
unpose(trigger,'WPN_Trigger');parts.append(joined('Trigger_A40',[trigger],'WPN_Trigger'))
notes['magazine_neck_extension_m']=.0042;notes['native_tracks_changed']=False

# Import only the retained native magazine section from the current UE export.
old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/Before_Body.fbx'),use_anim=False);imported=set(bpy.data.objects)-old;donorrig=next(o for o in imported if o.type=='ARMATURE');donorroot=donorrig.matrix_world@donorrig.data.bones['WPN_root'].matrix_local
for ob in imported:
 if ob.type!='MESH':continue
 me=ob.data;me.calc_loop_triangles();ts=[t for t in me.loop_triangles if 'Magazine' in me.materials[t.material_index].name]
 if not ts:continue
 xf=donorroot.inverted()@ob.matrix_world;indices=np.array([t.vertices[:] for t in ts]);vid,remap=np.unique(indices,return_inverse=True);v=np.array([(xf@me.vertices[int(i)].co)[:] for i in vid]);oldz=v[:,2].copy();amount=np.clip((oldz+.050)/(.050-.034272693),0,1);v[:,2]+=.0042*amount
 nm=bpy.data.meshes.new('A40_MagazineRetainedUV');nm.from_pydata(v.tolist(),[],remap.reshape(-1,3).tolist());nm.update();magmat=bpy.data.materials.new('M_LMG201_Magazine');nm.materials.append(magmat);uv=nm.uv_layers.new(name='UV0');normal=[]
 for p,t in zip(nm.polygons,ts):
  p.use_smooth=True
  for dst,src in zip(p.loop_indices,t.loops):
   uv.data[dst].uv=me.uv_layers.active.data[src].uv;n=(xf.to_3x3().inverted().transposed()@me.corner_normals[src].vector).normalized();z=(xf@me.vertices[me.loops[src].vertex_index].co).z
   if -.050<z<-.034272693:n.z/=1+.0042/(.050-.034272693)
   normal.append(n.normalized())
 nm.normals_split_custom_set(normal);mag=bpy.data.objects.new('FactoryMagazine_A40',nm);bpy.context.scene.collection.objects.link(mag);bind(mag,'WPN_SOCKET_Magazine');parts.append(mag)
for ob in imported:bpy.data.objects.remove(ob,do_unlink=True)
bind(rec,'WPN_root');parts.append(rec)

# Replacement slots shared with the edited rail carry the front components
# unchanged. Only their old slot is replaced once in the runtime assembly.
for name in ['Barrel','GasTube','GasFrontHardware','FrontSightBase_Fitted']:parts.append(bpy.data.objects[name])
select(parts+[rig]);fbx=O/'Exports/SK_LMG201_A40_Parts.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')

# Standalone folding head: optical notch and pivot remain at the current datum.
head=[]
for side in [-1,1]:
 ear=slab('A40_RearSightEar',[(-.004,0),(.004,0),(.004,.0345),(.0028,.0361),(-.0028,.0361),(-.004,.0345)],.0016,coat,.0006);displaced(ear,side*.010);head.append(ear)
profile=[(-.008,.004),(.008,.004),(.008,.0315),(.005,.033),(.003,.0296),(-.003,.0296),(-.005,.033),(-.008,.0315)]
vs=[(cx+x,y,z) for y in [-.0022,.0022] for x,z in profile];n=len(profile);fs=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
head+=[shape('A40_RearSightNotchedLeaf',vs,fs,coat,.00045),box('A40_RearSightLowerBridge',(cx,0,.0035),(.019,.010,.007),coat,.00065),cylinder('A40_RearSightPivot',(cx,0,.010),.0028,.023,'X',satin)]
rear=joined('RearSight_A40',head,None)
# Static component local X excludes the weapon center offset.
for v in rear.data.vertices:v.co.x-=cx
select([rear]);rearfbx=O/'Exports/SM_LMG201_A40_RearSight.fbx';bpy.ops.export_scene.fbx(filepath=str(rearfbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
rear.hide_render=True;rear.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Assembly40.blend'))
(O/'model.json').write_text(json.dumps({'body_fbx':str(fbx),'rear_fbx':str(rearfbx),'parts':[o.name for o in parts],'notes':notes},indent=2));print('A40_AUTHORED',flush=True)
