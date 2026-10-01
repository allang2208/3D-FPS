"""A762 local receiver, guard and grip junction revision; metres in WPN_root."""
import bpy,bmesh,json,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
from shell_cleanup import close_slivers
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
OUT=O/'Exports';OUT.mkdir(exist_ok=True)
h,raw,p,t,m,uv,n,bone=G.body();extra=np.fromfile(O/'Input/Body_extra_uv.bin',np.float32).reshape(h['uv_sets']-1,len(t),3,2)
CX=.00056;STEEL='M_A762_R08_Receiver';CONTROL='M_A762_R08_Mechanism';NECK='M_A762_R08_GripNeck'
parts=[];diagnostics={}
def material(name):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color=(.25,.27,.29,1) if 'grip' in name.lower() or name.endswith('_0') else (.48,.5,.52,1)
    return mat
def meshob(name,verts,faces,slot=STEEL,target='Body'):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material(slot))
    ob['target']=target;ob['slot']=slot;parts.append(ob);return ob
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def normals(ob,smooth=True):
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm,dist=3e-7 if 'ContinuousGrip08' in ob.name else 1e-8,edges=list(bm.edges))
    if 'ContinuousGrip08' in ob.name:
        todo=set(bm.verts);components=[]
        while todo:
            component={todo.pop()};stack=list(component)
            while stack:
                vertex=stack.pop()
                for edge in vertex.link_edges:
                    other=edge.other_vert(vertex)
                    if other in todo:todo.remove(other);component.add(other);stack.append(other)
            components.append(component)
        if components:
            keep=max(components,key=len);remove=[v for v in bm.verts if v not in keep]
            if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
    wire=[e for e in bm.edges if not e.link_faces]
    if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    if 'ContinuousGrip08' in ob.name:close_slivers(bm)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for f in ob.data.polygons:f.use_smooth=smooth
    if smooth:
        active(ob);mod=ob.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=45
        bpy.ops.object.modifier_apply(modifier=mod.name)
def planar_uv(ob):
    layer=ob.data.uv_layers.get('UV0') or ob.data.uv_layers.new(name='UV0')
    for face in ob.data.polygons:
        axis=max(range(3),key=lambda k:abs(face.normal[k]));axes=[k for k in range(3) if k!=axis]
        for li in face.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]*35,v[axes[1]]*35)
def bevel(ob,width=.00065,segments=4):
    normals(ob,False);active(ob);mod=ob.modifiers.new('Manufactured edge radii','BEVEL');mod.width=width;mod.segments=segments;mod.limit_method='ANGLE';mod.angle_limit=math.radians(28);mod.use_clamp_overlap=True
    bpy.ops.object.modifier_apply(modifier=mod.name);normals(ob);planar_uv(ob);return ob
def prism(name,profile,x0,x1,slot=STEEL,width=.0006):
    count=len(profile);verts=[(x,y,z) for x in (x0,x1) for y,z in profile]
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(j,(j+1)%count,(j+1)%count+count,j+count) for j in range(count)]
    ob=meshob(name,verts,faces,slot);return bevel(ob,width)
def box(name,lo,hi,slot=STEEL,width=.0005):
    return prism(name,[(lo[1],lo[2]),(hi[1],lo[2]),(hi[1],hi[2]),(lo[1],hi[2])],lo[0],hi[0],slot,width)
def cylinder_x(name,x0,x1,y,z,r,slot=CONTROL):
    return prism(name,[(y+r*math.cos(a),z+r*math.sin(a)) for a in np.linspace(0,math.tau,48,endpoint=False)],x0,x1,slot,.00025)
def bezier(a,b,c,d,count=16):
    ts=np.linspace(0,1,count,endpoint=False)[:,None];a,b,c,d=map(np.array,(a,b,c,d))
    return (1-ts)**3*a+3*(1-ts)**2*ts*b+3*(1-ts)*ts**2*c+ts**3*d
