"""Reference-guided receiver skins, swept guard and native-pivot bipod collars.
Game art only. Authoring/export does not run a scene or visual acceptance.
"""
from pathlib import Path
O=Path(__file__).parent;S=O.parent
helpers=(S/'Assembly40/model.py').read_text().split('# Preserve the edited receiver')[0]
helpers=helpers.replace('HardSurface39/LMG201_HardSurface39.blend','SightFinish41/LMG201_SightFinish41.blend').replace(".replace('M_LMG201_R38_','M_LMG201_A40_')",".replace('M_LMG201_R38_','M_LMG201_S42_')")
exec(compile(helpers,str(O/'model.py'),'exec'),globals())
for mat in [coat,satin]:
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.02810,.03179,.03532,1);bs.inputs['Roughness'].default_value=.357 if mat==coat else .32;bs.inputs['Metallic'].default_value=.73
previous=json.loads((S/'SightFinish41/model.json').read_text())
parts=[bpy.data.objects[n] for n in previous['parts'] if n not in ['Receiver','TriggerGuard_S41','Trigger_S41']]
for name in ['TriggerGuard_S41','Trigger_S41']:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)

def rounded(poly,r=.001,steps=6):
 out=[];p=[Vector(q) for q in poly]
 for i,c in enumerate(p):
  a=p[(i-1)%len(p)]-c;b=p[(i+1)%len(p)]-c;d=min(r,a.length*.24,b.length*.24);a=c+a.normalized()*d;b=c+b.normalized()*d
  for t in np.linspace(0,1,steps,endpoint=False):out.append(tuple((1-t)**2*a+2*(1-t)*t*c+t*t*b))
 return out

def sideplate(name,poly,x0,x1,mat=coat,bevel=0):
 return displaced(slab(name,poly,abs(x1-x0)/2,mat,bevel),(x0+x1)/2-cx)

def recess(ob,poly,side,face,depth=.0018):
 cut=sideplate('S42_BlindRecess',poly,side*(face-depth),side*(face+.014),coat)
 boolean(ob,cut,'DIFFERENCE')

def screw(name,side,y,z,face,r=.0024):
 ob=cylinder(name,(side*(face+.0001),y,z),r,.0014,'X',satin)
 cut=box(name+'_Slot',(side*(face+.0008),y,z),(.00075,r*1.25,.0006),satin,0);boolean(ob,cut,'DIFFERENCE');finish(ob,.00010);return ob

# Cut only exterior skins. The original receiver core, tray interfaces, UVs,
# corner normals and bottom attachment geometry remain in the native frame.
rec=bpy.data.objects['Receiver'];localize(rec);rec.data.materials.append(coat);newmid=len(rec.data.materials)-1
for side in [-1,1]:
 cut=box('S42_RemoveUnevenSide',(side*.050,-.085,.037),(.070,.298,.075),coat,0)
 cut.data.materials.clear()
 for mat in rec.data.materials:cut.data.materials.append(mat)
 for p in cut.data.polygons:p.material_index=newmid
 boolean(rec,cut,'DIFFERENCE')
rec.data.update();ns=[n.vector.copy() for n in rec.data.corner_normals]
for p in rec.data.polygons:
 if p.material_index==newmid:
  for i in p.loop_indices:ns[i]=p.normal.copy()
rec.data.normals_split_custom_set(ns);bind(rec,'WPN_root');parts.append(rec)

panels=[]
rear=rounded([(-.1125,.0015),(.057,.0015),(.066,.008),(.066,.059),(.057,.0748),(-.1125,.0748)],.0022)
for side in [1,-1]:
 face=.0213 if side==1 else .0217
 ob=sideplate('S42_ReceiverLeft' if side==1 else 'S42_ReceiverRight',rear,side*.0138,side*face)
 for ya,yb in [(-.094,-.037),(-.031,.0285)]:recess(ob,round_profile(ya,yb,.051,.068,.0032,10),side,face,.0020)
 if side==1:
  # Two reference recesses define the oblique lower stiffener; both are blind.
  recess(ob,rounded([(-.108,.0375),(-.053,.0375),(-.050,.033),(-.087,.0095),(-.108,.0095)],.0027),side,face,.0020)
  recess(ob,rounded([(-.063,.012),(-.031,.0375),(-.006,.0375),(.038,.0145),(.038,.0105),(-.060,.0105)],.0030),side,face,.0020)
  recess(ob,rounded([(.028,.039),(.048,.039),(.048,.018)],.0018),side,face,.0016)
 else:
  # Opposite face carries two straight stepped ribs, not mirrored Z relief.
  for z,w,deep in [(.034,.0105,.0062),(.016,.0090,.0065)]:
   rib=sideplate('S42_RightLongStiffener',round_profile(-.109,.063,z-w/2,z+w/2,.0028,10),-.0212,-(.0217+deep),coat,.00065);panels.append(rib)
 finish(ob,.00048);panels.append(ob)
 for y,z,r in [(.055,.062,.0038),(.055,.013,.0038),(-.098,.050,.0016),(-.034,.049,.0016),(.0315,.049,.0016)]:panels.append(screw('S42_ReceiverFastener',side,y,z,face,r))

