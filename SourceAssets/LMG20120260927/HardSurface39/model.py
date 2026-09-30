"""Local 201 hard-surface repair, preserving native art interfaces and controls."""
from pathlib import Path
O=Path(__file__).parent;S=O.parent
# Reuse the retained, bounded mesh authoring helpers, not the R38 production body.
helpers=(S/'ReferenceRepair38/model.py').read_text().split('# Restore only the bad receiver')[0]
helpers=helpers.replace("FitFinish37/LMG201_FitFinish37_Editable.blend","ReferenceRepair38/LMG201_ReferenceRepair38.blend").replace('M_LMG201_R38_','M_LMG201_H39_')
helpers=helpers.replace('bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))','bmesh.ops.dissolve_degenerate(bm,dist=.0000001,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))')
exec(compile(helpers,str(O/'model.py'),'exec'),globals())
cx=.0008;new=[];old_names=['Barrel','GasTube','GasFrontHardware','FrontSightBase_Fitted','TopRail'];roles={};report={}
def join(name,parts,bone='WPN_root'):
 select(parts);bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=parts[0];ob.name=name
 select([ob]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
 if bone:bind(ob,bone)
 return ob
def lathe(name,rows,z,mat=coat):
 n=64;verts=[(cx+r*math.cos(i*math.tau/n),y,z+r*math.sin(i*math.tau/n)) for y,r in rows for i in range(n)]
 faces=[tuple(range(n-1,-1,-1)),tuple((len(rows)-1)*n+i for i in range(n))]+[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(rows)-1) for i in range(n)]
 return shape(name,verts,faces,mat,.00016)
def side_profile(name,profile,half,mat=coat,bevel=.00055):
 n=len(profile);verts=[(cx+s*half,y,z) for s in [-1,1] for y,z in profile];faces=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return shape(name,verts,faces,mat,bevel)
for name in old_names:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)

barrel=lathe('H39_Barrel',[(y,r) for y,r in [(-.6877,.0092),(-.683,.0092),(-.6815,.0089),(-.572,.0089),(-.570,.0101),(-.537,.0101),(-.535,.0098),(-.45166,.0098)]],.04866)
new.append(join('Barrel',[barrel]))
tube=lathe('H39_GasTube',[(-.57077,.0076),(-.566,.0076),(-.565,.0086),(-.538,.0086),(-.536,.0079),(-.460,.0079),(-.45166,.0091)],.0181)
port=cylinder('H39_VisiblePort',(cx+.0080,-.501,.019),.0017,.004,'X',inside);boolean(tube,port,'DIFFERENCE');finish(tube,.00012)
new.append(join('GasTube',[tube]))
hardware=lathe('H39_FrontSteppedCap',[(-.59065,.0076),(-.5897,.009),(-.5873,.009),(-.5863,.0055),(-.5785,.0055),(-.577,.0070),(-.571,.0070),(-.57018,.0076)],.0174)
# The small hanging loop follows the visible source; closed rings reuse topology.
loop=[];N=48;K=10;verts=[]
for i in range(N):
 for j in range(K):
  r=.0041+.00105*math.cos(j*math.tau/K);verts.append((cx+r*math.cos(i*math.tau/N),-.587+r*math.sin(i*math.tau/N),.0069+.00105*math.sin(j*math.tau/K)))
faces=[(i*K+j,((i+1)%N)*K+j,((i+1)%N)*K+(j+1)%K,i*K+(j+1)%K) for i in range(N) for j in range(K)]
loop=shape('H39_ClosedFrontLoop',verts,faces,coat)
new.append(join('GasFrontHardware',[hardware,loop,box('H39_LoopStem',(cx,-.588,.0098),(.003,.0035,.0055),coat,.00035)]))

housing=side_profile('H39_SightHousing',[(-.56948,.034),(-.56948,.051),(-.558,.056),(-.550,.0648),(-.535,.0648),(-.529,.055),(-.51875,.052),(-.51875,.035),(-.528,.030),(-.562,.030)],.0132,coat,.00065)
barrel_cut=cylinder('H39_BarrelSeat',(cx,-.543,.04866),.01015,.064,'Y',inside);boolean(housing,barrel_cut,'DIFFERENCE');finish(housing,.00015)
baseparts=[housing,box('H39_LowerSightBridge',(cx,-.550,.028),(.018,.025,.017),coat,.0008)]
for x in [cx-.0132,cx+.0132]:baseparts.append(cylinder('H39_SightPivotHead',(x,-.54212,.0596),.0048,.0020,'X',coat))
new.append(join('FrontSightBase_Fitted',baseparts))