def rounded_rect(x0,x1,y0,y1,r,count=8):
    result=[]
    for x,y,angle in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
        for a in np.linspace(math.radians(angle),math.radians(angle+90),count,endpoint=False):result.append((x+r*math.cos(a),y+r*math.sin(a)))
    return np.array(result)
def sweep(name,path,width,thickness,slot=CONTROL):
    """Closed rounded rectangular strap swept in YZ; no overlapping straight joins."""
    path=np.array(path);cross=rounded_rect(-width/2,width/2,-thickness/2,thickness/2,min(thickness*.27,.00065),4)
    verts=[];faces=[];ns=len(cross)
    for i,point in enumerate(path):
        tangent=path[(i+1)%len(path)]-path[(i-1)%len(path)];tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]])
        for x,r in cross:verts.append([CX+x,*(point+r*normal)])
    for i in range(len(path)):
        for j in range(ns):faces.append((i*ns+j,i*ns+(j+1)%ns,((i+1)%len(path))*ns+(j+1)%ns,((i+1)%len(path))*ns+j))
    ob=meshob(name,verts,faces,slot);normals(ob);planar_uv(ob);return ob
def source_piece(key,sid):
    if key=='Body':sh,sp,st,sm,su,sn=h,p,t,m,uv,n;sx=extra
    else:
        sh,sp,st,sm,su,sn=G.read(key);sp=sp*G.FLIP;sn=sn*[1,-1,1]
        sx=np.fromfile(O/'Input'/(key+'_extra_uv.bin'),np.float32).reshape(sh['uv_sets']-1,len(st),3,2)
    sel=sm==sid;vi,inv=np.unique(st[sel],return_inverse=True)
    ob=meshob(key+'_RetainedGrip',sp[vi].tolist(),inv.reshape(-1,3).tolist(),sh['slots'][sid],key)
    for i,layerdata in enumerate([su[sel],*sx[:,sel]]):
        layer=ob.data.uv_layers.new(name='UV'+str(i));values=layerdata.copy();values[:,:,1]=1-values[:,:,1];layer.data.foreach_set('uv',values.ravel())
    for face in ob.data.polygons:face.use_smooth=True
    ob.data.normals_split_custom_set(sn[sel].reshape(-1,3).tolist())
    return ob,sp,st[sel]