# The front receiver shoulder meets the handguard and the original lid seam.
front=rounded([(-.2358,.022),(-.223,.060),(-.211,.0685),(-.177,.0685),(-.177,.0085),(-.231,.0085)],.0015)
for side in [1,-1]:
 face=.0308;ob=sideplate('S42_FrontShoulder',front,side*.0138,side*face)
 if side==1:recess(ob,rounded([(-.227,.021),(-.219,.049),(-.211,.057),(-.197,.057),(-.1825,.022)],.0035),side,face,.0016)
 finish(ob,.00055);panels.append(ob)
 for y,z in [(-.224,.052),(-.184,.059)]:panels.append(screw('S42_ShoulderFastener',side,y,z,face,.0031))
 # Short lower return seats this side plate on the existing receiver base.
 panels.append(box('S42_ShoulderReturn',(side*.019,-.204,.010),(.015,.054,.005),coat,.0005))

# Feed-side sill retains the opening. Opposite port has its saved A40 backing.
feed=sideplate('S42_FeedSideSill',round_profile(-.1785,-.1105,.002,.039,.0018,8),.0138,.0258,coat,.0005);panels.append(feed)
for y in [-.177,-.1118]:panels.append(box('S42_FeedJamb',(.0248,y,.0485),(.0058,.0042,.034),coat,.0004))
other=sideplate('S42_OppositePortPlate',round_profile(-.1785,-.1105,.005,.070,.002,8),-.0138,-.0290)
recess(other,round_profile(-.169,-.119,.021,.038,.0026,8),-1,.029,.0018)
window=sideplate('S42_BackedPortOpening',round_profile(-.133,-.111,.0585,.0675,.0013,8),-.012,-.050,inside);boolean(other,window,'DIFFERENCE');finish(other,.00045);panels.append(other)
parts.append(joined('ReceiverSideSkins_S42',panels))

# Swept guard traced to the reference: sloping front, gently bowed underside,
# narrow rear return. The attachment pads enter the existing bottom flanges.
outer=rounded([(-.079,.0045),(-.011,.0045),(-.011,-.0345),(-.016,-.0395),(-.043,-.041),(-.064,-.0395),(-.071,-.036),(-.079,-.005)],.0040,8)
inner=rounded([(-.0752,.0008),(-.0146,.0008),(-.0146,-.0325),(-.018,-.0358),(-.043,-.0372),(-.062,-.036),(-.068,-.033),(-.0752,-.005)],.0030,8)
guard=ring_slab('S42_SweptGuard',outer,inner,.0050,coat)
slot=box('S42_TriggerExit',(cx,-.034,.0035),(.008,.019,.013),inside,.0004);boolean(guard,slot,'DIFFERENCE');finish(guard,.00012)
housing=[guard]
for y0,y1 in [(-.079,-.071),(-.018,-.009)]:housing.append(slab('S42_GuardSeat',rounded([(y0,-.0025),(y1,-.0025),(y1,.006),(y0,.006)],.001),.0078,coat,.00035))
parts.append(joined('TriggerGuard_S42',housing))

# A continuous curved blade joins the original animated root in idle space.
def bezier(a,b,c,d,t):return (1-t)**3*np.array(a)+3*(1-t)**2*t*np.array(b)+3*(1-t)*t*t*np.array(c)+t**3*np.array(d)
line=np.array([bezier((-.028,.01463),(-.024,-.006),(-.034,-.028),(-.039,-.032),t) for t in np.linspace(0,1,40)])
tang=np.gradient(line,axis=0);norm=np.stack([-tang[:,1],tang[:,0]],axis=1);norm/=np.linalg.norm(norm,axis=1)[:,None];width=np.linspace(.0021,.0013,len(line))
profile=np.concatenate([line+norm*width[:,None],(line-norm*width[:,None])[::-1]])
trigger=slab('S42_CurvedBlade',profile.tolist(),.0026,satin,.00035)
rootp=poses['clips']['idle']['bones']['WPN_Trigger']['p'];hub=cylinder('S42_TriggerPivot',(rootp[0],-rootp[1],rootp[2]),.0033,.0065,'X',satin)
trigger=joined('S42_BladeAndPivot',[trigger,hub],None);tm=satin.copy();tm.name='M_LMG201_Trigger_S42';trigger.data.materials.clear();trigger.data.materials.append(tm)
for p in trigger.data.polygons:p.material_index=0
unpose(trigger,'WPN_Trigger');parts.append(joined('Trigger_S42',[trigger],'WPN_Trigger'))

select(parts+[rig]);fbx=O/'Exports/SK_LMG201_S42_Parts.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')