# Retain rail length, top height and mounting datum; rebuild regular cross-bars.
rail=[box('H39_RailWeb',(cx,-.012,.077),(.024,.140,.0024),coat,.00025)]
for y in np.linspace(-.0775,.0535,14):
 rail.append(box('H39_RailTooth',(cx,float(y),.080),(.024,.0047,.004),coat,.00028))
new.append(join('TopRail',rail))

# Existing embossed panels and grip ridges retain topology and UV. Only fitted
# coherent panels move. Preserve the authored corner normals outside the fit;
# tiny moved triangles cannot provide a stable rotation for a shaded panel.
for name in ['Receiver','Handguard']:
 ob=bpy.data.objects[name];localize(ob);me=ob.data;me.update();old_v=np.array([v.co[:] for v in me.vertices]);old_face=[p.normal.copy() for p in me.polygons];old_n=[n.vector.copy() for n in me.corner_normals]
 data=np.load(O/(name+'_fair.npz'));target=data['v'];mask=data['mask'];normal_fit=data['normal_target']
 for vert,p in zip(me.vertices,target):vert.co=p
 me.update();normals=old_n.copy()
 for p,normal in zip(me.polygons,old_face):
  for i in p.loop_indices:
   norm=old_n[i].normalized();vi=me.loops[i].vertex_index;fit=Vector(normal_fit[vi])
   if mask[vi]>0 and fit.length>.5 and norm.dot(fit)>.80:norm=(norm*(1-mask[vi]*.95)+fit*mask[vi]*.95).normalized()
   normals[i]=norm
 me.normals_split_custom_set(normals)
 clean=me.color_attributes.new(name='H39SurfaceClean',type='FLOAT_COLOR',domain='CORNER');me.color_attributes.active_color=clean;me.color_attributes.render_color_index=len(me.color_attributes)-1
 for i,loop in enumerate(me.loops):clean.data[i].color=(float(mask[loop.vertex_index]),0,0,1)
 mat=bpy.data.materials.new('M_LMG201_H39_'+name);mat.use_nodes=True;roles[mat.name]=name
 me.materials[0]=mat;report[name]={'topology_preserved':True,'panel_mask_vertices':int((mask>.1).sum())};bind(ob,'WPN_root');new.append(ob)

# The old independent bipod base spans 148 mm and exposes both end wedges.
# A compact saddle and twin ears connect the SAME existing leg pivots.
# Explicit closed cross-sections avoid the tiny Boolean/bevel fragments that
# the static importer removed from the first mount candidate.
saddle=[]
for y in [-.479,-.477,-.460,-.451]:
 r=float(np.interp(y,[-.460,-.45166],[.0079,.0091]));phi=math.acos((.0181-.0137)/r)
 arc=[(cx+r*math.sin(a),.0181-r*math.cos(a)) for a in np.linspace(-phi,phi,25)]
 profile=[(cx-.0152,-.004),(cx-.0152,.0115),(cx-.0132,.0137)]+arc+[(cx+.0132,.0137),(cx+.0152,.0115),(cx+.0152,-.004)]
 saddle.append((y,profile))
base=loft('H39_ContinuousTubeSaddle',saddle,coat,.00022);parts=[base]
for side in [-1,1]:
 ear=side_profile('H39_PivotEar',[(-.478,-.003),(-.453,-.003),(-.455,-.012),(-.461,-.020),(-.472,-.020),(-.478,-.010)],.0025,coat,.0004)
 for q in ear.data.vertices:q.co.x+=side*.01276
 parts.append(ear)
for x in [cx-.01276,cx+.01276]:parts.append(cylinder('H39_PivotBoss',(x,-.46498,-.01398),.0058,.005,'X',coat))
base=join('BipodBase_H39',parts,None)
select([base]);basefbx=O/'Exports/SM_LMG201_H39_BipodBase.fbx';bpy.ops.export_scene.fbx(filepath=str(basefbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
base.hide_render=True;base.hide_set(True)

# New hard-surface helpers remove degenerate faces before freezing their normals.
# Existing Receiver/Handguard corner normals and masks never pass through BMesh.
retained=[bpy.data.objects[name] for name in ['CarryHandle','TriggerGuard_Fitted','RearSightBase_Fitted']]
select(new+retained+[rig]);fbx=O/'Exports/SK_LMG201_H39_BodyParts.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_HardSurface39.blend'))
(O/'model.json').write_text(json.dumps({'status':'authored','body_fbx':str(fbx),'base_fbx':str(basefbx),'body_parts':[o.name for o in new],'retained_shared_slot_parts':[o.name for o in retained],'material_roles':roles,'panels':report,'bipod_pivots_preserved':[[.01356,-.46498,-.01398],[-.01196,-.46498,-.01398]],'bipod_legs_modified':False},indent=2));print('H39_SOURCE_SAVED',flush=True)
