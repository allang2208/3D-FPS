"""Author Meshy male security on the intact Nurse skeleton. Background production only."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
body=bpy.data.objects['Security_SourceBody']
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
donor=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body)
rig.animation_data_clear();donor.shape_key_clear()
for p in rig.pose.bones:p.matrix_basis.identity()
REST={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
HEAD={n:m.translation for n,m in REST.items()}
def similarity(a,b,c,d):
 a,b,c,d=map(Vector,(a,b,c,d));u=b-a;v=d-c
 rot=u.rotation_difference(v).to_matrix().to_4x4()
 return Matrix.Translation(c)@rot@Matrix.Scale(v.length/u.length,4)@Matrix.Translation(-a)
def turn(a,target,angle=0,scale=1):
 return Matrix.Translation(Vector(target))@Matrix.Rotation(angle,4,'Y')@Matrix.Scale(scale,4)@Matrix.Translation(-a)
def major(n):
 if n.startswith(('thumb','index','middle','ring','pinky','wrist')):return 'hand_'+n[-1]
 for p in ['upperarm','lowerarm','hand','thigh','calf','foot','ball']:
  if n.startswith(p):return p+'_'+n[-1]
 if n.startswith('clavicle'):return n
 if n in ['pelvis','head','neck_01','neck_02'] or n.startswith('spine_'):return n
 b=rig.data.bones[n]
 return major(b.parent.name) if b.parent else 'pelvis'
MAP={}
for n in REST:
 z=HEAD[n].z
 shift=float(np.interp(z,[0,.1,.55,.987,1.135,1.33,1.453,1.515,1.626,1.83],[0,.105,.57,1.035,1.20,1.39,1.54,1.63,1.70,1.90]))-z
 MAP[n]=Matrix.Translation((0,0,shift))
TARGET={}
for side,sign in [('l',1),('r',-1)]:
 shoulder=Vector((sign*.235,.034,1.525));elbow=Vector((sign*.312,.041,1.265));wrist=Vector((sign*.412,-.010,1.008))
 hip=Vector((sign*.110,.018,1.035));knee=Vector((sign*.157,.020,.580));ankle=Vector((sign*.205,.080,.105));toe=Vector((sign*.240,-.080,.025))
 for part,a,b in [('upperarm',shoulder,elbow),('lowerarm',elbow,wrist),('thigh',hip,knee),('calf',knee,ankle),('foot',ankle,toe)]:
  child={'upperarm':'lowerarm','lowerarm':'hand','thigh':'calf','calf':'foot','foot':'ball'}[part]
  MAP[part+'_'+side]=similarity(HEAD[part+'_'+side],HEAD[child+'_'+side],a,b)
 MAP['ball_'+side]=turn(HEAD['ball_'+side],toe)
 # Fit the real donor middle fingertip surface to the source fingertip.
 hand_tip=[]
 for v in donor.data.vertices:
  if any(donor.vertex_groups[g.group].name=='middle_03_'+side and g.weight>.25 for g in v.groups):
   hand_tip.append(donor.matrix_world@v.co)
 hand_tip.sort(key=lambda p:(p-HEAD['hand_'+side]).length,reverse=True)
 donor_tip=sum(hand_tip[:max(1,len(hand_tip)//5)],Vector())/max(1,len(hand_tip)//5)
 src_tip=[v.co.copy() for v in body.data.vertices if sign*v.co.x>.36 and .73<v.co.z<.88]
 src_tip.sort(key=lambda p:p.z)
 source_tip=sum(src_tip[:max(1,len(src_tip)//10)],Vector())/max(1,len(src_tip)//10)
 MAP['hand_'+side]=similarity(HEAD['hand_'+side],donor_tip,wrist,source_tip)
 MAP['clavicle_'+side]=similarity(HEAD['clavicle_'+side],HEAD['upperarm_'+side],(sign*.012,.020,1.55),shoulder)
 TARGET[side]=dict(shoulder=list(shoulder),elbow=list(elbow),wrist=list(wrist),hip=list(hip),knee=list(knee),ankle=list(ankle),toe=list(toe))
for n in REST:
 m=major(n)
 if m!=n:MAP[n]=MAP[m].copy()
def vertex_weights(o,v):
 return {o.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-7 and o.vertex_groups[g.group].name in REST}
def norm(ws):
 ws={n:w for n,w in sorted(ws.items(),key=lambda kv:-kv[1])[:8] if w>1e-5};t=sum(ws.values())
 return {n:w/t for n,w in ws.items()} if t else {'pelvis':1.}
def matrix(ws):
 a=Matrix(((0,0,0,0),)*4)
 for n,w in ws.items():
  m=MAP[n]
  for r in range(4):
   for c in range(4):a[r][c]+=m[r][c]*w
 return a
# Build the posed anatomical donor surface, excluding nurse clothing, hair and eyes.
dw=[norm(vertex_weights(donor,v)) for v in donor.data.vertices]
dp=[matrix(ws)@(donor.matrix_world@v.co) for v,ws in zip(donor.data.vertices,dw)]
donor.data.calc_loop_triangles()
tri=[tuple(t.vertices) for t in donor.data.loop_triangles if donor.data.polygons[t.polygon_index].material_index in (0,3)]
bvh=BVHTree.FromPolygons(dp,tri,all_triangles=True)
def sample(point,tree,verts,tris,weights):
 hit=tree.find_nearest(point)
 if hit[0] is None:raise RuntimeError('No donor surface at '+str(point))
 ids=tris[hit[2]]
 b=barycentric_transform(hit[0],*(verts[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 b=[max(0.,float(x)) for x in b];total=sum(b);result={}
 for i,f in zip(ids,b):
  for n,w in weights[i].items():result[n]=result.get(n,0)+w*f/total
 return norm(result)
# The donor's upper legs/hips are absent below its dress. Do not transfer
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
 # Compare anatomical surface envelopes, including the front/back distance.
 # A height/x-only blend erroneously mixed inner sleeves with the torso.
 shoulder,elbow,wrist=(Vector(TARGET[side][key]) for key in ['shoulder','elbow','wrist'])
 def seg_distance(a,b):
  t=max(0.,min(1.,(p-a).dot(b-a)/(b-a).length_squared))
  return (p-a.lerp(b,t)).length
 arm_metric=min(seg_distance(shoulder,elbow)/.084,seg_distance(elbow,wrist)/.062,
                (p-wrist).length/.16 if p.z<wrist.z else 1e6)
 rx=float(np.interp(p.z,[.8,1.05,1.20,1.39,1.54,1.65],[.230,.215,.190,.235,.200,.073]))
 ry=float(np.interp(p.z,[.8,1.05,1.20,1.39,1.54,1.65],[.135,.148,.140,.158,.133,.080]))
 torso_metric=math.sqrt((p.x/rx)**2+((p.y-.020)/ry)**2)
 arm_blend=smooth(-.35,.35,torso_metric-arm_metric)
 if p.z<1.18 and abs(p.x)<.255:arm_blend=0.
 if p.z>1.655:arm_blend=0.
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
 if p.z>=1.075:core=torso_weights(p)
 else:
  hip=smooth(1.080,.885,p.z)
  knee=smooth(.645,.515,p.z)
  ankle=smooth(.175,.080,p.z)
  ball=smooth(-.008,-.095,p.y)*(1-smooth(.06,.105,p.z))
  core=mixweights({'pelvis':1.},{'thigh_'+side:1.},hip)
  core=mixweights(core,{'calf_'+side:1.},knee)
  foot=mixweights({'foot_'+side:1.},{'ball_'+side:1.},ball)
  core=mixweights(core,foot,ankle)
 return mixweights(core,arm,arm_blend) if arm_blend else core
body_weights=[anatomical_weights(p) for p in points]
body.data.calc_loop_triangles();bodytris=[tuple(t.vertices) for t in body.data.loop_triangles]
body_bvh=BVHTree.FromPolygons(points,bodytris,all_triangles=True)
def body_sample(p):return sample(p,body_bvh,points,bodytris,body_weights)

# Appended to the native skeleton/anatomical fitting prefix by build_recipe.py.
parts=[]
forced={}
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
    active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def shell(o,thickness=.0025):
    m=o.modifiers.new('SewnPhysicalThickness','SOLIDIFY');m.thickness=thickness;m.offset=-1
    apply(o,m)
def imagefile(name,array,data=False):
    h,w=array.shape[:2]
    im=bpy.data.images.new(name,width=w,height=h,alpha=False)
    if data:im.colorspace_settings.name='Non-Color'
    rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=array
    im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(ROOT/'Textures'/(name+'.png'))
    im.file_format='PNG';im.save();return im
def material(family,color,rough,kind='cloth',metal=0):
    size=2048 if kind=='cloth' else 1024
    yy,xx=np.mgrid[:size,:size];u=xx/size;v=yy/size
    macro=.5*np.sin(2*math.pi*u*3)*np.sin(2*math.pi*v*5)+.23*np.sin(2*math.pi*(u+v)*11)
    if kind=='cloth':
        warp=np.sin(2*math.pi*u*256);weft=np.sin(2*math.pi*v*256)
        mask=((np.floor(u*256)+np.floor(v*256))%4<2)
        height=.28*np.where(mask,warp,weft)+.08*np.sin(2*math.pi*(u-v)*64)
    elif kind=='leather':
        rng=np.random.default_rng(1008);height=rng.normal(0,.22,(size,size))
        for _ in range(3):height=(height*4+np.roll(height,1,0)+np.roll(height,-1,0)+np.roll(height,1,1)+np.roll(height,-1,1))/8
        height+=.045*np.sin(2*math.pi*u*57)*np.sin(2*math.pi*v*71)
    else:height=.012*np.sin(2*math.pi*u*270)+.004*macro
    dy,dx=np.gradient(height)
    normal=np.stack([-dx*.32,-dy*.32,np.ones_like(height)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
    base=np.clip(np.array(color)[None,None,:]*(1+.07*height[:,:,None]+.026*macro[:,:,None]),0,1)
    orm=np.ones((size,size,3));orm[:,:,1]=np.clip(rough-.055*height+.02*macro,.18,.96);orm[:,:,2]=metal
    name='Security_'+family
    images=[imagefile(name+'_BaseColor',base),imagefile(name+'_Normal',normal*.5+.5,True),imagefile(name+'_ORM',orm,True)]
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links
    bs=n.get('Principled BSDF') or n.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Specular IOR Level'].default_value=.27 if kind=='cloth' else .42
    bs.inputs['Sheen Weight'].default_value=.14 if kind=='cloth' else 0
    for im,channel in zip(images,['base','normal','orm']):
        node=n.new('ShaderNodeTexImage');node.image=im
        if channel=='base':l.new(node.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='normal':
            nm=n.new('ShaderNodeNormalMap');l.new(node.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:
            sep=n.new('ShaderNodeSeparateColor');l.new(node.outputs['Color'],sep.inputs['Color'])
            l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    return mat
shirtmat=material('Uniform',(.055,.076,.106),.81)
pantsmat=material('Trousers',(.029,.037,.049),.84)
leather=material('Leather',(.019,.024,.030),.53,'leather')
trim=material('Trim',(.024,.031,.042),.87)
metal=material('Hardware',(.32,.34,.35),.37,'metal',.86)
thread=material('Insignia',(.39,.42,.44),.75)
def assign_uv(o,mode='shirt'):
    # 20 cm physical tile; branch-aware cylindrical projection for limbs.
    uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
    for face in o.data.polygons:
        coords=[]
        for li in face.loop_indices:
            p=o.data.vertices[o.data.loops[li].vertex_index].co
            side='l' if p.x>=0 else 'r';ax=abs(p.x)
            if mode=='pants' and p.z<.89:
                a=Vector(TARGET[side]['hip']);b=Vector(TARGET[side]['ankle']);axis=(b-a).normalized()
                t=(p-a).dot(axis);center=a+axis*t;q=p-center
                coords.append((math.atan2(q.x,-q.y)*.100/.20,t/.20))
            elif mode=='shirt' and ax>.252 and p.z<1.56:
                a=Vector(TARGET[side]['shoulder']);b=Vector(TARGET[side]['wrist']);axis=(b-a).normalized()
                t=(p-a).dot(axis);q=p-a-axis*t
                coords.append((math.atan2(q.z,q.y)*.074/.20,t/.20))
            elif mode in ['shirt','pants']:
                coords.append((math.atan2(p.x,-(p.y-.02))*.210/.20,p.z/.20))
            else:
                n=face.normal
                coords.append((p.y/.20,p.z/.20) if abs(n.x)>abs(n.y) else (p.x/.20,p.z/.20))
        # Unwrap triangles crossing cylindrical seam locally.
        if mode in ['shirt','pants'] and max(c[0] for c in coords)-min(c[0] for c in coords)>2.5:
            coords=[(c[0]+2*math.pi*.210/.20 if c[0]<0 else c[0],c[1]) for c in coords]
        for li,co in zip(face.loop_indices,coords):uv.data[li].uv=co
def mesh(name,verts,faces,mat,uvmode='planar'):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    assign_uv(o,uvmode);parts.append(o);return o
def clean_surface(o):
    o.data.update()
    for p in o.data.polygons:p.material_index=0;p.use_smooth=True
    o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
def wrist_distance(p,side):
    w=Vector(TARGET[side]['wrist']);e=Vector(TARGET[side]['elbow'])
    return (p-w).dot((w-e).normalized())
def garment_from_body(name,mode,mat):
    o=body.copy();o.data=body.data.copy();bpy.context.collection.objects.link(o);o.name=name
    o.data.materials.clear();o.data.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(o.data)
    remove=[]
    for f in bm.faces:
        c=f.calc_center_median();side='l' if c.x>=0 else 'r'
        if mode=='shirt':keep=c.z<1.645 and (c.z>1.116 or abs(c.x)>.29) and wrist_distance(c,side)<-.013
        else:keep=.145<c.z<1.170 and abs(c.x)<.285
        if not keep:remove.append(f)
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000035)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    for v in bm.verts:
        p=v.co
        if mode=='shirt':ease=.017+.005*smooth(1.37,1.57,p.z)
        else:
            ease=.021+.015*(1-smooth(.48,.82,p.z))
            if abs(p.x)<.055 and .77<p.z<1.02:ease=.010
        v.co+=v.normal*ease
    boundary=[v for v in bm.verts if v.is_boundary]
    for _ in range(24):bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.28,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    for v in boundary:
        p=v.co
        if mode=='pants':p.z=.145 if p.z<.3 else 1.170
        elif p.z>1.605:p.z=1.645
        elif abs(p.x)<.29:p.z=1.116
        else:
            side='l' if p.x>=0 else 'r';w=Vector(TARGET[side]['wrist']);e=Vector(TARGET[side]['elbow']);axis=(w-e).normalized()
            p-=axis*(wrist_distance(p,side)+.013)
    bm.normal_update();bm.to_mesh(o.data);bm.free();clean_surface(o)
    # Reduce only the newly constructed garment shell; source body is untouched.
    dec=o.modifiers.new('GarmentTopologyBudget','DECIMATE');dec.ratio=.32;apply(o,dec)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    for v in bm.verts:
        p=v.co;side='l' if p.x>=0 else 'r'
        if mode=='shirt' and abs(p.x)>.27:
            e=Vector(TARGET[side]['elbow']);w=Vector(TARGET[side]['wrist']);axis=(w-e).normalized()
            d=(p-e).dot(axis);r=p-e-axis*d
            relief=.0028*math.sin(d*94+math.atan2(r.z,r.y)*1.5)*math.exp(-(d/.080)**2)
        elif mode=='pants':
            relief=.0025*math.sin(p.z*78+p.y*9)*math.exp(-((p.z-.575)/.10)**2)
        else:relief=.0008*math.sin(p.z*65+p.x*11)*math.exp(-((p.z-1.20)/.09)**2)
        v.co+=v.normal*relief
    bm.to_mesh(o.data);bm.free();clean_surface(o);assign_uv(o,mode);shell(o,.0026)
    parts.append(o);return o
shirt=garment_from_body('Security_Shirt_Continuous','shirt',shirtmat)
pants=garment_from_body('Security_Trousers_Continuous','pants',pantsmat)
def surface(o):
    o.data.calc_loop_triangles();vs=[v.co.copy() for v in o.data.vertices];ts=[tuple(t.vertices) for t in o.data.loop_triangles]
    return BVHTree.FromPolygons(vs,ts,all_triangles=True)
shirt_bvh=surface(shirt);pants_bvh=surface(pants)
def facepoint(x,z,tree=shirt_bvh,back=False,ease=.003):
    h=tree.ray_cast(Vector((x,.65 if back else -.65,z)),Vector((0,-1 if back else 1,0)),1.3)
    if h[0] is None:h=tree.find_nearest(Vector((x,.18 if back else -.18,z)))
    return Vector((x,h[0].y+(ease if back else -ease),z))
def patch(name,xz,mat,tree=shirt_bvh,back=False,ease=.004,thickness=.002):
    # A subdivided patch follows its parent cloth, avoiding floating rigid panels.
    verts=[tuple(facepoint(x,z,tree,back,ease)) for x,z in xz]
    o=mesh(name,verts,[tuple(range(len(verts)))],mat)
    shell(o,thickness);return o
def block(name,center,size,mat,bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('RoundedEdges','BEVEL');m.width=bevel;m.segments=3;apply(o,m)
    world=o.matrix_world.copy()
    for v in o.data.vertices:v.co=world@v.co
    o.matrix_world=Matrix.Identity(4);o.data.materials.clear();o.data.materials.append(mat)
    clean_surface(o);assign_uv(o,'planar');parts.append(o);return o
def tube(name,paths,mat,radius=.00085,segments=6):
    verts=[];faces=[]
    for path in paths:
        if len(path)<2:continue
        path=[Vector(p) for p in path];base=len(verts)
        for i,p in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
            a=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
            u=tangent.cross(a).normalized();v=tangent.cross(u)
            for k in range(segments):verts.append(tuple(p+radius*(u*math.cos(k*2*math.pi/segments)+v*math.sin(k*2*math.pi/segments))))
        for j in range(len(path)-1):
            for k in range(segments):
                a=base+j*segments+k;b=base+j*segments+(k+1)%segments
                faces.append((a,b,b+segments,a+segments))
        faces.extend([tuple(base+k for k in reversed(range(segments))),tuple(base+(len(path)-1)*segments+k for k in range(segments))])
    return mesh(name,verts,faces,mat)
def front_grid(name,xlo,xhi,zlo,zhi,mat,tree=shirt_bvh,ease=.004,rows=18,cols=4):
    verts=[tuple(facepoint(float(x),float(z),tree,ease=ease)) for z in np.linspace(zlo,zhi,rows) for x in np.linspace(xlo,xhi,cols)]
    faces=[(j*cols+i,j*cols+i+1,(j+1)*cols+i+1,(j+1)*cols+i) for j in range(rows-1) for i in range(cols-1)]
    o=mesh(name,verts,faces,mat);shell(o,.0016);return o
front_grid('Security_FrontPlacket',-.013,.013,1.145,1.602,shirtmat)
for i,z in enumerate(np.linspace(1.185,1.56,6)):
    p=facepoint(0,float(z),ease=.008);block('Security_ShirtButton_%02d'%i,p,(.008,.003,.008),trim,.003)
for sign in [-1,1]:
    # Chest pockets with shaped flaps and stitched edges.
    x0,x1=sorted([sign*.048,sign*.149])
    front_grid('Security_ChestPocket_'+str(sign),x0,x1,1.364,1.466,shirtmat,ease=.006,rows=10,cols=8)
    coords=[(x0,1.476),(x1,1.476),(x1,1.445),((x0+x1)/2,1.433),(x0,1.445)]
    patch('Security_PocketFlap_'+str(sign),coords,shirtmat,ease=.010)
    p=facepoint((x0+x1)/2,1.447,ease=.014);block('Security_PocketButton_'+str(sign),p,(.007,.003,.007),trim,.002)
    path=[facepoint(x,z,ease=.0085) for x,z in [(x0+.004,1.460),(x0+.004,1.370),(x1-.004,1.370),(x1-.004,1.460)]]
    tube('Security_PocketStitch_'+str(sign),[path],trim,.0006)
    # Physical collar leaves meet a neck band; head stays fully exposed.
    coords=[(sign*.014,1.648),(sign*.073,1.642),(sign*.109,1.575),(sign*.045,1.591)]
    patch('Security_CollarLeaf_'+str(sign),coords,shirtmat,ease=.010,thickness=.0028)
    # Back trouser welt pockets and curved front pocket opening.
    coords=[(sign*.055,1.044),(sign*.168,1.044),(sign*.168,1.060),(sign*.055,1.060)]
    patch('Security_RearPocketWelt_'+str(sign),coords,trim,pants_bvh,True,.004)
    path=[facepoint(sign*(.105+.075*t),1.115-.135*t,pants_bvh,ease=.004) for t in np.linspace(0,1,20)]
    tube('Security_TrouserPocketSeam_'+str(sign),[path],trim,.001)
    # Shoulder epaulettes conform to shoulder surface, not floating pads.
    verts=[]
    for x in np.linspace(.105,.269,16):
        for y in [.009,.061]:
            hit=shirt_bvh.ray_cast(Vector((sign*float(x),y,1.85)),Vector((0,0,-1)),.55)
            p=hit[0] or Vector((sign*float(x),y,1.57));verts.append(tuple(p+Vector((0,0,.0035))))
    faces=[(j*2,j*2+1,j*2+3,j*2+2) for j in range(15)]
    ep=mesh('Security_Epaulette_'+str(sign),verts,faces,trim);shell(ep,.002)
    p=Vector(verts[4]).lerp(Vector(verts[5]),.5)+Vector((0,0,.003))
    block('Security_EpauletteStud_'+str(sign),p,(.008,.008,.003),metal,.002)
    for j in [10,12]:
        a=Vector(verts[j*2])+Vector((0,0,.003));b=Vector(verts[j*2+1])+Vector((0,0,.003))
        tube('Security_RankBar_'+str(sign)+'_'+str(j),[[a,b]],thread,.0017,6)
# Neck band follows the actual base-neck surface.
verts=[];faces=[]
for z in np.linspace(1.624,1.657,5):
    for i in range(65):
        theta=2*math.pi*i/64;d=Vector((math.sin(theta),-math.cos(theta),0));c=Vector((0,.019,float(z)))
        h=body_bvh.ray_cast(c,d,.16);r=(h[0]-c).length if h[0] is not None else .074
        verts.append(tuple(c+d*(r+.010)))
for j in range(4):
    for i in range(64):a=j*65+i;faces.append((a,a+1,a+66,a+65))
collar=mesh('Security_CollarStand',verts,faces,shirtmat,'shirt');shell(collar,.0023)
# Short secured tie follows the chest rather than a loose simulated strip.
verts=[]
for j,z in enumerate(np.linspace(1.305,1.607,36)):
    width=float(np.interp(z,[1.305,1.325,1.46,1.575,1.607],[.001,.026,.022,.014,.018]))
    for t in np.linspace(-1,1,5):verts.append(tuple(facepoint(float(t*width),float(z),ease=.014+.002*(1-t*t))))
faces=[(j*5+i,j*5+i+1,(j+1)*5+i+1,(j+1)*5+i) for j in range(35) for i in range(4)]
tie=mesh('Security_Tie',verts,faces,trim);shell(tie,.002)
block('Security_TieClip',facepoint(0,1.414,ease=.020),(.041,.003,.005),metal,.001)
# Waist belt and keepers wrap the real cloth cross section.
def beltpoint(theta,z,ease=.010):
    c=Vector((0,.020,z));d=Vector((math.sin(theta),-math.cos(theta),0))
    hits=[h for h in [shirt_bvh.ray_cast(c,d,.4),pants_bvh.ray_cast(c,d,.4)] if h[0] is not None]
    r=max((h[0]-c).length for h in hits) if hits else .21
    return c+d*(r+ease)
verts=[tuple(beltpoint(2*math.pi*i/112,float(z))) for z in np.linspace(1.107,1.153,5) for i in range(113)]
faces=[(j*113+i,j*113+i+1,(j+1)*113+i+1,(j+1)*113+i) for j in range(4) for i in range(112)]
belt=mesh('Security_DutyBelt',verts,faces,leather,'pants');shell(belt,.004);forced[belt.name]={'pelvis':1.}
for i,t in enumerate([.55,1.08,1.85,2.7,3.58,4.43,5.2,5.73]):
    verts=[tuple(beltpoint(t+dx,z,.016)) for z in [1.102,1.159] for dx in [-.029,.029]]
    o=mesh('Security_BeltKeeper_%02d'%i,verts,[(0,1,3,2)],trim);shell(o,.003);forced[o.name]={'pelvis':1.}
p=beltpoint(0,1.130,.017)
for name,center,size in [('Top',p+Vector((0,0,.022)),(.061,.005,.006)),('Bottom',p-Vector((0,0,.022)),(.061,.005,.006)),('Left',p+Vector((.028,0,0)),(.006,.005,.044)),('Right',p-Vector((.028,0,0)),(.006,.005,.044)),('Prong',p,(.040,.004,.004))]:
    o=block('Security_Buckle_'+name,center,size,metal,.0015);forced[o.name]={'pelvis':1.}
# Two compact duty pouches, no weapon or independent physics bodies.
for i,theta in enumerate([1.22,4.95]):
    c=beltpoint(theta,1.095,.030);o=block('Security_BeltPouch_%d'%i,c,(.048,.075,.120),leather,.010);forced[o.name]={'pelvis':1.}
# ID plate and subdued back security lettering.
p=facepoint(.102,1.506,ease=.009)
block('Security_IDPlate',p,(.089,.003,.021),metal,.0015)
def text_mesh(name,label,center,size,mat,back=False):
    cu=bpy.data.curves.new(name,'FONT');cu.body=label;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.extrude=.00015;cu.resolution_u=4
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);o.location=center
    o.rotation_euler=(math.pi/2,0,math.pi if back else 0);active(o);bpy.ops.object.convert(target='MESH')
    world=o.matrix_world.copy()
    for v in o.data.vertices:v.co=world@v.co
    o.matrix_world=Matrix.Identity(4);o.data.materials.append(mat);assign_uv(o,'planar');parts.append(o);return o
text_mesh('Security_IDLetters','M / SECURITY',p+Vector((0,-.002,0)),.0082,trim)
label=text_mesh('Security_BackLettering','SECURITY',facepoint(0,1.478,back=True,ease=.006),.038,thread,True)
for v in label.data.vertices:
    q=facepoint(v.co.x,v.co.z,back=True,ease=.006);v.co.y=q.y
# Wrist cuffs use body-derived rings with true openings and edge thickness.
for side in ['l','r']:
    w=Vector(TARGET[side]['wrist']);e=Vector(TARGET[side]['elbow']);axis=(w-e).normalized()
    u=Vector((0,1,0));u=(u-axis*u.dot(axis)).normalized();v=axis.cross(u)
    verts=[]
    for t in np.linspace(-.059,.000,6):
        c=w+axis*float(t)
        for i in range(49):
            angle=2*math.pi*i/48;d=u*math.cos(angle)+v*math.sin(angle)
            h=body_bvh.ray_cast(c,d,.11);r=(h[0]-c).length if h[0] is not None else .036
            verts.append(tuple(c+d*(min(r,.071)+.017)))
    faces=[(j*49+i,j*49+i+1,(j+1)*49+i+1,(j+1)*49+i) for j in range(5) for i in range(48)]
    o=mesh('Security_Cuff_'+side,verts,faces,shirtmat,'shirt');shell(o,.0028)
    c=w-axis*.027+Vector((0,-.059,0));block('Security_CuffButton_'+side,c,(.008,.003,.008),trim,.002)
# Ankle boots are sculpted envelopes; toes stay inside a continuous leather upper.
for side,sign in [('l',1),('r',-1)]:
    o=body.copy();o.data=body.data.copy();bpy.context.collection.objects.link(o);o.name='Security_Boot_'+side
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if any(v.co.z>.225 or sign*v.co.x<.060 for v in f.verts)],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00004)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    for v in bm.verts:
        v.co+=v.normal*.012
        v.co.z=max(.011,v.co.z)
    bm.to_mesh(o.data);bm.free();active(o)
    rem=o.modifiers.new('ContinuousLeatherUpper','REMESH');rem.mode='VOXEL';rem.voxel_size=.0050;rem.use_smooth_shade=True;apply(o,rem)
    sm=o.modifiers.new('LastShapeSmooth','SMOOTH');sm.factor=.65;sm.iterations=10;apply(o,sm)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().z>.215],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    for v in bm.verts:
        if v.is_boundary:v.co.z=.215
    bm.to_mesh(o.data);bm.free();o.data.materials.clear();o.data.materials.append(leather);clean_surface(o)
    assign_uv(o,'planar');shell(o,.0035);parts.append(o)
    boot_bvh=surface(o)
    # Sole traces the actual foot envelope at low height.
    a=Vector(TARGET[side]['ankle']);center=Vector((sign*.226,.010,.032));outline=[]
    for i in range(81):
        theta=2*math.pi*i/80;d=Vector((math.sin(theta),-math.cos(theta),0));h=boot_bvh.ray_cast(center,d,.25)
        r=(h[0]-center).length if h[0] is not None else .060
        outline.append(center+d*(r+.004))
    verts=[(p.x,p.y,z) for z in [.002,.010,.035] for p in outline]
    faces=[(j*81+i,j*81+i+1,(j+1)*81+i+1,(j+1)*81+i) for j in range(2) for i in range(80)]
    faces.append(tuple(reversed(range(80))));faces.append(tuple(162+i for i in range(80)))
    sole=mesh('Security_BootSole_'+side,verts,faces,trim);forced[sole.name]={'foot_'+side:1.}
    path=[Vector((p.x,p.y,.039)) for p in outline];tube('Security_BootWelt_'+side,[path],leather,.0018)
    paths=[]
    for j,z in enumerate(np.linspace(.087,.191,6)):
        x=a.x;pa=facepoint(x-.024,float(z),boot_bvh,ease=.003);pb=facepoint(x+.024,float(z)+.008,boot_bvh,ease=.003)
        paths.append([pa,pa.lerp(pb,.5)+Vector((0,-.003,0)),pb])
        for k,p in enumerate([pa,pb]):block('Security_BootEyelet_'+side+'_'+str(j)+'_'+str(k),p,(.006,.002,.006),metal,.002)
    tube('Security_BootLaces_'+side,paths,trim,.0015,6)
# Smooth anatomy-preserving weights shared by adjoining clothes and details.
def garment_weights(o,p):
    if o.name in forced:return forced[o.name]
    ws=body_sample(p)
    if o.name.startswith('Security_Collar'):return {'spine_05':.86,'neck_01':.14}
    if (o.name.startswith('Security_Shirt') and abs(p.x)<.29 and p.z<1.20) or (o.name.startswith('Security_Trousers') and p.z>1.02):
        return {'pelvis':1.}
    return ws
def bind(o,values):
    oldnormals=[v.vector.copy() for v in o.data.corner_normals]
    matrices=[matrix(ws) for ws in values]
    mapped=[(matrices[lp.vertex_index].to_3x3().transposed()@n).normalized() for lp,n in zip(o.data.loops,oldnormals)]
    o.vertex_groups.clear()
    for n in sorted({n for ws in values for n in ws}):o.vertex_groups.new(name=n)
    for v,ws,m in zip(o.data.vertices,values,matrices):
        v.co=m.inverted_safe()@v.co
        for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
    o.data.update();o.data.normals_split_custom_set(mapped)
    o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=o.modifiers.new('NativeHumanoidSkin','ARMATURE');mod.object=rig
# The complete supplied body stays editable; only the assembled display hides
# permanently covered skin. Hands overlap cuffs, neck overlaps the collar.
display=body.copy();display.data=body.data.copy();bpy.context.collection.objects.link(display);display.name='Security_OutfitBody'
bm=bmesh.new();bm.from_mesh(display.data)
remove=[]
for f in bm.faces:
    c=f.calc_center_median();side='l' if c.x>=0 else 'r'
    exposed=c.z>1.628 or (abs(c.x)>.30 and .70<c.z<1.10 and wrist_distance(c,side)>-.019)
    if not exposed:remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(display.data);bm.free()
display_weights=[body_sample(v.co) for v in display.data.vertices]
for o in parts:
    bind(o,[garment_weights(o,v.co) for v in o.data.vertices])
bind(display,display_weights)
body.name='Security_CompleteBody';body.data.materials[0].name='Security_Skin';bind(body,body_weights)
for o in list(bpy.context.scene.objects):
    if o not in parts+[body,display,rig]:bpy.data.objects.remove(o,do_unlink=True)
rig.name='root';rig['source_world_matrix']=[x for row in rig.matrix_world for x in row]
rig.show_in_front=True
body.hide_set(True);body.hide_render=True
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
for im in list(bpy.data.images):
    if not im.users:bpy.data.images.remove(im)
for mat in list(bpy.data.materials):
    if not mat.users:bpy.data.materials.remove(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V01.blend'))
report={'stage':'authored','source_body_triangles':len(bodytris),'complete_body_preserved':True,
    'source_authoring_height_m':1.90,'fit_targets':TARGET,'bone_count':len(rig.data.bones)+1,
    'clothing_parts':[{'name':o.name,'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)} for o in parts],
    'display_body_triangles':sum(len(p.vertices)-2 for p in display.data.polygons),
    'cloth_simulation':False,'rendered':False,'runtime_tested':False,
    'notes':['Intact complete source body stored separately; assembled display contains only head, neck and hands.',
             'Continuous shirt shoulder and sleeve topology; separately following trouser legs.',
             'Native Nurse skeleton coordinate system retained, anatomical retopology weights fitted to the male model.',
             'New 20 cm woven PBR materials, independent leather and metal surface families.']}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_AUTHORING_SAVED '+json.dumps({'parts':len(parts),'body_triangles':len(bodytris),'clothing_triangles':sum(x['triangles'] for x in report['clothing_parts'])}),flush=True)
