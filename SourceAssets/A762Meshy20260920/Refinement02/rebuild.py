"""Reference-led A762 exterior reconstruction. Author/export only, no render or tests.

All dimensions are fitted game-space coordinates, not manufacturing dimensions.
Keep the existing mechanical bones, sight hinges and A762 animation tracks.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).parent; D=O/'Exports'; D.mkdir(exist_ok=True)
I=O.parent/'Integration'; previous=O.parent/'Refinement01'
meta=json.loads((I/'authoring.json').read_text(encoding='utf-8'))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(previous/'A762_Refined_Editable.blend'))
s=bpy.context.scene; r=bpy.data.objects['SK_M4_Infima']; hands=bpy.data.objects['SK_Manny_Arms_Export']
r.animation_data.action=bpy.data.actions['A_A762_idle']; r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE'; s.frame_set(0); bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy()
rest={b.name:b.matrix_local.copy() for b in r.data.bones}; pose={b.name:b.matrix.copy() for b in r.pose.bones}
cx=.00056; body=[]; new=[]; magazines=[]; sights={'RearSight':[],'FrontSight':[]}
archive=bpy.data.collections.new('A762_BEFORE_REFINEMENT02'); s.collection.children.link(archive)
made=bpy.data.collections.new('A762_RECONSTRUCTED_02'); s.collection.children.link(made)
report={'source':'Refinement01/A762_Refined_Editable.blend','changes':{},'new_parts':{},'materials':{},
        'markers':meta['markers_blender_root'],'hinges':meta['hinges_ue_root'],'tests_run':False,'renders_run':False}
mats={}
for key in ['MachinedSteel','Flash_Hider','SightInner','Inside','Handguard']:
    mats[key]=bpy.data.materials['M_A762_'+key]

# New meshes have their own finish; the old source atlas normal is not projected
# onto unrelated topology. Broad retained surfaces keep their original UV0 data.
recipes={
 'Magazine_Rebuilt':((.025,.031,.039),.82,.365,.030),
 'MagazineEdge_Rebuilt':((.030,.036,.044),.86,.315,.021),
 'MagazineInside_Rebuilt':((.008,.011,.015),.35,.66,.018),
 'FrontAssembly_Rebuilt':((.022,.028,.037),.85,.33,.020),
 'FrontSight_Rebuilt':((.021,.028,.038),.80,.37,.018),
 'RearSight_Rebuilt':((.021,.028,.038),.80,.38,.018),
}
# A tileable, low-amplitude finish mask, used only as roughness variation.
T=O/'Textures'; T.mkdir(exist_ok=True)
rng=np.random.default_rng(76202); n=256
fine=rng.random((n,n)); smooth=sum(np.roll(np.roll(fine,i,0),j,1) for i in range(-2,3) for j in range(-2,3))/25
grain=np.clip(.5+(fine-.5)*.34+(smooth-.5)*1.9,0,1)
pixels=np.ones((n,n,4),dtype=np.float32); pixels[:,:,:3]=grain[:,:,None]
img=bpy.data.images.new('T_A762_RebuiltFinish',width=n,height=n,alpha=True)
img.pixels.foreach_set(pixels.ravel()); img.colorspace_settings.name='Non-Color'
img.filepath_raw=str(T/'T_A762_RebuiltFinish.png'); img.file_format='PNG'; img.save()
for key,(col,metal,rough,variation) in recipes.items():
    mat=bpy.data.materials.new('M_A762_'+key); mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links; nodes.clear()
    bs=nodes.new('ShaderNodeBsdfPrincipled'); out=nodes.new('ShaderNodeOutputMaterial'); links.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*col,1); bs.inputs['Metallic'].default_value=metal
    uv=nodes.new('ShaderNodeUVMap'); uv.uv_map='UVMap'
    tx=nodes.new('ShaderNodeTexImage'); tx.image=img; links.new(uv.outputs[0],tx.inputs[0])
    mul=nodes.new('ShaderNodeMath'); mul.operation='MULTIPLY'; mul.inputs[1].default_value=variation; links.new(tx.outputs['Color'],mul.inputs[0])
    add=nodes.new('ShaderNodeMath'); add.operation='ADD'; add.inputs[1].default_value=rough-variation*.5; links.new(mul.outputs[0],add.inputs[0]); links.new(add.outputs[0],bs.inputs['Roughness'])
    mats[key]=mat
    report['materials'][mat.name]={'base_color_linear':col,'metallic':metal,'roughness_center':rough,'roughness_variation':variation,'finish_texture':'Textures/T_A762_RebuiltFinish.png'}

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.hide_set(False); ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def hide_old(ob):
    ob.name=ob.name+'_Before02'
    for collection in list(ob.users_collection): collection.objects.unlink(ob)
    archive.objects.link(ob); ob.hide_set(True); ob.hide_render=True

def regions(me,indices=None):
    layer=me.color_attributes.get('SurfaceRegions') or me.color_attributes.new(name='SurfaceRegions',type='FLOAT_COLOR',domain='CORNER')
    me.color_attributes.active_color=layer
    for p in me.polygons:
        c=(1 if indices and p.index in indices else 0,0,0,1)
        for li in p.loop_indices: layer.data[li].color=c

def bind(ob,bone='WPN_root'):
    xf=rest[bone]@pose[bone].inverted()@root; nx=xf.to_3x3().inverted().transposed()
    normals=[(nx@n.vector).normalized() for n in ob.data.corner_normals]
    ob.data.transform(xf); ob.data.normals_split_custom_set(normals)
    ob.parent=r; ob.matrix_parent_inverse=Matrix.Identity(4); ob.matrix_basis=Matrix.Identity(4)
    ob.vertex_groups.clear(); ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE')
    ob.modifiers.new('A762 mechanical bone','ARMATURE').object=r

def primitive(name,vertices,faces,key='FrontAssembly_Rebuilt',bevel=.00014,inner=None,group=None,mag=False):
    me=bpy.data.meshes.new(name); me.from_pydata(vertices,[],faces); me.update(); me.materials.append(mats[key])
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces: f.smooth=True
    for e in bm.edges: e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(38))
    bm.to_mesh(me); bm.free()
    if inner and key!='Flash_Hider':
        me.materials.append(mats['MagazineInside_Rebuilt' if mag else 'SightInner'])
        for i in inner: me.polygons[i].material_index=1
    uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        axis=max(range(3),key=lambda a:abs(p.normal[a])); a,b=[k for k in range(3) if k!=axis]
        for li in p.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv=(v[a]*36,v[b]*36)
    regions(me,inner if key=='Flash_Hider' else None)
    ob=bpy.data.objects.new(name,me); made.objects.link(ob); select([ob])
    if bevel:
        mod=ob.modifiers.new('Controlled edge radius','BEVEL'); mod.width=bevel; mod.segments=3
        mod.limit_method='ANGLE'; mod.angle_limit=math.radians(38); mod.use_clamp_overlap=True; mod.harden_normals=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=ob.modifiers.new('Weighted planes and split edges','WEIGHTED_NORMAL'); mod.keep_sharp=True; mod.weight=50
    bpy.ops.object.modifier_apply(modifier=mod.name)
    report['new_parts'][name]={'faces':len(ob.data.polygons),'material':key,'binding':'WPN_SOCKET_Magazine' if mag else group or 'WPN_root'}
    if group: sights[group].append(ob)
    elif mag: magazines.append(ob)
    else: new.append(ob)
    return ob

def extrude(name,outline,a,b,axis=1,key='FrontAssembly_Rebuilt',bevel=.00014,group=None,mag=False):
    axes=[k for k in range(3) if k!=axis]; v=[]
    for t in [a,b]:
        for q in outline:
            p=[0,0,0]; p[axis]=t; p[axes[0]]=q[0]; p[axes[1]]=q[1]; v.append(p)
    m=len(outline); f=[tuple(range(m-1,-1,-1)),tuple(range(m,m*2))]
    f.extend((i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m))
    return primitive(name,v,f,key,bevel,group=group,mag=mag)

def box(name,center,size,key='FrontAssembly_Rebuilt',bevel=.00014,group=None,mag=False):
    x,y,z=center; dx,dy,dz=[q/2 for q in size]
    return extrude(name,[(x-dx,z-dz),(x+dx,z-dz),(x+dx,z+dz),(x-dx,z+dz)],y-dy,y+dy,1,key,bevel,group,mag)

def lathe(name,center,sections,key='FrontAssembly_Rebuilt',inner_start=999,n=72,axis=1,group=None):
    v=[]; f=[]; inner=[]; other=[k for k in range(3) if k!=axis]
    for rad,t in sections:
        for i in range(n):
            a=math.tau*i/n; p=list(center); p[axis]+=t; p[other[0]]+=rad*math.cos(a); p[other[1]]+=rad*math.sin(a); v.append(p)
    for j in range(len(sections)):
        for i in range(n):
            f.append((j*n+i,j*n+(i+1)%n,((j+1)%len(sections))*n+(i+1)%n,((j+1)%len(sections))*n+i))
            if j>=inner_start: inner.append(len(f)-1)
    return primitive(name,v,f,key,0,inner,group)

def tube(name,y0,y1,z,rad,key='FrontAssembly_Rebuilt',group=None):
    d=.0002; ri=max(.001,rad-.0014)
    return lathe(name,(cx,0,z),[(rad-d,y0),(rad,y0+d),(rad,y1-d),(rad-d,y1),(ri,y1),(ri,y0)],key,4,72,group=group)

def pin(name,center,rad=.0020,key='FrontAssembly_Rebuilt',group=None):
    # Solid external screw head, with a narrow dark recessed central socket.
    return lathe(name,center,[(rad*.85,-.0007),(rad,-.00045),(rad,.00045),(rad*.85,.00065),(rad*.30,.00065),(rad*.30,.00015),(.00004,.00015),(.00004,-.0007)],key,4,48,axis=0,group=group)

def rounded_rect(hw,hh,rad,n=5):
    pts=[]
    for x,y,a in [(hw-rad,hh-rad,0),(-hw+rad,hh-rad,90),(-hw+rad,-hh+rad,180),(hw-rad,-hh+rad,270)]:
        for angle in np.linspace(a,a+90,n,endpoint=False):
            t=math.radians(float(angle)); pts.append((x+rad*math.cos(t),y+rad*math.sin(t)))
    return pts

def loop_prism(name,outer,inner,a,b,axis=1,key='FrontAssembly_Rebuilt',group=None):
    # Real aperture: outer wall, inner wall and annular rims. No face spans it.
    axes=[k for k in range(3) if k!=axis]; v=[]; f=[]; dark=[]; m=len(outer)
    for t,outline in [(a,outer),(b,outer),(a,inner),(b,inner)]:
        for q in outline:
            p=[0,0,0]; p[axis]=t; p[axes[0]]=q[0]; p[axes[1]]=q[1]; v.append(p)
    for i in range(m):
        j=(i+1)%m
        f.extend([(i,j,m+j,m+i),(2*m+i,3*m+i,3*m+j,2*m+j),(i,2*m+i,2*m+j,j),(m+i,m+j,3*m+j,3*m+i)])
        dark.append(len(f)-3)
    return primitive(name,v,f,key,.00012,dark,group)

# Retain complete unrelated parts. Remove the previous approximated front
# assembly and magazine rather than stacking additions over broken source faces.
active=bpy.data.collections['A762_REFINED_GEOMETRY']
replace_prefix=('A762_Barrel_','A762_GasTube_','A762_Flash_Hider_')
for ob in list(active.objects):
    if ob.type!='MESH': continue
    if ob.name=='A762_Magazine' or ob.name.startswith(replace_prefix) or ob.name in ['SM_A762_FrontSight','SM_A762_RearSight']:
        hide_old(ob)
    elif ob.name!='A762_Receiver': body.append(ob)

# Clip the generated receiver at the complete front assembly seam. Interpolate
# UV0 and authored corner normals at the cut, preserving the retained finish.
old=bpy.data.objects['A762_Receiver']; xf=root.inverted()@pose['WPN_root']@rest['WPN_root'].inverted()
nx=xf.to_3x3().inverted().transposed(); srcuv=old.data.uv_layers.active
vroot=[xf@v.co for v in old.data.vertices]; verts=[]; faces=[]; uvfaces=[]; normals=[]; matids=[]; index={}
def clip(poly,axis,threshold,keep_greater=True):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-threshold)*(1 if keep_greater else -1); db=(b[0][axis]-threshold)*(1 if keep_greater else -1)
        if da>=0: out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db); out.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized()))
    return out
for p in old.data.polygons:
    poly=[(vroot[old.data.loops[li].vertex_index],srcuv.data[li].uv.copy(),(nx@old.data.corner_normals[li].vector).normalized()) for li in p.loop_indices]
    poly=clip(poly,1,-.3662)
    if len(poly)<3: continue
    c=sum((v[0] for v in poly),Vector())/len(poly)
    # Remove source fragments at the old magazine split. The surrounding collar
    # is rebuilt below, while trigger, trigger guard and grip stay untouched.
    if -.237<c.y<-.060 and c.z<.035:
        poly=clip(poly,2,.0318)
    if len(poly)<3: continue
    face=[]
    for v,uv,normal in poly:
        key=tuple(round(q,8) for q in v)
        if key not in index: index[key]=len(verts); verts.append(tuple(v))
        face.append(index[key])
    if len(set(face))<3: continue
    faces.append(face); uvfaces.append([p[1] for p in poly]); normals.extend(p[2] for p in poly); matids.append(p.material_index)
name=old.name; hide_old(old)
me=bpy.data.meshes.new(name+'_ContinuousSeams'); me.from_pydata(verts,[],faces); me.update()
for mat in old.data.materials: me.materials.append(mat)
uv=me.uv_layers.new(name='UVMap')
for p,us,mi in zip(me.polygons,uvfaces,matids):
    p.material_index=mi; p.use_smooth=True
    for li,value in zip(p.loop_indices,us): uv.data[li].uv=value
me.normals_split_custom_set(normals); regions(me)
ob=bpy.data.objects.new(name,me); made.objects.link(ob); bind(ob); body.append(ob)
report['changes']['receiver']='Exact front-plane clipping with interpolated UV0/split normals; remove stray source magazine interface faces; rebuild covered interface collars.'

# Continuous front assembly. The fixed barrel runs through every collar and
# reaches the existing muzzle mount. Only the removable factory device uses its
# original Flash_Hider material slot, preserving gunsmith visibility behavior.
tube('A762_R02_Barrel_Continuous',-.520,-.3615,.0544,.0077)
tube('A762_R02_Barrel_RearShoulder',-.394,-.362,.0544,.0100)
tube('A762_R02_Barrel_Transition',-.398,-.389,.0544,.0085)
tube('A762_R02_GasTube_Core',-.497,-.360,.0804,.0068)
tube('A762_R02_GasTube_RearSeat',-.391,-.362,.0804,.0094)
for y,rad,w in [(-.364,.0106,.003),(-.386,.0100,.003),(-.394,.0082,.002),(-.481,.0084,.003),(-.495,.0088,.006)]:
    tube('A762_R02_GasTube_Ring_'+str(y),y-w/2,y+w/2,.0804,rad)

# Long fluted sleeve, modelled as actual recessed strips in the radial surface.
v=[]; f=[]; n=96
rows=[(-.482,0),(-.480,.0),(-.477,1),(-.404,1),(-.400,0),(-.397,0)]
for y,amount in rows:
    for i in range(n):
        a=math.tau*i/n; phase=abs(math.sin(3*a)); groove=max(0,1-phase/.32)**.65
        rad=.0080-.0010*groove*amount
        v.append((cx+rad*math.cos(a),y,.0804+rad*math.sin(a)))
for j in range(len(rows)-1):
    f.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
f.extend([tuple(range(n-1,-1,-1)),tuple(range((len(rows)-1)*n,len(rows)*n))])
primitive('A762_R02_GasTube_FlutedSleeve',v,f,bevel=0)
# Faceted end of the reference gas tube, rear adjustment bosses and their seats.
octagon=[(cx+x,.0804+z) for x,z in rounded_rect(.0088,.0082,.0023,4)]
extrude('A762_R02_GasTube_FrontSocket',octagon,-.4955,-.4595,bevel=.00025)
for side in [-1,1]:
    pin('A762_R02_GasTube_RearBoss_'+str(side),(cx+side*.0091,-.376,.0804),.0040)

# A clean closing ferrule covers the old generated guard seam and houses the two
# tubes; these holes are occupied by continuous closed external tubes.
outline=[(cx+x,.056+z) for x,z in rounded_rect(.0207,.0245,.006,6)]
extrude('A762_R02_Handguard_EndFerrule',outline,-.373,-.3655,bevel=.00025)
for y in [-.452,-.493]:
    tube('A762_R02_BarrelBand_'+str(y),y-.0031,y+.0031,.0544,.0093)
    box('A762_R02_BarrelBand_Lug_'+str(y),(cx,y,.0425),(.009,.0060,.0100),bevel=.0007)
    for side in [-1,1]: pin('A762_R02_BarrelBand_Pin_'+str(y)+'_'+str(side),(cx+side*.0046,y,.0414),.00185)
# Fixed front block physically bridges gas tube, barrel, folding sight pivot.
bridge=[(-.501,.050),(-.484,.050),(-.483,.077),(-.487,.085),(-.499,.085),(-.503,.062)]
extrude('A762_R02_FrontBlock_Bridge',bridge,cx-.0064,cx+.0064,axis=0,bevel=.00035)
tube('A762_R02_FrontBlock_BarrelSeat',-.504,-.482,.0544,.0101)
tube('A762_R02_Muzzle_JoinedShoulder',-.5205,-.501,.0544,.0100)
tube('A762_R02_Muzzle_SeatBand',-.5195,-.5145,.0544,.0120)
lathe('A762_R02_FactoryMuzzle',(cx,0,.0544),[(.0106,-.5170),(.0130,-.519),(.0130,-.572),(.0137,-.574),(.0137,-.5815),(.0126,-.5845),(.0124,-.58648),(.0052,-.58648),(.0048,-.5855),(.0048,-.517)],'Flash_Hider',7,112)
# Fine machined rings are part of the detachable device, never stranded when hidden.
for y in [-.5230,-.5262,-.578,-.580]:
    tube('A762_R02_Muzzle_ExternalRing_'+str(y),y-.00034,y+.00034,.0544,.01345,'Flash_Hider')

# Magazine: one complete closed shell with finite mouth recess, four complete
# walls and a slanted floor. Curve endpoints retain the original grip envelope.
def bez(points,t):
    a,b,c,d=[Vector(p) for p in points]; return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
def mag_edges(t):
    return (bez([(-.132,.030),(-.144,-.025),(-.160,-.060),(-.209,-.087)],t),
            bez([(-.064,.030),(-.063,-.031),(-.103,-.085),(-.173,-.136)],t))
def section(t,width=.0112,inset=0):
    a,b=mag_edges(t); mid=(a+b)/2; direction=(b-a).normalized(); h=(b-a).length/2-inset
    return [(cx+x,*(mid+direction*p)) for x,p in rounded_rect(width,h,.0017,6)]
v=[]; f=[]; dark=[]; samples=list(np.linspace(0,1,57)); m=len(section(0))
for t in samples: v.extend(section(float(t)))
for j in range(len(samples)-1): f.extend((j*m+i,j*m+(i+1)%m,(j+1)*m+(i+1)%m,(j+1)*m+i) for i in range(m))
f.append(tuple(range((len(samples)-1)*m,len(samples)*m)))
mouth0=len(v); v.extend(section(0,.0088,.0030))
mouth1=len(v); v.extend(section(.065,.0088,.0030))
for i in range(m):
    j=(i+1)%m; f.append((i,j,mouth0+j,mouth0+i)); f.append((mouth0+i,mouth0+j,mouth1+j,mouth1+i)); dark.append(len(f)-1)
f.append(tuple(range(mouth1,mouth1+m))); dark.append(len(f)-1)
primitive('A762_R02_Magazine_CompleteShell',v,f,'Magazine_Rebuilt',.00012,dark,mag=True)

def mag_band(name,t0,t1,width=.0123,key='MagazineEdge_Rebuilt'):
    a=section(t0,width,-.0004); b=section(t1,width,-.0004); m=len(a)
    f=[tuple(range(m-1,-1,-1)),tuple(range(m,m*2))]+[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
    return primitive(name,a+b,f,key,.00024,mag=True)
mag_band('A762_R02_Magazine_Floorplate',.985,1.015,.0128)
# Curved embossed strips, with a rounded trapezoid across their width. The flat
# perimeter is sunk into the complete shell, so no exposed ribbon remains.
def strip(name,side,t0,t1,u0,u1,lift=.00060,key='MagazineEdge_Rebuilt'):
    steps=max(2,int((t1-t0)*65)); rows=np.linspace(t0,t1,steps+1); v=[]; f=[]
    profile=[(u0,0),(u0+(u1-u0)*.22,lift),(u1-(u1-u0)*.22,lift),(u1,0)]
    for t in rows:
        a,b=mag_edges(float(t))
        for u,h in profile:
            yz=a.lerp(b,u); v.append((cx+side*(.0112+h-.00008),yz.x,yz.y))
    for j in range(steps):
        for k in range(3): f.append((j*4+k,j*4+k+1,(j+1)*4+k+1,(j+1)*4+k))
        f.append((j*4,(j+1)*4,(j+1)*4+3,j*4+3))
    f.extend([(3,2,1,0),tuple(range(steps*4,steps*4+4))])
    return primitive(name,v,f,key,0,mag=True)
for side in [-1,1]:
    strip('A762_R02_Magazine_FrontBead_'+str(side),side,.055,.99,.026,.071,.0009)
    strip('A762_R02_Magazine_FrontInnerBead_'+str(side),side,.08,.98,.155,.180,.0006)
    strip('A762_R02_Magazine_RearBead_'+str(side),side,.04,.99,.915,.952,.0006)
    for i,t in enumerate(np.linspace(.12,.925,10)):
        strip('A762_R02_Magazine_CrossRib_'+str(side)+'_'+str(i),side,float(t)-.007,float(t)+.007,.035,.17,.0010)
    # Broad pressed side panel: shallow continuous plane, bounded away from ribs.
    strip('A762_R02_Magazine_PressedPanel_'+str(side),side,.15,.92,.23,.85,.00018,'Magazine_Rebuilt')
    box('A762_R02_Magazine_FeedLip_'+str(side),(cx+side*.0083,-.0978,.0303),(.0040,.059,.0032),'MagazineEdge_Rebuilt',.0005,mag=True)
box('A762_R02_Magazine_Follower',(cx,-.098,.0193),(.015,.057,.0020),'MagazineInside_Rebuilt',.0005,mag=True)
box('A762_R02_Magazine_FrontCatch',(cx,-.133,.0230),(.015,.006,.007),'MagazineEdge_Rebuilt',.0007,mag=True)
box('A762_R02_Magazine_RearCatch',(cx,-.062,.0190),(.013,.006,.010),'MagazineEdge_Rebuilt',.0007,mag=True)
# Fixed magwell rim with an actual central opening; stays on the weapon root.
outer=[(cx+x,-.098+p) for x,p in rounded_rect(.0150,.039,.003,6)]
inner=[(cx+x,-.098+p) for x,p in rounded_rect(.0120,.036,.002,6)]
loop_prism('A762_R02_Receiver_MagwellCollar',outer,inner,.0314,.0363,axis=2)
report['changes']['magazine']='Replace entire scanned magazine by a closed curved shell, recessed mouth, follower, lips, catches, pressed side panels, covered reinforcement beads, and a closed slanted floorplate; all parts bound to original magazine bone.'

# Reference-shaped folding front sight: long slotted upright in side view, a
# thick hood and side bosses. The silhouette no longer rests on a thin wedge.
front=Vector(meta['markers_blender_root']['WPN_FrontSight']); rear=Vector(meta['markers_blender_root']['WPN_RearSight'])
fk='FrontSight_Rebuilt'; rk='RearSight_Rebuilt'; fg='FrontSight'; rg='RearSight'
box('A762_R02_FrontSight_PivotFoot',(cx,-.49144,.0775),(.017,.018,.0070),fk,.0006,fg)
outer=[(-.499,.079),(-.483,.079),(-.484,.104),(-.497,.105)]
inner=[(-.4955,.084),(-.4870,.084),(-.4878,.100),(-.4945,.100)]
loop_prism('A762_R02_FrontSight_SlottedUpright',outer,inner,cx-.0045,cx+.0045,axis=0,key=fk,group=fg)
hood=front+Vector((0,0,.0020))
lathe('A762_R02_FrontSight_ThickHood',tuple(hood),[(.0073,.0048),(.0097,.0048),(.0100,.0044),(.0100,-.0044),(.0097,-.0048),(.0073,-.0048),(.0070,-.0045),(.0070,.0045)],fk,5,112,group=fg)
for side in [-1,1]:
    pin('A762_R02_FrontSight_HoodBoss_'+str(side),(cx+side*.00945,front.y,.1134),.0046,fk,fg)
    for y in [-.4955,-.4865]: pin('A762_R02_FrontSight_PivotPin_'+str(side)+'_'+str(y),(cx+side*.0085,y,.0777),.0022,fk,fg)
box('A762_R02_FrontSight_PostFoot',(cx,front.y,.1044),(.0048,.0036,.0027),fk,.0002,fg)
extrude('A762_R02_FrontSight_FrontPost',[(cx-.0012,.1046),(cx+.0012,.1046),(cx+.00052,front.z),(cx-.00052,front.z)],front.y-.00080,front.y+.0008,key='SightInner',bevel=.000055,group=fg)

# Compact boxed rear sight, open hood and a recessed aperture plate. The marker
# is the peep center; there is no filled back face or atlas-textured fake hole.
box('A762_R02_RearSight_Base',(cx,rear.y-.007,.0995),(.024,.036,.0048),rk,.0006,rg)
outer=[(cx+x,.1102+z) for x,z in rounded_rect(.0101,.0108,.0022,8)]
inner=[(cx+x,.1112+z) for x,z in rounded_rect(.0068,.0070,.0012,8)]
loop_prism('A762_R02_RearSight_BoxedHood',outer,inner,rear.y-.0070,rear.y+.0065,key=rk,group=rg)
outer=[(cx+x,rear.z+z) for x,z in rounded_rect(.0075,.0075,.0018,16)]
# Same number/order as rounded rectangle; angular sampling need only preserve
# cyclic correspondence, not match the outer silhouette.
inner=[(cx+.0039*math.cos(math.tau*i/len(outer)),rear.z+.0039*math.sin(math.tau*i/len(outer))) for i in range(len(outer))]
loop_prism('A762_R02_RearSight_RecessedPeep',outer,inner,rear.y+.0025,rear.y+.0053,key=rk,group=rg)
for side in [-1,1]:
    pin('A762_R02_RearSight_Adjuster_'+str(side),(cx+side*.0102,rear.y-.0007,.1058),.0031,rk,rg)
box('A762_R02_RearSight_TopBlade',(cx,rear.y-.003,.1220),(.0020,.005,.0036),rk,.00022,rg)
report['changes']['sights']='Replace both heads. Front: slotted side-profile upright, thick open hood, side bosses and narrow independent post. Rear: compact boxed hood and a real recessed peep aperture. Original folding origins and alignment markers retained.'
report['changes']['muzzle']='Remove the full residual generated front section, build continuous barrel and gas tube, recessed flutes, a joined front block, secured bands and muzzle shoulders; keep detachable factory muzzle slot.'

# Export each sight at its established hinge; restore its source-rig binding.
for key,parts in sights.items():
    select(parts); active=parts[0]; bpy.context.view_layer.objects.active=active; bpy.ops.object.join(); active.name='SM_A762_'+key
    h=meta['hinges_ue_root'][key]; h=Vector((h[0],-h[1],h[2])); active.data.transform(Matrix.Translation(-h))
    select([active]); bpy.ops.export_scene.fbx(filepath=str(D/(active.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    active.data.transform(Matrix.Translation(h)); bind(active); active['independent_folding_head']=True
for ob in new: bind(ob)
for ob in magazines: bind(ob,'WPN_SOCKET_Magazine')
body.extend(new+magazines)
r.data.pose_position='REST'; bpy.context.view_layer.update()
select(body+[hands,r]); bpy.ops.export_scene.fbx(filepath=str(D/'SK_A762_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE'; s.frame_set(0); bpy.context.view_layer.update()
archive.hide_viewport=True; archive.hide_render=True
report['material_sources']={mat.name:'Refinement01' for ob in body for mat in ob.data.materials if mat and mat.name not in report['materials']}
report['editable']='A762_Reconstructed_Editable.blend'; report['exports']=['Exports/SK_A762_Manny.fbx','Exports/SM_A762_FrontSight.fbx','Exports/SM_A762_RearSight.fbx']
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_Reconstructed_Editable.blend'))
print('A762_REFERENCE_RECONSTRUCTION_AUTHORED',flush=True)
