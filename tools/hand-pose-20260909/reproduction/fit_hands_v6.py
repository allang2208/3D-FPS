import bpy,bmesh,json,struct,pathlib,os,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=pathlib.Path(__file__).parent
raw=pathlib.Path('E:/3d/3-dfps/assets/models/infima/infima_ar.glb').read_bytes();jl=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+jl]);binary=bytearray(raw[28+jl:])
anim=json.dumps(doc['animations'],sort_keys=True)
def read(i):
 a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];f={5126:'f',5123:'H',5125:'I',5121:'B'}[a['componentType']];s=struct.calcsize(f)*n;o=v.get('byteOffset',0)+a.get('byteOffset',0)
 return np.array([struct.unpack_from('<'+f*n,binary,o+j*v.get('byteStride',s)) for j in range(a['count'])])
def write(rows,kind,ctype=5126):
 rows=np.asarray(rows);rows=rows.reshape(len(rows),-1)
 while len(binary)%4:binary.append(0)
 offset=len(binary);data=rows.astype({5126:'<f4',5123:'<u2',5125:'<u4'}[ctype]).tobytes();binary.extend(data)
 vi=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
 a={'bufferView':vi,'componentType':ctype,'count':len(rows),'type':kind}
 if kind=='VEC3':a.update(min=rows.min(axis=0).tolist(),max=rows.max(axis=0).tolist())
 ai=len(doc['accessors']);doc['accessors'].append(a);return ai
node=next(n for n in doc['nodes'] if n.get('name')=='SK_FP_CH_Default_Cubic');skin=doc['skins'][node['skin']];names=[doc['nodes'][i]['name'] for i in skin['joints']]
rests={n:np.linalg.inv(m.reshape(4,4).T)[:3,3] for n,m in zip(names,read(skin['inverseBindMatrices']))}
weapon=os.environ.get('HANDS_WEAPON','infima_ar')
rig_profile=json.loads((OUT/'hand-rigs.json').read_text())[weapon]
rests={n:np.array(v) for n,v in rig_profile['rests'].items()}
prims=doc['meshes'][node['mesh']]['primitives']
for p in prims:
 a={k:read(v) for k,v in p['attributes'].items()};idx=read(p['indices']).astype(int).reshape(-1,3)
 hand_ids={i for i,n in enumerate(names) if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))}
 ishand=np.array([sum(w for j,w in zip(js,ws) if int(j) in hand_ids)>.5 for js,ws in zip(a['JOINTS_0'],a['WEIGHTS_0'])])
 p['indices']=write(idx[~np.all(ishand[idx],axis=1)].reshape(-1,1),'SCALAR',5125)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'source/hand-prepared.blend'),load_ui=False,use_scripts=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST'
src={b.name:np.array(b.head_local) for b in rig.data.bones}
src['Bone.017']=src['Bone.017']*.45+src['Bone.018']*.55
chains={'index':['Bone.005','Bone.006','Bone.007'],'middle':['Bone.008','Bone.009','Bone.010'],'ring':['Bone.011','Bone.012','Bone.013'],'pinky':['Bone.014','Bone.015','Bone.016'],'thumb':['Bone.017','Bone.018','Bone.019']}
def unit(v):return v/np.linalg.norm(v)
def basis(direction,normal):
 y=unit(direction);x=unit(np.cross(y,normal));z=np.cross(x,y);return np.column_stack([x,y,z])
def segment_distance(p,a,b):
 d=b-a;t=np.clip(np.dot(p-a,d)/np.dot(d,d),0,1);return np.linalg.norm(p-a-t*d)
def anatomical_cut(p,influences):
 values=[]
 for f,chain in chains.items():
  points=[src[n] for n in chain]+[np.array(rig.data.bones[chain[-1]].tail_local)]
  start,end=(points[1],points[2]) if f=='thumb' else (points[0],points[1])
  cut=start+(end-start)*(.18 if f=='thumb' else .72)
  distance=min(segment_distance(p,a,b) for a,b in zip(points,points[1:]))
  mass=sum(w for n,w in influences if n in chain)
  values.append(min(np.dot(p-cut,unit(end-start)),(.72 if f=='thumb' else .65)-distance,(mass-.45)*2))
 return .55+max(values)
source_normal=unit(np.cross(src['Bone.005']-src['Bone.014'],src['Bone.008']-src['Bone']))
materials=[]
for label,color,rough in [('Donor skin',[.48,.285,.195,1],.57),('Donor nails',[.60,.39,.30,1],.31)]:
 materials.append(len(doc['materials']));doc['materials'].append({'name':label,'pbrMetallicRoughness':{'baseColorFactor':color,'metallicFactor':0,'roughnessFactor':rough},'doubleSided':True})