# A compact rounded saddle uses the same tube seat and original leg pivots.
saddle=[]
for y in [-.4778,-.4755,-.459,-.452]:
 r=float(np.interp(y,[-.460,-.45166],[.0079,.0091]));phi=math.acos((.0181-.0137)/r)
 arc=[(cx+r*math.sin(a),.0181-r*math.cos(a)) for a in np.linspace(-phi,phi,25)]
 profile=[(cx-.0128,-.0035),(cx-.0150,.004),(cx-.0150,.0117),(cx-.0128,.0137)]+arc+[(cx+.0128,.0137),(cx+.0150,.0117),(cx+.0150,.004),(cx+.0128,-.0035)]
 saddle.append((y,profile))
baseparts=[loft('S42_RoundedTubeSaddle',saddle,coat,.0004)]
for side in [-1,1]:
 ear=slab('S42_RoundedMountEar',rounded([(-.476,-.001),(-.454,-.001),(-.4555,-.010),(-.4605,-.0198),(-.4695,-.0198),(-.4745,-.011)],.0035,8),.0020,coat,.0004);displaced(ear,side*.0090);baseparts.append(ear)
baseparts.append(cylinder('S42_ContinuousPivotBridge',(cx,-.46498,-.01398),.0038,.0355,'X',satin))
for x in [cx-.0170,cx+.0170]:baseparts.append(cylinder('S42_OuterPivotCap',(x,-.46498,-.01398),.0052,.0015,'X',coat))
base=joined('BipodBase_S42',baseparts,None)
static={'BipodBase':base};staticpaths={}

def world_local(ob):
 xf=ob.matrix_world.copy();ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)

for key,side in [('BipodLegA',1),('BipodLegB',-1)]:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('Before_'+key+'.fbx')),use_anim=False);imported=set(bpy.data.objects)-old
 leg=next(o for o in imported if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_')));world_local(leg)
 leg.data.materials.append(coat);mid=len(leg.data.materials)-1
 cut=box('S42_RemoveRoughLegHead',(0,0,.030),(.15,.15,.110),coat,0);cut.data.materials.clear()
 for m in leg.data.materials:cut.data.materials.append(m)
 for p in cut.data.polygons:p.material_index=mid
 boolean(leg,cut,'DIFFERENCE');leg.data.update();ns=[n.vector.copy() for n in leg.data.corner_normals]
 for p in leg.data.polygons:
  if p.material_index==mid:
   for li in p.loop_indices:ns[li]=p.normal.copy()
 leg.data.normals_split_custom_set(ns)
 # Elliptical transition sections follow actual shaft samples, not foot-to-root
 # extrapolation. The lowest ring overlaps retained shaft below the cut.
 rings=[(0,0,-.003,.0066,.0068),(side*.0025,.001,-.011,.0070,.0070),(side*.0090,.0028,-.020,.0085,.0075),(side*.0160,.0035,-.029,.0102,.0083),(side*.0192,.0035,-.035,.0093,.0079)]
 vs=[];N=40
 for x,y,z,rx,ry in rings:
  for i in range(N):vs.append((x+rx*math.cos(i*math.tau/N),y+ry*math.sin(i*math.tau/N),z))
 fs=[tuple(range(N-1,-1,-1)),tuple((len(rings)-1)*N+i for i in range(N))]+[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(rings)-1) for i in range(N)]
 sleeve=shape('S42_LegTransition',vs,fs,coat,.00025)
 eye=cylinder('S42_LegPivotEye',(0,0,0),.0071,.0072,'X',coat)
 # Seat counterbore exposes the base pin but is a blind visual socket.
 bore=cylinder('S42_PinSeat',(side*.0040,0,0),.0040,.0023,'X',inside);boolean(eye,bore,'DIFFERENCE');finish(eye,.00012)
 head=joined('S42_CleanLegHead',[sleeve,eye],None)
 # Project only new geometry. Retained leg and foot keep source UVs/normals.
 select([leg,head]);bpy.context.view_layer.objects.active=leg;bpy.ops.object.join();leg.name=key+'_S42';static[key]=leg
 for ob in imported:
  if ob!=leg and ob.name in bpy.data.objects:bpy.data.objects.remove(ob,do_unlink=True)

for key,ob in static.items():
 path=O/'Exports'/('SM_LMG201_S42_'+key+'.fbx');select([ob]);bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE');staticpaths[key]=str(path);ob.hide_render=True;ob.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_SurfaceReform42.blend'))
notes={'receiver':'bounded exterior replacement; asymmetric blind recesses, straight right ribs and regular fasteners','trigger':'reference swept guard and smooth blade; native root and pose inverse retained','bipod':'both rough upper collars rebuilt around unchanged pivot; feet and lower shafts retained','native_tracks_changed':False,'material':'new surfaces map to current S41 coat without old atlas normal','tested':False}
(O/'model.json').write_text(json.dumps({'body_fbx':str(fbx),'static_fbx':staticpaths,'parts':[o.name for o in parts],'notes':notes},indent=2));print('S42_SOURCE_SAVED',flush=True)
