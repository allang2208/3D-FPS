import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];V2=ROOT.parent/'reward-chest-v2'
SOURCE=ROOT/'TreasureChest_v3.blend'
if not SOURCE.exists():SOURCE=V2/'working/TreasureChest_Refined_v2.blend'
for folder in ('working','previews','reports'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.frame_set(1);arm=bpy.data.objects['GamedevTreasureChestRig']
MAP=Matrix(((0,-.65,0,0),(.65,0,0,0),(0,0,.65,0),(0,0,0,1)))
mats=[bpy.data.materials[n] for n in ['Treasure_BlackIron','Treasure_AntiqueGold','Treasure_Interior']]
removed=[]
for o in list(scene.objects):
 if (o.name.startswith('V3_') and o.name!='V3_Crest_Disc') or o.name.startswith(('Scroll_','Lock_FineScroll','Lid_EndScroll','Lid_EndLeaf')) or (o.name.startswith('Lid_Medallion') and o.name!='Lid_MedallionBase'):
  removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
base=bpy.data.objects.get('Lid_MedallionBase') or bpy.data.objects['V3_Crest_Disc'];base.name='V3_Crest_Disc'
for f in base.data.polygons:f.material_index=0
created=[]
def co(mode,fixed,u,v,d):
 if mode=='front':p=(u,fixed-d,v)
 elif mode=='back':p=(u,fixed+d,v)
 elif mode=='left':p=(fixed-d,u,v)
 elif mode=='right':p=(fixed+d,u,v)
 else:p=(u,v,fixed+d+58*(math.sqrt(max(0,1-(v/74)**2))-1))
 return tuple(MAP@Vector(p))
def finish(name,verts,faces,bone='Root',mat=1):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
 for m in mats:me.materials.append(m)
 uv=me.uv_layers.new(name='UV0_Physical');wear=me.uv_layers.new(name='UV1_ComponentWear');cols=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
 for f in me.polygons:
  f.material_index=mat;f.use_smooth=True
  axis=max(range(3),key=lambda k:abs(f.normal[k]));axes=((1,2),(0,2),(0,1))[axis]
  for j in f.loop_indices:
   p=me.vertices[me.loops[j].vertex_index].co;uv.data[j].uv=(p[axes[0]]/100,p[axes[1]]/100);wear.data[j].uv=(.5,.5);cols.data[j].color=(.08,.2,.2,1)
 o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);o.parent=arm;g=o.vertex_groups.new(name=bone);g.add(list(range(len(me.vertices))),1,'REPLACE');mod=o.modifiers.new('OriginalRigidHinge','ARMATURE');mod.object=arm;created.append(o);return o

def bezier(a,b,c,d,t):return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d

def ribbon(name,mode,fixed,center,scale,mirror=1,bone='Root',mat=1):
 # One uninterrupted C1-continuous S-scroll; mirrored partner has an open gap.
 segments=[((-4.5,-14),(-11.5,-14),(-20.5,-5),(-19.5,4)),((-19.5,4),(-18.5,13),(-10.5,17),(-6.5,12)),((-6.5,12),(-2.5,7),(-9.5,4),(-11.5,7))]
 ps=[]
 for seg in segments:
  vv=[Vector(p) for p in seg]
  for j in range(28):ps.append(bezier(*vv,j/28))
 ps.append(Vector(segments[-1][-1]));verts=[];faces=[];sides=12
 for i,p in enumerate(ps):
  tan=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized();across=Vector((-tan.y,tan.x));t=i/(len(ps)-1)
  width=scale*(.10+1.12*math.sin(math.pi*t)**.65)
  for k in range(sides):
   a=2*math.pi*k/sides;q=p*scale+across*(width*math.cos(a));u=center[0]+mirror*q.x;v=center[1]+q.y;depth=.16+.24*math.sin(a)
   verts.append(co(mode,fixed,u,v,depth))
 for i in range(len(ps)-1):
  for k in range(sides):faces.append((i*sides+k,i*sides+(k+1)%sides,(i+1)*sides+(k+1)%sides,(i+1)*sides+k))
 faces.extend([tuple(range(sides-1,-1,-1)),tuple(range((len(ps)-1)*sides,len(ps)*sides))]);return finish(name,verts,faces,bone,mat)