glove_material=len(doc['materials']);doc['materials'].append({'name':'Fitted fingerless glove','pbrMetallicRoughness':{'baseColorFactor':[.022,.027,.02,1],'metallicFactor':0,'roughnessFactor':.88},'doubleSided':True})
hem_material=len(doc['materials']);doc['materials'].append({'name':'Bound glove openings','pbrMetallicRoughness':{'baseColorFactor':[.032,.037,.027,1],'metallicFactor':0,'roughnessFactor':.82},'doubleSided':True})
manifest=json.loads((OUT/'bake-manifest.json').read_text())
donor_materials={}
def embed_image(filename):
 while len(binary)%4:binary.append(0)
 data=(OUT/'baked'/filename).read_bytes();vi=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)});binary.extend(data)
 ii=len(doc.setdefault('images',[]));doc['images'].append({'name':filename,'bufferView':vi,'mimeType':'image/png'})
 ti=len(doc.setdefault('textures',[]));doc['textures'].append({'source':ii});return ti
for name,maps in manifest.items():
 donor_materials[name]=len(doc['materials']);doc['materials'].append({'name':'Baked donor '+name,'pbrMetallicRoughness':{'baseColorTexture':{'index':embed_image(maps['DIFFUSE'])},'baseColorFactor':[.60,.49,.36,1],'metallicFactor':0,'roughnessFactor':.65 if name.endswith('.002') else .42},'normalTexture':{'index':embed_image(maps['NORMAL']),'scale':.18},'doubleSided':True})
def append_primitive(rows,material):
 if not rows:return
 assert np.isfinite(np.asarray(rows)).all()
 p=[];n=[];uv=[];jj=[];ww=[]
 for row in rows:
  p.append(row[:3]);n.append(unit(row[3:6]));uv.append(row[6:8]);weight=row[8:];ids=np.argsort(weight)[-4:][::-1];values=weight[ids];values/=values.sum();jj.append(ids);ww.append(values)
 attrs={'POSITION':write(p,'VEC3'),'NORMAL':write(n,'VEC3'),'TEXCOORD_0':write(uv,'VEC2'),'JOINTS_0':write(jj,'VEC4',5123),'WEIGHTS_0':write(ww,'VEC4')}
 prims.append({'attributes':attrs,'indices':write(np.arange(len(rows)).reshape(-1,1),'SCALAR',5125),'material':material})
def clip_polygon(poly,inside):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ain=(a[1]>=.55)==inside;bin=(b[1]>=.55)==inside
  if ain:result.append(a)
  if ain!=bin:
   t=(.55-a[1])/(b[1]-a[1]);result.append((a[0]*(1-t)+b[0]*t,.55))
 return result
def append_bound_hem(segments):
 # Weld contour intersections into loops, then make continuous rounded binding.
 points={};neighbors={}
 def key(row):return tuple(np.round(row[:3],6))
 for a,b in segments:
  ka,kb=key(a),key(b)
  if ka==kb:continue
  points[ka]=a;points[kb]=b;neighbors.setdefault(ka,set()).add(kb);neighbors.setdefault(kb,set()).add(ka)
 unused=set(points);triangles=[];loops=0
 while unused:
  start=next(iter(unused));path=[start];previous=None;current=start
  for _ in range(len(points)+1):
   unused.discard(current);options=neighbors[current]-({previous} if previous is not None else set())
   if not options:break
   nxt=next(iter(options))
   if nxt==start:break
   if nxt in path:break
   path.append(nxt);previous,current=current,nxt
  if len(path)<4 or start not in neighbors[path[-1]]:continue
  loops+=1;rings=[]
  for i,k in enumerate(path):
   row=points[k];normal=unit(row[3:6]);tangent=unit(points[path[(i+1)%len(path)]][:3]-points[path[i-1]][:3]);across=unit(np.cross(tangent,normal));ring=[]
   for j in range(8):
    angle=j*np.pi/4;radial=normal*np.cos(angle)+across*np.sin(angle);v=row.copy();v[:3]+=normal*.00065+radial*.00065;v[3:6]=radial;v[6:8]=[i/len(path),j/8];ring.append(v)
   rings.append(ring)
  for i in range(len(rings)):
   for j in range(8):
    a=rings[i][j];b=rings[(i+1)%len(rings)][j];c=rings[(i+1)%len(rings)][(j+1)%8];d=rings[i][(j+1)%8];triangles.extend([a,b,c,a,c,d])
 append_primitive(triangles,hem_material)
 return loops
