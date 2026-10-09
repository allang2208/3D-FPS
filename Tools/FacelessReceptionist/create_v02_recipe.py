from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist')
s=(p/'author_character.py').read_text(encoding='utf-8-sig')
s=s.replace("ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')","BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')\nROOT=BASE/'V02'\nfor folder in ['Authoring','Delivery','Textures','Logs']: (ROOT/folder).mkdir(parents=True,exist_ok=True)\nimport shutil\nfor f in (BASE/'Textures').glob('Source_*.png'): shutil.copy2(f,ROOT/'Textures'/f.name)")
s=s.replace("ROOT/'Authoring/Inputs.blend'","BASE/'Authoring/Inputs.blend'")
s=s.replace("@Matrix.Translation(a)","@Matrix.Translation(-a)")
s=s.replace("['upperarm','lowerarm','thigh','calf','foot','ball']","['upperarm','lowerarm','hand','thigh','calf','foot','ball']")
s=s.replace(" MAP['hand_'+side]=turn(HEAD['hand_'+side],wrist,sign*math.radians(22))",''' # Fit the real donor middle fingertip surface to the source fingertip.
 hand_tip=[]
 for v in donor.data.vertices:
  if any(donor.vertex_groups[g.group].name=='middle_03_'+side and g.weight>.25 for g in v.groups):
   hand_tip.append(donor.matrix_world@v.co)
 hand_tip.sort(key=lambda p:(p-HEAD['hand_'+side]).length,reverse=True)
 donor_tip=sum(hand_tip[:max(1,len(hand_tip)//5)],Vector())/max(1,len(hand_tip)//5)
 src_tip=[v.co.copy() for v in body.data.vertices if sign*v.co.x>.37 and v.co.z<.88]
 src_tip.sort(key=lambda p:p.z)
 source_tip=sum(src_tip[:max(1,len(src_tip)//10)],Vector())/max(1,len(src_tip)//10)
 MAP['hand_'+side]=similarity(HEAD['hand_'+side],donor_tip,wrist,source_tip)''')