def leaf(name,mode,fixed,start,length,width,angle=0,bone='Root',mat=1,curve=.0):
 # A single closed lenticular blade. No second blade, vein tube or overlapping curl.
 n=32;verts=[];ca,sa=math.cos(angle),math.sin(angle)
 def pos(u,v,d):return co(mode,fixed,start[0]+ca*u-sa*v,start[1]+sa*u+ca*v,d)
 for j in range(n+1):
  t=j/n;w=width*math.sin(math.pi*t)**.85;u0=curve*math.sin(math.pi*t)
  for side in (-1,0,1):verts.append(pos(u0+side*w,length*t,.08+(.48 if side==0 else .08)*math.sin(math.pi*t)))
 faces=[]
 for j in range(n):
  for k in range(2):a=j*3+k;faces.append((a,a+3,a+4,a+1))
 outline=[j*3 for j in range(n+1)]+[j*3+2 for j in range(n,-1,-1)]
 back=[]
 for j in range(n+1):
  t=j/n;w=width*math.sin(math.pi*t)**.85;u0=curve*math.sin(math.pi*t)
  back.append(pos(u0-w,length*t,-.04))
 for j in range(n,-1,-1):
  t=j/n;w=width*math.sin(math.pi*t)**.85;u0=curve*math.sin(math.pi*t)
  back.append(pos(u0+w,length*t,-.04))
 off=len(verts);verts.extend(back);faces.append(tuple(range(off,off+len(back))))
 for i in range(len(outline)):j=(i+1)%len(outline);faces.append((outline[i],outline[j],off+j,off+i))
 return finish(name,verts,faces,bone,mat)

# Three separated elements per large panel: no crossing, piled leaves or tendrils.
for s in (-1,1):
 mode='front' if s<0 else 'back'
 for x in (-66,66):
  for m in (-1,1):ribbon('V3_PanelScroll_%s_%s_%s'%(s,x,m),mode,s*71.65,(x,55),.92,m,mat=1 if s<0 else 0)
  leaf('V3_PanelLeaf_%s_%s'%(s,x),mode,s*71.65,(x,45),22,2.6,mat=1 if s<0 else 0)
for s in (-1,1):
 mode='left' if s<0 else 'right'
 for y in (-43,43):
  for m in (-1,1):ribbon('V3_SideScroll_%s_%s_%s'%(s,y,m),mode,s*95,(y,55),.60,m,mat=0)
  leaf('V3_SideLeaf_%s_%s'%(s,y),mode,s*95,(y,48.5),14,1.7,mat=0)
 # Side cap: scaled openwork rhythm, seated directly against the flat cap.
 for m in (-1,1):ribbon('V3_CapScroll_%s_%s'%(s,m),mode,s*101.02,(0,125),1.30,m,bone='Lid')
 leaf('V3_CapLeaf_'+str(s),mode,s*101.02,(0,111),30,3.1,bone='Lid')
# The lock gets one quiet blade per side, not miniature repeated scroll clusters.
for m in (-1,1):leaf('V3_LockLeaf_'+str(m),'front',-75.58,(m*8,48.5),10.5,1.55,angle=-m*.10,curve=m*.35)
# Crown: one border only and eight detached petals around a clear central space.
N=160;S=12;verts=[];faces=[]
for i in range(N):
 a=2*math.pi*i/N
 for j in range(S):
  b=2*math.pi*j/S;r=24.9+.52*math.cos(b);verts.append(co('top',157.95,r*math.cos(a),r*math.sin(a),.15+.40*math.sin(b)))
for i in range(N):
 for j in range(S):faces.append((i*S+j,i*S+(j+1)%S,((i+1)%N)*S+(j+1)%S,((i+1)%N)*S+j))
finish('V3_Crest_SingleBorder',verts,faces,'Lid')
for i in range(8):
 a=2*math.pi*i/8;start=(6.0*math.cos(a),6.0*math.sin(a));leaf('V3_Crest_Petal_'+str(i),'top',158.0,start,14.8,2.0,angle=a-math.pi/2,bone='Lid',curve=.8)
scene['Revision']='RewardChest_v3_Flowing_Separated_Ornament';scene.frame_set(1)
# Save unchanged texture quality, materials, frame/hinge construction and original action.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'working/TreasureChest_v3_Ornament.blend'))
(ROOT/'reports/ornament_changes.json').write_text(json.dumps({'removed':removed,'created':[o.name for o in created],'principle':'smooth separated ribbons and leaves; one crown border; no added crossing layers'},indent=2))
# Close-up checkpoints only. Full rendering waits for review.
cam=scene.camera;scene.cycles.samples=24;scene.render.resolution_x=1100;scene.render.resolution_y=900
views=[('01_Front_Ornament_Check.png',(230,-42,112),(47,34,36),61),('02_Cap_Ornament_Check.png',(70,-245,125),(0,-65,77),112),('03_Crown_Ornament_Check.png',(130,-135,250),(0,0,103),92),('04_Lock_Ornament_Check.png',(260,-70,116),(47,0,49),64)]
for name,loc,target,scale in views:
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(ROOT/'previews'/name);bpy.ops.render.render(write_still=True)