def trim_grip(ob,z):
    me=ob.data;attr=me.attributes.new('OriginalCornerNormal','FLOAT_VECTOR','CORNER')
    attr.data.foreach_set('vector',np.array([tuple(v.vector) for v in me.corner_normals],np.float32).ravel())
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,z),plane_no=(0,0,1),clear_outer=True)
    if ob['target']=='Body':
        oldweb=[f for f in bm.faces if f.calc_center_median().y<.011 and f.calc_center_median().z>-.033]
        bmesh.ops.delete(bm,geom=oldweb,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(me);bm.free()
    for f in me.polygons:f.use_smooth=True
    ns=[d.vector.normalized() if d.vector.length_squared>1e-14 else Vector((0,0,1)) for d in me.attributes['OriginalCornerNormal'].data]
    me.normals_split_custom_set(ns)
def smooth_ring(ring,steps=4):
    result=ring.copy()
    for _ in range(steps):result=.5*result+.25*np.roll(result,1,axis=0)+.25*np.roll(result,-1,axis=0)
    return result

def restore_lower_normals(ob,original,cut):
    original.calc_loop_triangles()
    co=np.array([tuple(v.co) for v in original.vertices]);tris=np.array([tuple(t.vertices) for t in original.loop_triangles])
    loops=np.array([tuple(t.loops) for t in original.loop_triangles]);norm=np.array([tuple(v.vector) for v in original.corner_normals])[loops]
    tree=BVHTree.FromPolygons(co.tolist(),tris.tolist(),all_triangles=True)
    normals={}
    for v in ob.data.vertices:
        w=np.clip((cut-.006-v.co.z)/.012,0,1)
        if w<=0:continue
        loc,_,index,_=tree.find_nearest(v.co)
        if index is None:continue
        a,b,c=co[tris[index]];d=b-a;e=c-a;f=np.array(loc)-a
        gram=np.array([[d@d,d@e],[d@e,e@e]])
        if abs(np.linalg.det(gram))<1e-20:continue
        u,vv=np.linalg.solve(gram,[d@f,e@f]);ns=norm[index,0]*(1-u-vv)+norm[index,1]*u+norm[index,2]*vv
        normals[v.index]=(ns/max(np.linalg.norm(ns),1e-12),w)
    result=[]
    for loop,cn in zip(ob.data.loops,ob.data.corner_normals):
        ns=np.array(cn.vector)
        if loop.vertex_index in normals:
            old,w=normals[loop.vertex_index];ns=ns*(1-w)+old*w
        result.append(ns/max(np.linalg.norm(ns),1e-12))
    ob.data.normals_split_custom_set(result)

def blend_grip_boundary(ob,cut,ring,tangent,band=.012):
    """Conform the cut source band to the same polygon as the new neck.
    UVs and all geometry below the transition band retain their source values.
    """
    me=ob.data;center=(ring.min(0)+ring.max(0))*.5;count=len(ring)
    angles=np.unwrap(np.arctan2(ring[:,1]-center[1],ring[:,0]-center[0]))
    coords=np.array([tuple(v.co) for v in me.vertices]);oldnorm=np.array([tuple(v.vector) for v in me.corner_normals])
    weights=np.clip((coords[:,2]-(cut-band))/band,0,1);weights=weights**2*(3-2*weights)
    field=np.zeros_like(coords)
    for i,v in enumerate(coords):
        if weights[i]<=0:continue
        angle=math.atan2(v[1]-center[1],v[0]-center[0]);angle=(angle-angles[0])%math.tau+angles[0]
        j=int(np.searchsorted(angles,angle,side='right')-1)%count;k=(j+1)%count
        # Exact intersection with the same straight low-ring edge used by the loft.
        d=np.array([math.cos(angle),math.sin(angle)]);a=ring[j,:2]-center[:2];e=ring[k,:2]-ring[j,:2]
        cross=lambda a,b:a[0]*b[1]-a[1]*b[0]
        f=np.clip(cross(a,d)/cross(d,e),0,1);r=ring[j]*(1-f)+ring[k]*f;dt=tangent[j]*(1-f)+tangent[k]*f
        target=r[:2]+dt[:2]*(v[2]-cut)
        me.vertices[i].co.x=(1-weights[i])*v[0]+weights[i]*target[0]
        me.vertices[i].co.y=(1-weights[i])*v[1]+weights[i]*target[1]
        nr=np.cross(np.r_[e,0.],dt);nr/=np.linalg.norm(nr);field[i]=nr
    me.update()
    ns=[]
    for li,loop in enumerate(me.loops):
        w=weights[loop.vertex_index];nr=oldnorm[li]*(1-w)+field[loop.vertex_index]*w
        ns.append(nr/max(np.linalg.norm(nr),1e-12))
    me.normals_split_custom_set(ns)
def loft(name,low,high,slot,target,steps=24,tangent=None):
    count=len(low);verts=[];faces=[];length=high[0,2]-low[0,2]
    a=(high-low)/length if tangent is None else tangent;b=np.tile([0,0,1.],(count,1))
    for k in range(steps+1):
        s=k/steps;points=low*(2*s**3-3*s*s+1)+a*length*(s**3-2*s*s+s)+high*(-2*s**3+3*s*s)+b*length*(s**3-s*s)
        verts.extend(points.tolist())
    for k in range(steps):
        for j in range(count):faces.append((k*count+j,k*count+(j+1)%count,(k+1)*count+(j+1)%count,(k+1)*count+j))
    for offset in (0,steps*count):
        center=len(verts);verts.append(np.mean(verts[offset:offset+count],axis=0).tolist())
        for j in range(count):faces.append((center,offset+j,offset+(j+1)%count))
    ob=meshob(name,verts,faces,slot,target);normals(ob,False)
    for f in ob.data.polygons:f.use_smooth=f.index<steps*count
    planar_uv(ob)
    # Continuous side UVs; caps retain their planar projection.
    layer=ob.data.uv_layers.active;lengths=np.r_[0,np.cumsum(np.linalg.norm(np.roll(low,-1,axis=0)-low,axis=1))]*35
    for k in range(steps):
        for j in range(count):
            face=ob.data.polygons[k*count+j]
            for li in face.loop_indices:
                vid=ob.data.loops[li].vertex_index;ri,cj=divmod(vid,count)
                u=lengths[-1] if j==count-1 and cj==0 else lengths[cj]
                layer.data[li].uv=(u,ri/steps*length*35)
    return ob

# The outline follows the original reference; side plates have real interior faces.
outline=[(-.195,.052),(.088,.052),(.088,.025),(.071,.019),(.054,.014),(.010,.014),
         (-.010,.017),(-.041,.017),(-.060,.028),(-.063,.034),(-.134,.034),(-.145,.039),(-.173,.040),(-.195,.040)]
for sign,label in [(1,'Left'),(-1,'Right')]:
    outer=CX+sign*.0148;inner=CX+sign*.0129
    prism('Receiver_'+label+'_ClosedSide',outline,min(inner,outer),max(inner,outer),STEEL,.00065)
# Floor pieces leave the magazine well and trigger entry open.
box('Receiver_FrontFloor',(CX-.014,-.195,.040),(CX+.014,-.137,.0422),STEEL,.00045)
box('Receiver_CatchBridge',(CX-.014,-.061,.0265),(CX+.014,-.043,.029),STEEL,.00045)
prism('Receiver_RearFloor',[(.007,.014),(.054,.014),(.071,.019),(.088,.025),(.088,.028),(.071,.022),(.054,.017),(.007,.017)],CX-.0142,CX+.0142,STEEL,.0004)
box('Receiver_RearEnd',(CX-.014,.084,.025),(CX+.014,.088,.052),STEEL,.0005)
box('Receiver_FrontEnd',(CX-.014,-.195,.042),(CX+.014,-.191,.052),STEEL,.0004)
# Rounded upper channel. Its right-hand ejection port remains a functional opening.
outer=rounded_rect(CX-.019,CX+.019,.048,.075,.0055,12)
inner=rounded_rect(CX-.017,CX+.017,.050,.073,.0035,12)
verts=[(x,y,z) for y in (-.195,.089) for loop in (outer,inner) for x,z in loop];count=len(outer);faces=[]
for j in range(count):
    q=(j+1)%count
    faces += [(j,q,2*count+q,2*count+j),(count+j,3*count+j,3*count+q,count+q),
              (j,count+j,count+q,q),(2*count+j,2*count+q,3*count+q,3*count+j)]
channel=meshob('Receiver_UpperChannel',verts,faces);normals(channel)
cutter=box('Temporary_PortCut',(CX-.026,-.189,.058),(CX-.009,-.063,.085),STEEL,.003)
active(channel);mod=channel.modifiers.new('Native ejection opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
bpy.ops.object.modifier_apply(modifier=mod.name);parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
bevel(channel,.00045,3)
# Controlled folded lips replace the wavy, torn upper strips.
for sign,label in [(1,'Left'),(-1,'Right')]:
    x=CX+sign*.0183
    profile=[(-.017,.071),(-.009,.074),(.078,.074),(.084,.071),(.084,.069),(-.017,.069)]
    prism('UpperLip_'+label,profile,min(x,x+sign*.0015),max(x,x+sign*.0015),STEEL,.00045)
    # Reference selector, detent and long side lever, retained at their native stations.
    base=CX+sign*.015;tip=base+sign*.0021
    cylinder_x('SelectorSeat_'+label,min(base,tip),max(base,tip),.0145,.0315,.0082)
    cylinder_x('SelectorHub_'+label,min(tip,tip+sign*.0012),max(tip,tip+sign*.0012),.0145,.0315,.0045)
    selector=rounded_rect(.013,.036,.0288,.0342,.0026,10)
    prism('SelectorPaddle_'+label,selector,min(tip,tip+sign*.0018),max(tip,tip+sign*.0018),CONTROL,.0004)
    rail_x=CX+sign*.0191
    prism('SideTrack_'+label,[(-.034,.051),(.082,.051),(.085,.054),(.082,.057),(-.034,.057)],min(rail_x,rail_x+sign*.0012),max(rail_x,rail_x+sign*.0012),STEEL,.0006)
    # The dark recess is shallow and bounded by a clean machined rim.
    slot=rounded_rect(-.016,.054,.0525,.0553,.0013,8)
    prism('TrackRecess_'+label,slot,min(rail_x+sign*.00125,rail_x+sign*.00135),max(rail_x+sign*.00125,rail_x+sign*.00135),'M_A762_Inside',.00003)
    arm=[(-.031,.056),(-.035,.053),(-.044,.023),(-.043,.020),(-.040,.022),(-.032,.046),(-.028,.052)]
    prism('SideLever_'+label,arm,min(rail_x+sign*.0014,rail_x+sign*.0032),max(rail_x+sign*.0014,rail_x+sign*.0032),CONTROL,.00045)
    cylinder_x('SideLeverPivot_'+label,min(rail_x+sign*.0015,rail_x+sign*.0035),max(rail_x+sign*.0015,rail_x+sign*.0035),-.031,.054,.0032)
# Slim tapered catch, replacing the previous rectangular slab and side shards.
cheek=[(-.061,.025),(-.046,.023),(-.046,.008),(-.049,-.0085),(-.057,-.0085),(-.061,.001)]
for sign in (-1,1):
    a,b=CX+sign*.0043,CX+sign*.0074
    prism('CatchCheek_'+str(sign),cheek,min(a,b),max(a,b),CONTROL,.00075)
    cylinder_x('CatchPivot_'+str(sign),min(b,b+sign*.0007),max(b,b+sign*.0007),-.052,-.0015,.0023)
box('CatchTopBridge',(CX-.007,-.060,.024),(CX+.007,-.045,.029),CONTROL,.00065)
prism('CatchLever',[(-.054,.013),(-.051,.010),(-.055,-.018),(-.0575,-.021),(-.060,-.020),(-.057,-.016)],CX-.0033,CX+.0033,CONTROL,.00045)
# Guard belongs to the fixed receiver, so all rear grips retain a complete loop.
path=np.concatenate([bezier((-.044,.018),(-.025,.018),(-.01,.018),(.010,.018),16),
    bezier((.010,.018),(.010,.006),(.012,-.012),(.001,-.018),24),
    bezier((.001,-.018),(-.008,-.022),(-.029,-.022),(-.037,-.018),24),
    bezier((-.037,-.018),(-.046,-.015),(-.045,.005),(-.044,.018),24)])
sweep('Continuous_TriggerGuard',path,.009,.0026)
blade=np.concatenate([bezier((-.005,.018),(-.008,.007),(-.006,-.003),(-.019,-.015),32),
    bezier((-.019,-.015),(-.020,-.017),(-.017,-.017),(-.015,-.014),12),
    bezier((-.015,-.014),(-.004,-.006),(-.001,.006),(-.001,.018),32),np.array([[-.001,.018]])])
prism('TriggerBlade',blade,CX-.003,CX+.003,CONTROL,.00035)

# Bolt-side fragments are the moving bolt's shell, not a fixed receiver plate.
# Rebuild its skin at the same native bone station; preserve the WPN_bolt motion.
bolt_shell=prism('Bolt_CleanCarrier',[(-.186,.056),(-.186,.073),(-.173,.076),(-.031,.076),(-.021,.068),(-.021,.056)],-.018,-.0155,STEEL,.0008)
bolt_shell['bone']='WPN_bolt'
bolt_handle=box('Bolt_ChargingHandle',(-.0265,-.034,.057),(-.016,-.023,.065),CONTROL,.0015)
bolt_handle['bone']='WPN_bolt'

# Common rifle-side contact follows the factory grip's actual mounting contour.
factory=m==h['slots'].index('M_A762_FactoryRearGrip')
contact=smooth_ring(G.section(p,t[factory],.006,128),5);contact[:,2]=.0125
shoe_low=contact.copy();shoe_low[:,2]=.0122
shoe_high=contact.copy();shoe_high[:,0]=CX+(shoe_high[:,0]-CX)*1.30
shoe_high[:,1]=.035+(shoe_high[:,1]-.035)*1.05;shoe_high[:,2]=.0182
loft('Receiver_GripSeat',shoe_low,shoe_high,STEEL,'Body',6)
for key,cut in [('Body',-.018),('phantom_reargrip',-.010),('balanced_reargrip',-.022),('stable_antislip_reargrip',-.032)]:
    if key=='Body':sid=h['slots'].index('M_A762_FactoryRearGrip')
    else:sh,*_=G.read(key);sid=sh['slots'].index('A762_'+key+'_0')
    ob,sp,st=source_piece(key,sid)
    low=smooth_ring(G.section(sp,st,cut-.0015,128),3)
    below=smooth_ring(G.section(sp,st,cut-.0035,128),3)
    tangent=smooth_ring((low-below)/.002,5);tangent[:,:2]=np.clip(tangent[:,:2],-.9,.9);tangent[:,2]=1
    trim_grip(ob,cut)
    high=contact.copy();high[:,2]=.01255
    slot='M_A762_FactoryRearGrip_Neck08' if key=='Body' else NECK
    if key=='phantom_reargrip':slot='A762_phantom_reargrip_Neck08'
    neck=loft(key+'_FittedNeck',low,high,slot,key,tangent=tangent)
    if key=='phantom_reargrip':
        diagnostics[key]={'cut_z_m':cut,'retained_lower_mesh':ob.name,'contact_vertices':high.tolist(),'overlap_with_receiver_seat_mm':.35,'lower_neck_overlap_mm':1.5,'lattice_geometry':'original retained, no voxel remesh'}
        continue
    original=ob.data.copy()
    # Meshy grips contain overlapping disconnected skins. A local union of the
    # grip and its neck removes the hidden cuts and produces one closed shell.
    active(ob);neck.select_set(True);parts.remove(neck);bpy.ops.object.join()
    ob.data.remesh_voxel_size=.00018;ob.data.remesh_voxel_adaptivity=0
    bpy.ops.object.voxel_remesh()
    group=ob.vertex_groups.new(name='NeckFinish')
    for v in ob.data.vertices:
        w=max(0.,min(1.,(v.co.z-(cut-.015))/.010))
        if w>0:group.add([v.index],w,'REPLACE')
    mod=ob.modifiers.new('Neck surface continuity','SMOOTH');mod.factor=.6;mod.iterations=45;mod.vertex_group=group.name
    bpy.ops.object.modifier_apply(modifier=mod.name)
    target_faces=12000 if key=='Body' else 36000
    mod=ob.modifiers.new('Preserve close-up budget','DECIMATE');mod.ratio=min(1.,target_faces/max(1,len(ob.data.polygons)*2))
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.name=key+'_ContinuousGrip08';ob['slot']='M_A762_FactoryRearGrip_Clean08' if key=='Body' else 'A762_'+key+'_Body08'
    ob.data.materials.clear();ob.data.materials.append(material(ob['slot']))
    normals(ob,False)
    for f in ob.data.polygons:f.use_smooth=True;f.material_index=0
    planar_uv(ob)
    restore_lower_normals(ob,original,cut);bpy.data.meshes.remove(original)
    diagnostics[key]={'cut_z_m':cut,'retained_lower_mesh':ob.name,'contact_vertices':high.tolist(),
        'overlap_with_receiver_seat_mm':.35,'lower_neck_join':'continuous union surface','union_voxel_mm':.18}

# Production edit plan: only receiver/guard, old catch blocks and grip sections.
cent=p[t].mean(1)
delete=(m==h['slots'].index('M_A762_Receiver'))|(m==h['slots'].index('M_A762_FactoryRearGrip'))|(m==h['slots'].index('M_A762_Inside'))
oldcatch=(m==h['slots'].index('M_A762_FrontAssembly_Rebuilt'))&(cent[:,1]>-.062)&(cent[:,1]<-.015)&(cent[:,2]<.0305)
delete|=oldcatch
delete|=m==h['slots'].index('M_A762_Bolt')
plan={'Body':{'delete_triangles':np.nonzero(delete)[0].tolist(),'old_catch_triangles':int(oldcatch.sum())},
    'grips':diagnostics,'body_slot_replacements':['M_A762_Receiver','M_A762_FactoryRearGrip','M_A762_Inside','M_A762_Bolt'],
    'reference':'A762Meshy20260920/References/a762_side.png','runtime_tested':False}

# Export indexed buffers with all surviving UV channels and corner normals.
frames=json.loads((O/'Input/frames.json').read_text());root=np.array(frames['root_rest']);exported=[]
for ob in parts:
    me=ob.data;me.calc_loop_triangles();target=ob['target'];isbody=target=='Body';uvsets=h['uv_sets'] if isbody else G.read(target)[0]['uv_sets']
    co=np.array([tuple(v.co) for v in me.vertices],np.float64)
    nn=np.array([tuple(v.vector) for v in me.corner_normals],np.float64)
    bind=root if ob.get('bone','WPN_root')=='WPN_root' else np.linalg.inv(np.array(frames['bind_to_root'][ob['bone']]))
    if isbody:co=G.transform(co,bind);nn=nn@bind[:3,:3].T
    co/=G.FLIP;nn*=np.array([1,-1,1])
    tris=np.array([tuple(f.vertices) for f in me.loop_triangles],np.int32);loops=np.array([tuple(f.loops) for f in me.loop_triangles],np.int32)
    # Degenerate dissolved n-gons can tessellate a zero-thickness folded pair.
    # Both duplicate triangles are internal; discard the pair, not one side.
    _,inverse,counts=np.unique(np.sort(tris,axis=1),axis=0,return_inverse=True,return_counts=True)
    keep=counts[inverse]==1;tris=tris[keep];loops=loops[keep]
    channels=[]
    for i in range(uvsets):
        if i<len(me.uv_layers):values=np.array([tuple(v.uv) for v in me.uv_layers[i].data],np.float32);values[:,1]=1-values[:,1];channels.append(values[loops])
        else:channels.append(np.full((len(tris),3,2),.5 if i==1 else 0,np.float32))
    head={'name':ob.name,'target':target,'slot':ob['slot'],'vertices':len(co),'triangles':len(tris),'uv_sets':uvsets,'bone':ob.get('bone','WPN_root') if isbody else None}
    with (OUT/(ob.name+'.bin')).open('wb') as f:
        f.write((json.dumps(head)+'\n').encode());co.astype(np.float32).tofile(f);tris.tofile(f);nn[loops].astype(np.float32).tofile(f)
        for channel in channels:channel.astype(np.float32).tofile(f)
    exported.append(head)
plan['parts']=exported;(O/'authoring.json').write_text(json.dumps(plan,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_ReceiverGrip08.blend'))
for key in sorted({ob['target'] for ob in parts if ob['target']!='Body'}):
    group=[ob for ob in parts if ob['target']==key];active(group[0])
    for ob in group:ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/('SM_A762_'+key+'_R08.fbx')),use_selection=True,object_types={'MESH'},global_scale=1.,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
print('A762_DETAIL_AUTHORED',len(parts),{key:sum(x['triangles'] for x in exported if x['target']==key) for key in ['Body','phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']},flush=True)