a=s.index("points=[v.co.copy()")
b=s.index("body.data.calc_loop_triangles();bodytris",a)
s=s[:a]+'''# The donor's upper legs/hips are absent below its dress. Do not transfer
# those vertices against an unrestricted nearest-surface tree (hands were nearest).
# Torso and leg skin use anatomical joints; fingers alone use side-restricted
# donor surfaces after fitting the hand.
points=[v.co.copy() for v in body.data.vertices]
hand_trees={}
for side in ['l','r']:
 allowed=lambda n:n.endswith('_'+side) and n.startswith(('hand','thumb','index','middle','ring','pinky'))
 wh=[norm({n:w for n,w in ws.items() if allowed(n)}) for ws in dw]
 handtris=[t for t in tri if all(sum(w for n,w in dw[i].items() if allowed(n))>.35 for i in t)]
 hand_trees[side]=(BVHTree.FromPolygons(dp,handtris,all_triangles=True),handtris,wh)
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
spine_names=['pelvis']+sorted(n for n in REST if n.startswith('spine_') and len(n)==8)+['neck_01','neck_02','head']
spine_z=[(MAP[n]@HEAD[n]).z for n in spine_names]
def torso_weights(p):
 if p.z<=spine_z[0]:return {'pelvis':1.}
 for i in range(len(spine_z)-1):
  if p.z<=spine_z[i+1]:
   t=smooth(spine_z[i],spine_z[i+1],p.z)
   return norm({spine_names[i]:1-t,spine_names[i+1]:t})
 return {'head':1.}
def mixweights(a,b,t):
 result={n:w*(1-t) for n,w in a.items()}
 for n,w in b.items():result[n]=result.get(n,0)+w*t
 return norm(result)
def anatomical_weights(p):
 side='l' if p.x>=0 else 'r'
 sign=1 if p.x>=0 else -1
 # Source arms are separated from the hips by over 15 cm.
 threshold=float(np.interp(p.z,[.75,.98,1.12,1.27,1.40,1.48,1.55],[.29,.28,.245,.205,.155,.135,.18]))
 arm_blend=smooth(threshold-.025,threshold+.025,abs(p.x))
 if p.z>1.58:arm_blend=0.
 if arm_blend>0:
  shoulder,elbow,wrist=(Vector(TARGET[side][key]) for key in ['shoulder','elbow','wrist'])
  elbow_blend=smooth(-.05,.05,(p-elbow).dot((wrist-shoulder).normalized()))
  arm=mixweights({'upperarm_'+side:1.},{'lowerarm_'+side:1.},elbow_blend)
  wrist_blend=smooth(-.035,.020,(p-wrist).dot((wrist-elbow).normalized()))
  if wrist_blend>0:
   tree,ht,hw=hand_trees[side]
   hand=sample(p,tree,dp,ht,hw)
   hand={n:w for n,w in hand.items() if n!='pelvis'} or {'hand_'+side:1.}
   arm=mixweights(arm,norm(hand),wrist_blend)
  if arm_blend>=.999:return arm
 else:arm={}
 if p.z>=1.03:core=torso_weights(p)
 else:
  hip=smooth(1.035,.855,p.z)
  knee=smooth(.602,.477,p.z)
  ankle=smooth(.145,.065,p.z)
  ball=smooth(-.008,-.095,p.y)*(1-smooth(.06,.105,p.z))
  core=mixweights({'pelvis':1.},{'thigh_'+side:1.},hip)
  core=mixweights(core,{'calf_'+side:1.},knee)
  foot=mixweights({'foot_'+side:1.},{'ball_'+side:1.},ball)
  core=mixweights(core,foot,ankle)
 return mixweights(core,arm,arm_blend) if arm_blend else core
body_weights=[anatomical_weights(p) for p in points]
''' +s[b:]
s=s.replace("suit=textile('Receptionist_Suit',(.20,.235,.265))","suit=textile('Receptionist_Suit',(.058,.077,.100))")
s=s.replace("leather=textile('Receptionist_Shoes',(.10,.115,.125)","leather=textile('Receptionist_Shoes',(.035,.043,.052)")
a=s.index("levels=np.linspace(1.005")
b=s.index(" # Shirt cuffs occupy",a)
s=s[:a]+'''# A continuous shoulder-to-sleeve shell follows the source body. The V01
# disconnected radial torso/yoke/sleeves had overlapping shoulder boundaries.
def opening(z):
 return float(np.interp(z,[1.005,1.16,1.30,1.42,1.49,1.55],[.001,.002,.038,.072,.080,.058]))
def clothing_surface(name,kind,mat,offset):
 o=body.copy();o.data=body.data.copy();bpy.context.collection.objects.link(o);o.name=name
 o.data.materials.clear();o.data.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(o.data)
 def keep(p):
  if kind=='jacket':
   bottom=1.005-.023*smooth(.26,.36,abs(p.x))
   if p.z<bottom or p.z>1.55:return False
   if p.y<-.008 and abs(p.x)<opening(p.z):return False
   return True
  return p.z>1.024 and p.z<1.567 and abs(p.x)<.205
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if not all(keep(v.co) for v in f.verts)],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00008)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free();active(o)
 dec=o.modifiers.new('TailoredSurfaceTopology','DECIMATE');dec.ratio=.48 if kind=='jacket' else .35;apply(o,dec)
 sm=o.modifiers.new('FabricRelaxation','SMOOTH');sm.factor=.6;sm.iterations=10;apply(o,sm)
 # Project the relaxed fabric back outside the intact source, then add ease.
 for v in o.data.vertices:
  hit=body_bvh.find_nearest(v.co)
  if hit[0] is not None:v.co=hit[0]+hit[1]*offset
 for poly in o.data.polygons:poly.use_smooth=True;poly.material_index=0
 o.data.update()
 sm=o.modifiers.new('TailoredBoundary','SMOOTH');sm.factor=.35;sm.iterations=3;apply(o,sm)
 shell(o,.0028 if kind=='jacket' else .0015)
 parts.append(o);return o
jacket=clothing_surface('Receptionist_Blazer_Continuous','jacket',suit,.017)
clothing_surface('Receptionist_Shirt_Continuous','shirt',shirt,.006)
o=garment_rings('Receptionist_Shirt_CollarStand',np.linspace(1.548,1.579,5),64,lambda z,t:(.052*math.sin(2*math.pi*t),.005-.046*math.cos(2*math.pi*t),z),shirt);shell(o,.002)
for side,sign in [('l',1),('r',-1)]:
 a,e,w=(Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist'])
''' +s[b:]
# Lapels follow front surface coordinates, independent of radial torso fitting.
a=s.index("for sign in [-1,1]:\n vs=[];uv=[]")
b=s.index("\ndef block(",a)
s=s[:a]+'''def frontpoint(x,z,offset):
 hit=body_bvh.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)),.8)
 return Vector((x,(hit[0].y if hit[0] is not None else -.050)-offset,z))
for sign in [-1,1]:
 vs=[];uv=[]
 for j,z in enumerate(np.linspace(1.158,1.534,34)):
  x=opening(z)
  width=float(np.interp(z,[1.158,1.3,1.44,1.466,1.534],[.003,.035,.043,.027,.024]))
  for i in range(7):
   f=i/6;v=frontpoint(sign*(x+width*f),z,.025+.005*math.sin(f*math.pi))
   vs.append(tuple(v));uv.append((f,j/33*2))
 faces=[(j*7+i,j*7+i+1,(j+1)*7+i+1,(j+1)*7+i) for j in range(33) for i in range(6)]
 o=mesh('Receptionist_Lapel_'+str(sign),vs,faces,suit,uv);shell(o,.0025)
 vs=[(sign*.016,-.046,1.577),(sign*.050,-.048,1.569),(sign*.068,-.075,1.516),(sign*.033,-.081,1.536)]
 o=mesh('Receptionist_Shirt_CollarTip_'+str(sign),vs,[(0,1,2,3)],shirt);shell(o,.002)
''' +s[b:]
# Body skin and cloth use the same anatomical function, so nearby cloth cannot
# inherit hands through a nearest-surface query near hip/arm proximity.
s=s.replace("else body_sample(v.co) for v in o.data.vertices]","else anatomical_weights(v.co) for v in o.data.vertices]")
s=s.replace("V01","V02")
# Authoring stage only; export uses dedicated exporter after restoring the rig object frame.
a=s.index("def selected(objs):")
b=s.index("receipt={'stage'",a)
s=s[:a]+s[b:]
s=s.replace("'stage':'authored_and_exported'","'stage':'authored_v02'")
s=s.replace("'source':'Source/","'source':'../Source/")
s=s.replace("'Full original Meshy body preserved in author source and exports.'","'Full original Meshy body preserved. Anatomical trunk/legs, side-restricted hand transfer, continuous jacket shell.'")
s=s.replace("rig.name='root'","rig.name='root'\nrig['source_world_matrix']=[v for row in rig.matrix_world for v in row]")
(p/'author_character_v02.py').write_text(s,encoding='utf-8')