report=[]
for side in ['l','r']:
 target={n:rests[n+'_'+side] for n in ['hand']+[f'{f}_{i:02}' for f in chains for i in range(1,4)]}
 # Fit palm to source wrist and knuckle landmarks; preserve thickness with a fourth dimension.
 sn=np.array([src['Bone'],src['Bone.005'],src['Bone.008'],src['Bone.014']]);tn=np.array([target['hand'],target['index_01'],target['middle_01'],target['pinky_01']])
 normal=unit(np.cross(tn[1]-tn[3],tn[2]-tn[0]));normal*=1 if side=='r' else -1
 scale=np.linalg.norm(tn[2]-tn[0])/np.linalg.norm(sn[2]-sn[0])
 sn=np.vstack([sn,sn[0]+source_normal*3]);tn=np.vstack([tn,tn[0]+normal*3*scale])
 palm=np.linalg.lstsq(np.column_stack([sn,np.ones(len(sn))]),tn,rcond=None)[0]
 transforms={b.name:palm for b in rig.data.bones};mapping={b.name:'hand_'+side for b in rig.data.bones}
 for f,chain in chains.items():
  for k,bn in enumerate(chain):
   sh=src[bn];st=src[chain[k+1]] if k<2 else np.array(rig.data.bones[bn].tail_local)
   th=target[f'{f}_{k+1:02}'];tt=target[f'{f}_{k+2:02}'] if k<2 else th+unit(th-target[f'{f}_02'])*np.linalg.norm(th-target[f'{f}_02'])*.8
   sf=basis(st-sh,source_normal);tf=basis(tt-th,normal)
   linear=tf@np.diag([scale,np.linalg.norm(tt-th)/np.linalg.norm(st-sh),scale])@sf.T
   transforms[bn]=np.vstack([linear.T,th-linear@sh]);mapping[bn]=f'{f}_{k+1:02}_{side}'
 # Smooth landmark warp avoids discontinuities between palm and phalanx fitting frames.
 controls=[src['Bone']];destinations=[target['hand']]
 for f,chain in chains.items():
  for k,bn in enumerate(chain):controls.append(src[bn]);destinations.append(target[f'{f}_{k+1:02}'])
  bn=chain[-1];controls.append(np.array(rig.data.bones[bn].tail_local));th=target[f'{f}_03'];destinations.append(th+(th-target[f'{f}_02'])*.8)
 c0=np.array(controls);d0=np.array(destinations)
 controls=np.vstack([c0,c0+source_normal*.65,c0-source_normal*.65]);destinations=np.vstack([d0,d0+normal*.65*scale,d0-normal*.65*scale])
 kernel=np.linalg.norm(controls[:,None,:]-controls[None,:,:],axis=2);aff=np.column_stack([controls,np.ones(len(controls))])
 system=np.block([[kernel,aff],[aff.T,np.zeros((4,4))]])
 solution=np.linalg.solve(system,np.vstack([destinations,np.zeros((4,3))]))
 def warp(p):return np.append(p,1)@palm
 def thumb_volume(p):
  chain=chains['thumb'];sp=[src[n] for n in chain]+[np.array(rig.data.bones[chain[-1]].tail_local)]
  tp=[target[f'thumb_{i:02}'] for i in range(1,4)];tp.append(tp[-1]+(tp[-1]-tp[-2])*.8)
  candidates=[]
  for k in range(3):
   axis=sp[k+1]-sp[k];t=np.clip(np.dot(p-sp[k],axis)/np.dot(axis,axis),0,1);c=sp[k]+t*axis;candidates.append((np.linalg.norm(p-c),k,t,c))
  _,k,t,c=min(candidates,key=lambda r:r[0])
  def smooth_tangent(points):
   directions=[unit(points[i+1]-points[i]) for i in range(3)]
   a=directions[k] if k==0 else unit(directions[k-1]+directions[k])
   b=directions[k] if k==2 else unit(directions[k]+directions[k+1])
   return unit(a*(1-t)+b*t)
  sf=basis(smooth_tangent(sp),source_normal);tf=basis(smooth_tangent(tp),normal)
  radial=sf.T@(p-c)
  if side=='l':radial[0]*=-1
  return tp[k]*(1-t)+tp[k+1]*t+tf@radial*scale*1.12
 def finger_volume(p,f):
  chain=chains[f];sp=[src[n] for n in chain]+[np.array(rig.data.bones[chain[-1]].tail_local)]
  tp=[target[f'{f}_{i:02}'] for i in range(1,4)];tp.append(tp[-1]+(tp[-1]-tp[-2])*.8)
  candidates=[]
  for k in range(3):
   axis=sp[k+1]-sp[k];t=np.clip(np.dot(p-sp[k],axis)/np.dot(axis,axis),0,1);c=sp[k]+t*axis;candidates.append((np.linalg.norm(p-c),k,t,c))
  _,k,t,c=min(candidates,key=lambda r:r[0])
  def tangent(points):
   ds=[unit(points[i+1]-points[i]) for i in range(3)]
   a=ds[k] if k==0 else unit(ds[k-1]+ds[k]);b=ds[k] if k==2 else unit(ds[k]+ds[k+1])
   return unit(a*(1-t)+b*t)
  radial=basis(tangent(sp),source_normal).T@(p-c)
  if side=='l':radial[0]*=-1
  radius=.82 if side=='r' and f=='index' else .94
  position=tp[k]*(1-t)+tp[k+1]*t+basis(tangent(tp),normal)@radial*scale*radius
  # The fitting coordinate and the skinning transition use the same joint stations.
  lengths=np.array([np.linalg.norm(b-a) for a,b in zip(sp,sp[1:])]);stations=np.concatenate([[0],np.cumsum(lengths)]);s=stations[k]+t*lengths[k]
  weights=np.zeros(4);weights[k+1]=1
  for j,joint in enumerate(stations[:3]):
   width=lengths[max(0,j-1)]*(.22 if j==0 else .20)
   if abs(s-joint)<width:
    u=np.clip((s-joint+width)/(2*width),0,1);u=u*u*(3-2*u);weights[:]=0;weights[j]=1-u;weights[j+1]=u;break
  return position,weights
 for obj in [o for o in bpy.data.objects if o.type=='MESH']:
  obj.hide_viewport=False;obj.hide_set(False)
  for m in obj.modifiers:
   if m.type=='ARMATURE':m.show_viewport=False
   if m.type=='MULTIRES':m.levels=min(1,m.total_levels)
  bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
  to_rig=rig.matrix_world.inverted()@obj.matrix_world;verts=[];joints=[];weights=[];cut_values=[]
  for v in mesh.vertices:
   p=np.append(np.array(to_rig@v.co),1);influences=[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups if obj.vertex_groups[g.group].name in transforms and g.weight>1e-5]
   if not influences:influences=[('Bone',1.)]
   cut_values.append(anatomical_cut(p[:3],influences))
   # The donor metacarpal originally starts at the wrist. Reweight its proximal
   # portion to the palm after moving the virtual CMC landmark, to avoid a web
   # of wrist/palm vertices being pulled rigidly by thumb_01 during opposition.
   thumb_chain=chains['thumb'];thumb_mass=sum(w for n,w in influences if n in thumb_chain)
   if thumb_mass>1e-6:
    points=[src[n] for n in thumb_chain]+[np.array(rig.data.bones[thumb_chain[-1]].tail_local)]
    lengths=np.array([np.linalg.norm(b-a) for a,b in zip(points,points[1:])]);starts=np.concatenate([[0],np.cumsum(lengths)])
    candidates=[]
    for k,(a,b) in enumerate(zip(points,points[1:])):
     axis=b-a;u=np.clip(np.dot(p[:3]-a,axis)/np.dot(axis,axis),0,1)
     candidates.append((np.linalg.norm(p[:3]-a-u*axis),starts[k]+u*lengths[k]))
    distance,s=min(candidates)
    thumb_weights=np.zeros(4);thumb_weights[1+min(2,int(np.searchsorted(starts[1:3],s)))]=1
    for k,joint in enumerate(starts[:3]):
     width=.25 if k==0 else .16
     if abs(s-joint)<width:
      u=np.clip((s-joint+width)/(2*width),0,1);u=u*u*(3-2*u);thumb_weights[:]=0;thumb_weights[k]=1-u;thumb_weights[k+1]=u;break
    influences=[(n,w) for n,w in influences if n not in thumb_chain]+[(n,thumb_mass*w) for n,w in zip(['Bone']+thumb_chain,thumb_weights) if w>1e-6]
   total=sum(w for n,w in influences);pos=warp(p[:3])
   thumb_u=np.clip(np.dot(p[:3]-src['Bone.017'],src['Bone.018']-src['Bone.017'])/np.linalg.norm(src['Bone.018']-src['Bone.017'])**2,0,1)
   correction=np.clip((thumb_mass-.25)/.65,0,1)*np.clip(thumb_u/.75,0,1);correction=correction*correction*(3-2*correction)
   if correction>0:pos=pos*(1-correction)+thumb_volume(p[:3])*correction
   for f,chain in chains.items():
    if f=='thumb':continue
    mass=sum(w for n,w in influences if n in chain)
    if mass<1e-6:continue
    corrected,fw=finger_volume(p[:3],f)
    blend=np.clip((mass-.20)/.65,0,1);blend=blend*blend*(3-2*blend)
    pos=pos*(1-blend)+corrected*blend
    influences=[(n,w) for n,w in influences if n not in chain]+[(n,mass*w) for n,w in zip(['Bone']+chain,fw) if w>1e-6]
   # Keep the central palm on the palm bone; only the thumb-side transition
   # participates in opposition. The donor metacarpal originally began at wrist.
   t=np.clip((thumb_u-.30)/.55,0,1);t=t*t*(3-2*t)
   root_mass=sum(w for n,w in influences if n=='Bone.017')
   influences=[(n,w*t if n=='Bone.017' else w) for n,w in influences]
   influences.append(('Bone',root_mass*(1-t)))
   verts.append(pos)
   sums={}
   for n,w in influences:
    j=names.index(mapping[n]);sums[j]=sums.get(j,0)+w/total
   inf=sorted(sums.items(),key=lambda x:-x[1])[:4];den=sum(w for j,w in inf);joints.append([j for j,w in inf]+[0]*(4-len(inf)));weights.append([w/den for j,w in inf]+[0]*(4-len(inf)))
  if len(obj.data.vertices)>100:
   # Fair the continuous palm/web surface with fixed fingertip and cuff regions.
   # Alternating steps retain volume while removing fitting-frame ridges.
   edges=np.array([(e.vertices[0],e.vertices[1]) for e in mesh.edges],dtype=int)
   aa=np.concatenate([edges[:,0],edges[:,1]]);bb=np.concatenate([edges[:,1],edges[:,0]])
   count=np.maximum(1,np.bincount(aa,minlength=len(verts)))
   palm_ids=[names.index('hand_'+side),names.index('thumb_01_'+side)]
   mass=np.array([sum(w for j,w in zip(js,ws) if j in palm_ids) for js,ws in zip(joints,weights)])
   blend=np.clip((mass-.20)/.60,0,1);blend=blend*blend*(3-2*blend)
   positions=np.array(verts)
   for iteration in range(40):
    for step in [.5,-.53]:
     average=np.column_stack([np.bincount(aa,weights=positions[bb,k],minlength=len(verts))/count for k in range(3)])
     positions+=(average-positions)*blend[:,None]*step
   verts=list(positions)
  if len(obj.data.vertices)>100:
   pose_matrices=np.array([rig_profile['held'].get(n,np.eye(4).tolist()) for n in names])
   vertex_matrices=np.array([sum(pose_matrices[j]*w for j,w in zip(js,ws)) for js,ws in zip(joints,weights)])
   held_positions=np.einsum('nij,nj->ni',vertex_matrices,np.column_stack([verts,np.ones(len(verts))]))[:,:3]
   hand_id=names.index('hand_'+side);thumb_id=names.index('thumb_01_'+side)
   mass=np.array([sum(w for j,w in zip(js,ws) if j in [hand_id,thumb_id]) for js,ws in zip(joints,weights)])
   selected=np.where((mass>.75)&(np.array(cut_values)<.55))[0]
   bm=bmesh.new()
   for i in selected:bm.verts.new(held_positions[i])
   hull=bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
   bmesh.ops.delete(bm,geom=hull['geom_unused'],context='VERTS');bm.normal_update();tree=BVHTree.FromBMesh(bm)
   center=held_positions[selected].mean(axis=0);count=0
   corrected_positions=held_positions.copy()
   for i,position in enumerate(held_positions):
    blend=np.clip((mass[i]-.45)/.40,0,1);blend=blend*blend*(3-2*blend)
    if blend<.001 or cut_values[i]>=.55:continue
    direction=position-center;distance=np.linalg.norm(direction)
    if distance<1e-6:continue
    hit,normal_hit,face,length=tree.ray_cast(Vector(center),Vector(direction/distance),1.0)
    if hit is None or length<=distance:continue
    corrected=position+(np.array(hit)-position)*blend
    corrected_positions[i]=corrected;count+=1
   blend=np.clip((mass-.45)/.40,0,1);blend=blend*blend*(3-2*blend)
   for iteration in range(35):
    for step in [.5,-.53]:
     average=np.column_stack([np.bincount(aa,weights=corrected_positions[bb,k],minlength=len(verts))/np.maximum(1,np.bincount(aa,minlength=len(verts))) for k in range(3)])
     corrected_positions+=(average-corrected_positions)*blend[:,None]*step
   for i in range(len(verts)):
    if blend[i]<=.001:continue
    dense={j:w*(1-blend[i]) for j,w in zip(joints[i],weights[i])}
    dense[hand_id]=dense.get(hand_id,0)+blend[i]
    pairs=sorted(dense.items(),key=lambda x:-x[1])[:4];den=sum(w for j,w in pairs)
    joints[i]=[j for j,w in pairs]+[0]*(4-len(pairs));weights[i]=[w/den for j,w in pairs]+[0]*(4-len(pairs))
    corrected_matrix=sum(pose_matrices[j]*w for j,w in zip(joints[i],weights[i]))
    verts[i]=(np.linalg.inv(corrected_matrix)@np.append(corrected_positions[i],1))[:3]
   bm.free();print('CONTINUOUS_PALM_ENVELOPE',weapon,side,count)
  # Recalculate geometric normals after fitting, preserving the donor UV seams.
  fitted=bpy.data.meshes.new('Fitted');fitted.from_pydata(verts,[],[list(p.vertices) for p in mesh.polygons]);fitted.update();fitted.calc_loop_triangles()
  positions=[];normals=[];js=[];ws=[];uvs=[];exposure=[]
  for tri in fitted.loop_triangles:
   order=list(tri.loops)
   if side=='l':order.reverse()
   for li in order:
    vi=fitted.loops[li].vertex_index;positions.append(verts[vi]);n=np.array(fitted.vertices[vi].normal);normals.append(n*(-1 if side=='l' else 1));js.append(joints[vi]);ws.append(weights[vi]);uvs.append(list(mesh.uv_layers.active.data[li].uv) if mesh.uv_layers.active else [0,0])
    exposure.append(cut_values[vi])
  rows=[]
  for p,n,uv,jv,wv in zip(positions,normals,uvs,js,ws):
   dense=np.zeros(len(names))
   for ji,wi in zip(jv,wv):dense[ji]+=wi
   rows.append(np.concatenate([p,n,[uv[0],1-uv[1]],dense]))
  if len(obj.data.vertices)>100:
   segments=[]
   for i in range(0,len(rows),3):
    crossings=[]
    for ka,kb in [(i,i+1),(i+1,i+2),(i+2,i)]:
     if (exposure[ka]>=.55)!=(exposure[kb]>=.55):
      t=(.55-exposure[ka])/(exposure[kb]-exposure[ka]);crossings.append(rows[ka]*(1-t)+rows[kb]*t)
    if len(crossings)==2:segments.append(crossings)
   for inside,mat in [(True,donor_materials[obj.name]),(False,glove_material)]:
    output=[]
    for i in range(0,len(rows),3):
     poly=clip_polygon([(rows[k],exposure[k]) for k in range(i,i+3)],inside)
     for k in range(1,len(poly)-1):
      for row,_ in [poly[0],poly[k],poly[k+1]]:
       row=row.copy()
       if not inside:row[:3]+=unit(row[3:6])*.0009
       output.append(row)
    append_primitive(output,mat)
   hem_count=append_bound_hem(segments);assert hem_count==5,(side,hem_count);print('CLOSED_GLOVE_HEMS',side,hem_count)
  else:append_primitive(rows,donor_materials[obj.name])
  report.append({'side':side,'source':obj.name,'vertices':len(verts),'triangles':len(positions)//3});evaluated.to_mesh_clear();bpy.data.meshes.remove(fitted)
assert json.dumps(doc['animations'],sort_keys=True)==anim
doc['buffers'][0]['byteLength']=len(binary);j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary.extend(b'\0'*((-len(binary))%4))
(OUT/('hands-'+weapon+'-v3.glb')).write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary)
(OUT/('hands-'+weapon+'-v3-report.json')).write_text(json.dumps({'meshes':report,'original_animation_json_unchanged':True,'original_buffer_prefix_unchanged':bytes(binary[:len(raw)-28-jl])==raw[28+jl:]},indent=2))
print('FIT_CANDIDATE_OK',report)
