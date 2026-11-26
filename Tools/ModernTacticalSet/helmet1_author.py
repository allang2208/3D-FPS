"""TS01 helmet detail revision. Native cm, independent heads, authored surfaces."""
import bpy,bmesh,numpy as np,json,math,sys,importlib.util,hashlib,copy
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'HelmetDetailR1'
for folder in ['Models','Exports','Textures','SurfaceSources','Authored','Icons','Logs']:(R/folder).mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('ts01_old_helpers',S/'author_set.py');A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def unit(v):
    v=np.asarray(v,float);return v/max(np.linalg.norm(v),1e-12)
def xyz(p):return [float(p[0])*.01,-float(p[1])*.01,float(p[2])*.01]
FAMILIES={
 'Composite':([.48,.365,.253],.82,0.,2048,'coat',8.,.26),
 'Polymer':([.365,.278,.193],.68,0.,1024,'mould',4.,.28),
 'Rubber':([.125,.100,.077],.86,0.,1024,'rubber',4.,.24),
 'Webbing':([.385,.285,.191],.87,0.,1024,'webbing',4.,.25),
 'LoopPile':([.285,.226,.158],.93,0.,1024,'pile',4.,.22),
 'PadMesh':([.181,.143,.103],.90,0.,1024,'mesh',4.,.23),
 'Metal':([.249,.219,.179],.44,1.,1024,'metal',4.,.5)}

def noise(n,f,seed):
    rng=np.random.default_rng(seed);a=rng.normal(size=(n,n));freq=np.fft.fftfreq(n)*n;g=np.exp(-(freq[:,None]**2+freq[None,:]**2)/(2*f*f));a=np.fft.ifft2(np.fft.fft2(a)*g).real;a/=max(a.std(),1e-8);return np.clip(a,-2.5,2.5).astype(np.float32)/2.5

def textures():
    fields={}
    for j,(name,(color,rough,metal,n,kind,span,specular)) in enumerate(FAMILIES.items()):
        yy,xx=np.mgrid[:n,:n].astype(np.float32);x=xx/n;y=yy/n;large=noise(n,5,21+j);grain=noise(n,n/14,71+j);fine=noise(n,n/5,191+j)
        h=.0011*grain+.00035*fine
        if kind=='coat':h=.0020*grain+.00042*fine
        elif kind=='rubber':h=.0013*grain+.0004*fine
        elif kind in ['webbing','pile','mesh']:
            warp=np.cos(2*math.pi*x*128);weft=np.cos(2*math.pi*y*96)
            h=.0035*warp*weft+.0008*fine
            if kind=='webbing':h+=.004*np.cos(2*math.pi*x*24)
            elif kind=='pile':h=.005*grain+.0018*fine
            else:h+=.008*np.maximum(0,np.cos(2*math.pi*x*32)*np.cos(2*math.pi*y*40))**6
        elif kind=='metal':h=.00055*grain+.00015*np.sin(2*math.pi*x*220)
        # The normal and roughness derive from the same physical micro-surface.
        h=(h*4+np.roll(h,1,0)+np.roll(h,-1,0)+np.roll(h,1,1)+np.roll(h,-1,1))/8
        dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n)
        slope=np.sqrt(dx*dx+dy*dy);limit=np.maximum(1,slope/.42);dx/=limit;dy/=limit
        normal=np.stack([-dx,-dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
        base=np.asarray(color)[None,None,:]*(1+.035*large[:,:,None]+.035*grain[:,:,None]);r=np.clip(rough+.035*large+.045*grain,.28,.98);ao=np.clip(.97+.025*grain,.88,1)
        A.save_map(R/'Textures'/f'H1_{name}_BaseColor.png',base,True);A.save_map(R/'Textures'/f'H1_{name}_NormalGL.png',normal*.5+.5)
        A.save_map(R/'Textures'/f'H1_{name}_ORM.png',np.stack([ao,r,np.full_like(r,metal)],-1));np.savez_compressed(R/'SurfaceSources'/f'{name}.npz',height_cm=h,span_cm=span)
        fields[name]=dict(resolution=n,tile_cm=span,roughness=rough,metallic=metal,specular=specular,kind=kind,source='authored physical microheight; not a scan')
        print('HELMET_SURFACE_AUTHORED',name,flush=True)
    write(R/'surfaces.json',fields)

def materials():
    result={}
    for name,(color,rough,metal,n,kind,span,specular) in FAMILIES.items():
        m=bpy.data.materials.new('H1_'+name);m.use_nodes=True;m.diffuse_color=(*color,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=specular
        if kind in ['webbing','pile','mesh']:bs.inputs['Sheen Weight'].default_value=.22 if kind=='pile' else .10
        for c in ['BaseColor','NormalGL','ORM']:
            t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/'Textures'/f'H1_{name}_{c}.png'),check_existing=True)
            if c!='BaseColor':t.image.colorspace_settings.name='Non-Color'
            if c=='BaseColor':m.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color'])
            elif c=='NormalGL':
                q=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(t.outputs['Color'],q.inputs['Color']);m.node_tree.links.new(q.outputs[0],bs.inputs['Normal'])
            else:
                q=m.node_tree.nodes.new('ShaderNodeSeparateColor');m.node_tree.links.new(t.outputs['Color'],q.inputs[0]);m.node_tree.links.new(q.outputs['Green'],bs.inputs['Roughness']);m.node_tree.links.new(q.outputs['Blue'],bs.inputs['Metallic'])
        m['PhysicalTile_cm']=span;result[name]=m
    return result

def project_uv(ob):
    me=ob.data;me.update();uv=me.uv_layers.active or me.uv_layers.new(name='PhysicalUV')
    name=me.materials[0].name.removeprefix('H1_').split('.')[0];span=FAMILIES[name][5]
    for face in me.polygons:
        dominant=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=dominant]
        for li in face.loop_indices:
            p=A.nativept(me.vertices[me.loops[li].vertex_index].co);uv.data[li].uv=(p[axes[0]]/span,p[axes[1]]/span)

def finish_normals(ob):
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for edge in bm.edges:
        if len(edge.link_faces)==2:edge.smooth=edge.calc_face_angle(0)<math.radians(55)
    bm.to_mesh(ob.data);bm.free()
    for f in ob.data.polygons:f.use_smooth=True
    bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('ManufacturedCornerNormals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40;A.apply(ob,mod.name)

def mesh(name,p,f,mat,bevel=0):
    ob=A.mesh(name,p,f,mat,bevel=0,do_bind=False)
    if bevel:
        mod=ob.modifiers.new('PhysicalEdgeRadius','BEVEL');mod.width=bevel*.01;mod.segments=5 if HIGH else 3;A.apply(ob,mod.name)
    project_uv(ob);finish_normals(ob);return ob

def box(name,c,size,mat,bevel=.08,basis=None):
    basis=np.eye(3) if basis is None else np.asarray(basis);c=np.asarray(c);p=[c+basis@np.array([x*size[0]/2,y*size[1]/2,z*size[2]/2]) for x in [-1,1] for y in [-1,1] for z in [-1,1]]
    return mesh(name,p,[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]],mat,bevel)

def tube(name,path,radius,mat,sides=8,closed=False):
    path=np.asarray(path);n=len(path);p=[];prior=None
    for i,v in enumerate(path):
        tangent=unit(path[(i+1)%n]-path[(i-1)%n]) if closed else unit(path[min(i+1,n-1)]-path[max(0,i-1)])
        ref=np.array([0,0,1.]) if abs(tangent[2])<.9 else np.array([0,1.,0]);u=unit(np.cross(tangent,ref)) if prior is None else unit(prior-tangent*np.dot(prior,tangent));v2=np.cross(tangent,u);prior=u
        for k in range(sides):p.append(v+radius*(u*math.cos(math.tau*k/sides)+v2*math.sin(math.tau*k/sides)))
    f=[[i*sides+k,i*sides+(k+1)%sides,((i+1)%n)*sides+(k+1)%sides,((i+1)%n)*sides+k] for i in range(n if closed else n-1) for k in range(sides)]
    if not closed:f += [list(reversed(range(sides))),list(range((n-1)*sides,n*sides))]
    return mesh(name,p,f,mat)

def carve(ob,tool):
    bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('ManufacturedThroughSlot','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool;A.apply(ob,mod.name);A.OBJECTS.remove(tool);bpy.data.objects.remove(tool,do_unlink=True)

def deform(ob,fn,max_edge=.7):
    bm=bmesh.new();bm.from_mesh(ob.data)
    for _ in range(6):
        long=[e for e in bm.edges if e.calc_length()*100>max_edge]
        if not long:break
        bmesh.ops.subdivide_edges(bm,edges=long,cuts=1,use_grid_fill=True)
    bm.to_mesh(ob.data);bm.free()
    for v in ob.data.vertices:v.co=xyz(fn(A.nativept(v.co)))
    if ob.name.startswith('ARC_Rail_'):
        # Boolean slot tessellation can leave an opposing duplicate triangle
        # pair as an internal zero-thickness fin. Remove those source faces.
        me=ob.data;me.calc_loop_triangles();triangles=[tuple(t.vertices) for t in me.loop_triangles];groups={}
        for face in triangles:groups.setdefault(tuple(sorted(face)),[]).append(face)
        duplicates={key for key,faces in groups.items() if len(faces)>1}
        if duplicates:
            faces=[face for face in triangles if tuple(sorted(face)) not in duplicates];used=sorted({i for face in faces for i in face});lookup={vi:i for i,vi in enumerate(used)}
            clean=bpy.data.meshes.new(me.name+'_CleanSlots');clean.from_pydata([me.vertices[i].co[:] for i in used],[],[[lookup[i] for i in face] for face in faces]);clean.update()
            for mat in me.materials:clean.materials.append(mat)
            ob.data=clean;ob['RemovedInternalDuplicateTriangles']=len(triangles)-len(faces);bpy.data.meshes.remove(me)
    project_uv(ob);finish_normals(ob)

def extrude(name,outline,depth,mat,bevel=.1):
    p=[[x,d,z] for d in [-depth/2,depth/2] for x,z in outline];n=len(outline);f=[list(reversed(range(n))),list(range(n,n*2))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    return mesh(name,p,f,mat,bevel)

def screw(name,center,axis,r=.30):
    center=np.asarray(center);axis=unit(axis);u=unit(np.cross(axis,[0,0,1] if abs(axis[2])<.9 else [0,1,0]));v=np.cross(axis,u);n=36 if HIGH else 24
    rings=[(r*.92,-.08),(r,0),(r,.09),(r*.87,.14),(r*.42,.14),(r*.42,.035)];points=[]
    for ri,(rad,depth) in enumerate(rings):
        for k in range(n):
            a=math.tau*k/n;rr=rad if ri<4 else rad*math.cos(math.pi/6)/math.cos((a+math.pi/6)%(math.pi/3)-math.pi/6)
            points.append(center+axis*depth+(u*math.cos(a)+v*math.sin(a))*rr)
    faces=[[i*n+k,i*n+(k+1)%n,(i+1)*n+(k+1)%n,(i+1)*n+k] for i in range(len(rings)-1) for k in range(n)];faces += [list(reversed(range(n))),list(range((len(rings)-1)*n,len(rings)*n))]
    return mesh(name,points,faces,'Metal')

def rr(w,h,r,steps=6):
    return [(cx+r*math.cos(a),cy+r*math.sin(a)) for cx,cy,start in [(w-r,h-r,0),(-w+r,h-r,90),(-w+r,-h+r,180),(w-r,-h+r,270)] for a in np.linspace(math.radians(start),math.radians(start+90),steps,endpoint=False)]

def native(rig):
    head=read(R/'Inputs'/f'{rig}_Head.json');body=read(R/'Inputs'/f'{rig}_Body.json');hb=head['bones']['head'];bb=body['bones']['head'];p=np.asarray(head['positions']);p=(p-hb['position'])@np.linalg.inv(np.asarray(hb['axes']))@np.asarray(bb['axes'])+bb['position'];return head,body,p

def build(rig,high=False):
    global HIGH
    HIGH=high;bpy.ops.wm.read_factory_settings(use_empty=True);A.MATS=materials();A.OBJECTS=[];head,body,hp=native(rig);headbone=body['bones']['head'];top=float(hp[:,2].max());upper=hp[(hp[:,2]>top-12)&(hp[:,2]<top-2)];cx=float(np.median(upper[:,0]));cy=float((np.percentile(upper[:,1],98)+np.percentile(upper[:,1],2))/2)
    rx=float(np.quantile(abs(upper[:,0]-cx),.993)+1.3);ry=float((np.percentile(upper[:,1],99)-np.percentile(upper[:,1],1))/2+1.65);cz=top-10.2;rz=11.7;center=np.array([cx,cy,cz]);headtree=BVHTree.FromPolygons(hp.tolist(),head['triangles'],all_triangles=True)
    def shell(theta,t):
        edge=top-11.6+2.15*abs(math.sin(theta))**6-3.6*max(0,-math.cos(theta))**2
        phi=math.acos(np.clip((edge-cz)/rz,-1,1))*t;rad=math.sin(phi);s=math.sin(theta);c=math.cos(theta)
        return center+np.array([rx*rad*np.sign(s)*abs(s)**.96,ry*rad*c,rz*math.cos(phi)])
    def sn(theta,t):
        p=shell(theta,t);return unit((p-center)/np.array([rx*rx,ry*ry,rz*rz]))
    n=176 if high else 128;m=52 if high else 38;outer=[shell(math.tau*i/n,j/m) for j in range(1,m+1) for i in range(n)];inner=[p-sn(math.tau*(k%n)/n,(k//n+1)/m)*.65 for k,p in enumerate(outer)];p=outer+[shell(0,0)]+inner+[shell(0,0)-[0,0,.65]];off=len(outer)+1;f=[]
    for layer,start in [(0,0),(1,off)]:
        ff=[]
        for j in range(m-1):
            for i in range(n):a=start+j*n+i;b=start+j*n+(i+1)%n;ff.append([a,b,b+n,a+n])
        pole=start+m*n;ff.extend([[pole,start+i,start+(i+1)%n] for i in range(n)])
        f.extend(ff if layer==0 else [list(reversed(face)) for face in ff])
    f.extend([[(m-1)*n+i,(m-1)*n+(i+1)%n,off+(m-1)*n+(i+1)%n,off+(m-1)*n+i] for i in range(n)])
    crown=mesh('Continuous_Composite_Shell',p,f,'Composite');crown['WallThickness_cm']=.65;crown['Source']='independent native '+rig+' scalp envelope';crown['Construction']='Closed outer/inner shell with open head cavity and connected lower rim'
    tube('Continuous_Rubber_Edge_Binding',[shell(t,1)-sn(t,1)*.12 for t in np.linspace(0,math.tau,n,endpoint=False)],.29,'Rubber',12 if high else 10,True)
    # Curved rounded textile patches with sewn perimeter and actual backing.
    def patch(name,theta,t,w,h,mat='LoopPile',offset=.11,pad=False):
        corners=rr(w/2,h/2,min(.45,w/5,h/5),8 if high else 6);boundary=[]
        # Long straight edges must follow the shell too. Otherwise their chords
        # sink below the curved shell, cutting visible wedges out of the cloth.
        for i,a in enumerate(corners):
            a=np.asarray(a);b=np.asarray(corners[(i+1)%len(corners)]);steps=max(1,math.ceil(np.linalg.norm(b-a)/(.30 if high else .40)))
            boundary.extend([tuple(a+(b-a)*k/steps) for k in range(steps)])
        levels=8 if high else 6;points=[shell(theta,t)+sn(theta,t)*(offset-(.14 if pad else 0))];locals_=[(0,0)]
        for level in range(1,levels+1):
            for u,v in boundary:
                u*=level/levels;v*=level/levels;th=theta+u/max(rx*math.sin(math.acos(np.clip((shell(theta,t)[2]-cz)/rz,-1,1))),2.);tt=t+v/(rz*1.75);bulge=(1-(level/levels)**2)*(-.14 if pad else .018);points.append(shell(th,tt)+sn(th,tt)*(offset+bulge));locals_.append((u,v))
        nb=len(boundary);faces=[[0,1+i,1+(i+1)%nb] for i in range(nb)]
        for level in range(levels-1):
            for i in range(nb):a=1+level*nb+i;b=1+level*nb+(i+1)%nb;faces.append([a,b,b+nb,a+nb])
        ob=A.mesh(name,points,faces,mat,thickness=.48 if pad else .10,do_bind=False,radial_center=center);project_uv(ob);finish_normals(ob)
        if not pad:
            path=[points[1+(levels-1)*nb+i]+sn(theta,t)*.025 for i in range(nb)];tube(name+'_Bound_Edge',path,.045,'Webbing',6,True)
        return ob
    patch('Front_Crown_Loop_Panel',0,.30,4.4,3.0)
    for side in [-1,1]:patch('Temple_Loop_Panel_'+str(side),side*1.22,.53,5.5,3.4)
    patch('Rear_Identification_Loop',math.pi,.59,6.0,4.4)
    patch('Crown_Attachment_Loop',math.pi,.22,3.2,3.5)
    for i,t in enumerate([0,.9,-.9,1.9,-1.9,math.pi]):patch('Removable_Comfort_Pad_'+str(i),t,.66,4.5,4.0,'PadMesh',-.70,True)
    patch('Crown_Comfort_Pad',0,.10,4.2,3.0,'PadMesh',-.70,True)
    # Both rails are manufactured plates: real vent slots, undercut running lips,
    # recessed end fasteners; the complete part is formed onto its shell surface.
    for side in [-1,1]:
        length=rx*1.70
        def railpoint(q):
            th=side*(.72+(q[0]/length+.5)*1.72);return shell(th,.89)+sn(th,.89)*(.31+q[1])+np.array([0,0,q[2]])
        rail=box('ARC_Rail_'+str(side),(0,0,0),(length,.46,2.75),'Polymer',.18)
        for i,x in enumerate(np.linspace(-length*.35,length*.35,8)):
            tool=box('SlotTool',(x,0,0),(length*.060,2,.68),'Polymer',.16);carve(rail,tool)
        deform(rail,railpoint,.60)
        for edge in [-1,1]:
            lip=box('Rail_Dovetail_Lip_'+str((side,edge)),(0,.29,edge*.97),(length*.85,.26,.30),'Polymer',.065);deform(lip,railpoint,.6)
        for x in [-length*.43,length*.43]:
            q=railpoint([x,.34,0]);screw('Rail_Recessed_Hex_'+str((side,x)),q,sn(side*(.72+(x/length+.5)*1.72),.89),.30)
        # Four moulded index bars along the slider, subordinate to the real slot.
        for x in np.linspace(-length*.29,length*.29,4):
            bar=box('Rail_Index_'+str((side,x)),(x,.42,1.0),(.08,.05,.19),'Rubber',.015);deform(bar,railpoint,.7)
    # Front three-point mounting shroud: formed backplate, open receiver, catch.
    z0=top-6.8
    def frontpoint(q):
        x,z=q[0],z0+q[2];a=(x/rx)**2+((z-cz)/rz)**2;y=cy+ry*math.sqrt(max(.05,1-a));return np.array([cx+x,y+.19+q[1],z])
    plate=extrude('Three_Point_Shroud_Backplate',[(-3.7,-2.35),(3.7,-2.35),(4.05,-1.10),(1.65,3.05),(-1.65,3.05),(-4.05,-1.1)],.35,'Polymer',.20)
    opening=box('ReceiverTool',(0,0,.05),(3.1,2.5,3.6),'Polymer',.18);carve(plate,opening);deform(plate,frontpoint,.45)
    for x in [-1.85,1.85]:
        q=box('Receiver_Metal_Guide_'+str(x),(x,.35,0),(.42,.75,4.08),'Metal',.08);deform(q,frontpoint,.45)
    for z in [-1.93,1.96]:
        q=box('Receiver_Crosspiece_'+str(z),(0,.40,z),(3.8,.76,.36),'Metal',.07);deform(q,frontpoint,.45)
    q=box('Receiver_Recess_Back',(0,-.05,0),(2.95,.12,3.52),'Rubber',.12);deform(q,frontpoint,.45)
    q=box('Receiver_Lock_Catch',(0,.45,-1.42),(1.65,.5,.45),'Metal',.09);deform(q,frontpoint,.40)
    for x,z in [(-3.05,-1.25),(3.05,-1.25),(0,2.37)]:screw('Shroud_Hex_'+str((x,z)),frontpoint([x,.31,z]),unit((frontpoint([x,0,z])-center)/np.array([rx*rx,ry*ry,rz*rz])),.27)
    # Native head surface guides for suspension straps. All thickness goes outward.
    def headpoint(theta,z,gap=.34):
        direction=np.array([math.sin(theta),math.cos(theta),0]);start=np.array([cx,cy,z])+direction*35;hit=headtree.ray_cast(Vector(start),Vector(-direction),70)
        if hit[0] is None:return np.array([cx,cy,z])+direction*(rx*.68+gap)
        return np.array(hit[0])+direction*gap
    def ribbon(name,path,width,mat='Webbing',thick=.13):
        path=np.asarray(path);points=[];acrosses=[];norms=[];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
        for i,p in enumerate(path):
            tangent=unit(path[min(i+1,len(path)-1)]-path[max(0,i-1)]);normal=unit([p[0]-cx,p[1]-cy,0]);across=unit(np.cross(tangent,normal));acrosses.append(across);norms.append(normal)
            for k in range(5):points.append(p+across*((k/4-.5)*width)+normal*.025*math.cos(math.pi*(k/4-.5)))
        faces=[[i*5+k,i*5+k+1,(i+1)*5+k+1,(i+1)*5+k] for i in range(len(path)-1) for k in range(4)];ob=A.mesh(name,points,faces,mat,do_bind=False,radial_center=center)
        # A consistent warp/weft direction follows the actual strap, including turns.
        uv=ob.data.uv_layers.active
        for face in ob.data.polygons:
            for li in face.loop_indices:
                vi=ob.data.loops[li].vertex_index;j,k=divmod(vi,5);uv.data[li].uv=(k/4*width/4,arc[j]/4)
        # Extrude after authoring the strip UV so the underside inherits the
        # complete weave instead of collapsing to the last front vertex.
        mod=ob.modifiers.new('ActualWebbingThickness','SOLIDIFY');mod.thickness=thick*.01;mod.offset=-1;mod.use_even_offset=False;A.apply(ob,mod.name)
        me=ob.data;me.update();me.calc_loop_triangles();uv=me.uv_layers.active;rim_faces=set()
        for tri in me.loop_triangles:
            a,b,c=[uv.data[i].uv for i in tri.loops]
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-10:rim_faces.add(tri.polygon_index)
        for pi in rim_faces:
            face=me.polygons[pi];axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
            for li in face.loop_indices:
                p=A.nativept(me.vertices[me.loops[li].vertex_index].co);uv.data[li].uv=(p[axes[0]]/4,p[axes[1]]/4)
        finish_normals(ob)
        for edge in [-1,1]:tube(name+'_Selvedge_'+str(edge),[p+a*width*.44*edge+n*.04 for p,a,n in zip(path,acrosses,norms)],.024,'Webbing',4)
        return ob
    junction_z=top-20.5
    for side in [-1,1]:
        junction=headpoint(side*.88,junction_z,.40)
        for label,theta in [('Front',side*.72),('Rear',side*2.30)]:
            anchor=shell(theta,1)-sn(theta,1)*.25;path=[]
            for t in np.linspace(0,1,34):
                th=theta*(1-t)+side*.88*t;z=anchor[2]*(1-t)+junction_z*t;onhead=headpoint(th,z,.42);p=onhead*(min(1,t*6))+anchor*(1-min(1,t*6));path.append(p)
            ribbon('Suspension_'+label+'_'+str(side),path,1.45)
            # Rail-sized attachment tab, with a real fixing screw.
            screw('Suspension_Anchor_'+str((side,label)),anchor+sn(theta,1)*.50,sn(theta,1),.22)
        normal=unit([junction[0]-cx,junction[1]-cy,0]);h=unit(np.cross([0,0,1],normal));basis=np.column_stack([h,normal,[0,0,1]])
        buckle=box('Chin_Adjuster_'+str(side),junction+normal*.17,(2.05,.56,2.1),'Polymer',.16,basis)
        for zoff in [-.51,.51]:
            cut=box('AdjusterSlot',junction+normal*.17+np.array([0,0,zoff]),(1.40,1.5,.36),'Polymer',.11,basis);carve(buckle,cut)
        finish_normals(buckle);project_uv(buckle)
        zchin=top-23.6;path=[headpoint(side*.88*(1-t),junction_z*(1-t)+zchin*t,.36) for t in np.linspace(0,1,27)];ribbon('Chin_Closure_'+str(side),path,1.65)
        if side==1:
            p=headpoint(.60,top-21.6,.64);normal=unit([p[0]-cx,p[1]-cy,0]);basis=np.column_stack([unit(np.cross([0,0,1],normal)),normal,[0,0,1]])
            box('Side_Release_Buckle_Body',p,(2.1,.70,2.9),'Polymer',.22,basis)
            for e in [-1,1]:box('Side_Release_Press_Tab_'+str(e),p+basis[:,0]*e*.94,(.35,.36,1.3),'Rubber',.10,basis)
    chinpath=[headpoint(t,top-23.5+.6*(abs(t)/.56)**2,.46) for t in np.linspace(-.56,.56,32)];ribbon('Contoured_Chin_Cup',chinpath,2.45,'PadMesh',.28)
    # Rear cradle and physically knurled adjustment dial, visible in rear view.
    rear=[headpoint(t,top-17.7,.45) for t in np.linspace(2.08,4.20,52)];ribbon('Occipital_Cradle',rear,2.5,'Rubber',.32)
    dc=headpoint(math.pi,top-17.1,.95);axis=np.array([0,-1,0]);up=np.array([0,0,1]);right=np.array([1,0,0]);segments=72 if high else 48;points=[]
    for rad,depth in [(1.34,-.30),(1.50,-.05),(1.50,.38),(1.35,.53)]:
        for k in range(segments):a=math.tau*k/segments;r=rad+(.045 if k%2==0 else -.045);points.append(dc+axis*depth+(right*math.cos(a)+up*math.sin(a))*r)
    faces=[[i*segments+k,i*segments+(k+1)%segments,(i+1)*segments+(k+1)%segments,(i+1)*segments+k] for i in range(3) for k in range(segments)];faces.extend([list(reversed(range(segments))),list(range(3*segments,4*segments))]);mesh('Knurled_Rear_Fit_Dial',points,faces,'Polymer');screw('Dial_Recessed_Spindle',dc+axis*.52,axis,.24)
    for a in np.linspace(0,math.tau,6,endpoint=False):
        p=dc+axis*.55+(right*math.cos(a)+up*math.sin(a))*.98;tube('Dial_Grip_Rib_'+str(a),[p-(right*math.cos(a)+up*math.sin(a))*.18,p+(right*math.cos(a)+up*math.sin(a))*.10],.045,'Rubber',6)
    # Native head is available as a hidden author reference, excluded from export.
    ref=bpy.data.meshes.new('NativeHeadReference');ref.from_pydata([xyz(p) for p in hp],[],head['triangles']);ref.update();obj=bpy.data.objects.new('REFERENCE_ONLY_'+rig,ref);bpy.context.collection.objects.link(obj);obj.hide_render=True;obj.hide_set(True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene['Revision']='HelmetDetailR1';bpy.context.scene['NativeBody']=rig;bpy.context.scene['Reference']=str(S/'Design/TacticalSystem01_Concept.png');bpy.context.scene['Purpose']='Authoring HIGH' if high else 'GAME export';bpy.context.scene['GameplayTested']=False
    stage='HIGH' if high else 'GAME';bpy.ops.object.select_all(action='DESELECT')
    for o in A.OBJECTS:o.select_set(True)
    bpy.context.view_layer.objects.active=A.OBJECTS[0];bpy.ops.file.pack_all();blend=R/'Models'/f'TS01_Helmet_{rig}_{stage}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    counts=[]
    for ob in A.OBJECTS:ob.data.calc_loop_triangles();counts.append(dict(name=ob.name,vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles)))
    info=dict(rig=rig,stage=stage,blend=str(blend),parts=counts,triangles=sum(r['triangles'] for r in counts),native_head=head['sha256'],head_frame=headbone,dimensions=dict(rx=rx,ry=ry,top=top,center=[cx,cy,cz]),runtime_tested=False)
    if not high:
        bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/f'TS01_Helmet_{rig}.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
        bpy.ops.export_scene.gltf(filepath=str(R/'Exports'/f'TS01_Helmet_{rig}.glb'),export_format='GLB',use_selection=True,export_animations=False)
        data=payload(A.OBJECTS);write(R/'Authored'/f'helmet_{rig}_world.json',data);local=copy.deepcopy(data);axes=np.asarray(headbone['axes']);inv=np.linalg.inv(axes);local['positions']=((np.asarray(data['positions'])-headbone['position'])@inv).tolist();nn=np.asarray(data['normals'])@axes.T;nn/=np.linalg.norm(nn,axis=2,keepdims=True);local['normals']=nn.tolist();local['attachment_frame']=headbone;write(R/'Authored'/f'helmet_{rig}_wear.json',local)
    write(R/f'authored-{rig}-{stage}.json',info);print('HELMET_DETAIL_AUTHORED',rig,stage,info['triangles'],len(counts),flush=True)

def payload(objects):
    slots=list(FAMILIES);positions=[];faces=[];uvs=[];normals=[];materials=[]
    for ob in objects:
        me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active;offset=len(positions);positions.extend([list(A.nativept(ob.matrix_world@v.co)) for v in me.vertices]);slot=slots.index(me.materials[0].name.removeprefix('H1_').split('.')[0])
        for t in me.loop_triangles:
            faces.append([offset+i for i in t.vertices]);materials.append(slot);uvs.append([[float(uv.data[i].uv.x),1-float(uv.data[i].uv.y)] for i in t.loops]);normals.append([[float(me.corner_normals[i].vector.x),-float(me.corner_normals[i].vector.y),float(me.corner_normals[i].vector.z)] for i in t.loops])
    return dict(positions=positions,triangles=faces,uv=uvs,normals=normals,triangle_materials=materials,material_slots=['H1_'+s for s in slots])

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:];mode=args[0]
    if mode=='textures':textures()
    else:build(mode,len(args)>1 and args[1]=='HIGH')
