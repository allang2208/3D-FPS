"""Continuous upper/welt/outsole construction with matched native articulation."""
import copy,gc,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import geometry as g
old=read(OLD/'Jason_LeatherBoots.json');g.bone_ids={b['name']:b['index'] for b in old['bones']}
old_points=np.asarray(old['positions'])
bpy.ops.wm.read_factory_settings(use_empty=True)
bones={b['name']:{k:v for k,v in b.items() if k!='name'} for b in old['bones']};names={b['index']:b['name'] for b in old['bones']}
d=dict(profile='Jason',source=old['source'],binding_source=old['source'],skeleton=old['skeleton'],bones=bones,material_slots=SLOTS,contract='LeatherBootsUpgrade20261022: native Jason; connected upper/welt/midsole/outsole; common foot/ball skin field; original shaft envelope above ankle retained')
for k in ('positions','triangles','weights','uv','normals','triangle_materials','colors','parts'):d[k]=[]
objects=[];foundations={}
def smooth(a,b,x):t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def station(p,side):return (p[0]*(1 if side=='l' else -1)-14.798)*math.sin(math.atan2(2.00392146,12.92064786))+(p[1]+2.45465)*math.cos(math.atan2(2.00392146,12.92064786))
def finish_colors(points,slot,side):
    p=np.asarray(points);v=np.array([station(q,side) for q in p]);toe=smooth(11,23,v)*(1-smooth(6,13,p[:,2]));ankle=np.exp(-((p[:,2]-13)/4)**2)
    tone=.90-.08*toe+.09*np.sin(p[:,2]*.29+v*.37)+.045*np.sin(p[:,0]*1.37+v*.85+p[:,2]*.63);rough=1.-.045*toe+.025*ankle
    return np.c_[np.repeat(np.clip(tone,0,1)[:,None],3,axis=1),np.clip(rough,0,1)].tolist() if slot in (1,4) else np.ones((len(points),4)).tolist()
def add_original(part,face_start):
    a=part['first_vertex'];b=a+part['vertices'];n=part['triangles'];base=len(d['positions']);first=len(d['triangles']);points=old['positions'][a:b];side=part['name'].split('_')[1] if part['name'].startswith('LeatherShaft') else ('l' if '_l' in part['name'] else 'r')
    d['positions'].extend(points);d['weights'].extend([{names[i]:w for i,w in ws} for ws in old['weights'][a:b]]);d['colors'].extend(finish_colors(points,part['material'],side))
    fs=[[v-a+base for v in f] for f in old['triangles'][face_start:face_start+n]];d['triangles'].extend(fs);d['uv'].extend(copy.deepcopy(old['uv'][face_start:face_start+n]));d['normals'].extend(copy.deepcopy(old['normals'][face_start:face_start+n]));slots=list(old['triangle_materials'][face_start:face_start+n])
    if part['name'].startswith('LeatherShaftWithInnerWall'):
        for i,tri in enumerate(old['triangles'][face_start:face_start+n]):
            q=np.mean(old_points[tri],axis=0);cx,cy,_,_=g.profile(q[2]);rad=np.array([q[0]-(cx if side=='l' else -cx),q[1]-cy,0]);normal=np.mean(d['normals'][first+i],axis=0)
            if rad@normal<-.4:slots[i]=6
    d['triangle_materials'].extend(slots);d['parts'].append(dict(name=part['name'],first_vertex=base,vertices=b-a,first_triangle=first,triangles=n,material=part['material'],original=True))
def append_mesh(name,points,faces,side,mode,slots,uv_mode='metric',thickness=0,bevel=0,uv_coords=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in points],[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob
    for s in SLOTS:mesh.materials.append(bpy.data.materials.get(s) or bpy.data.materials.new(s))
    for i,poly in enumerate(mesh.polygons):poly.material_index=int(slots[i] if not np.isscalar(slots) else slots)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if thickness:
        mod=ob.modifiers.new('Leather edge thickness','SOLIDIFY');mod.thickness=thickness*.01;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)
    if bevel:
        mod=ob.modifiers.new('Rounded contact edges','BEVEL');mod.width=bevel*.01;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.55;bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for poly in mesh.polygons:poly.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(48));mesh.calc_loop_triangles();points=np.array([[v.co.x*100,-v.co.y*100,v.co.z*100] for v in mesh.vertices]);base=len(d['positions']);first=len(d['triangles']);d['positions'].extend(points.tolist());d['weights'].extend([{names[i]:float(w) for i,w in g.skin(side,p,mode).items() if w>1e-8} for p in points]);d['colors'].extend(finish_colors(points,1 if name.startswith(('BootFoundation','Toe')) else int(slots) if np.isscalar(slots) else 1,side))
    for tri in mesh.loop_triangles:
        ids=list(tri.vertices);p=points[ids];slot=mesh.polygons[tri.polygon_index].material_index;axis=int(np.argmax(np.abs(mesh.polygons[tri.polygon_index].normal)));plane=[i for i in range(3) if i!=axis];span=10. if slot==2 else 25.
        uv=p[:,plane]/span
        if slot==5:uv=np.c_[[station(q,side) for q in p],p[:,2]]/25.
        elif uv_coords is not None:
            raw=np.asarray([uv_coords[i] for i in ids]);uv=raw[:,:2].copy()
            if np.ptp(raw[:,0]/raw[:,2])>.5:uv[raw[:,0]/raw[:,2]<.5,0]+=raw[raw[:,0]/raw[:,2]<.5,2]
        uv=g.valid_uv(uv,p)
        d['triangles'].append([base+i for i in ids]);d['uv'].append(uv.tolist());d['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops]);d['triangle_materials'].append(slot)
    record=dict(name=name,first_vertex=base,vertices=len(points),first_triangle=first,triangles=len(d['triangles'])-first,material=int(slots) if np.isscalar(slots) else 'mixed');d['parts'].append(record);objects.append(ob);return ob,record

# Horizontal rings make ONE upper from the toe to the open cuff. Neither the
# calf nor the foot has a capped, intersecting end hidden beneath another part.
def curve(x,levels,values):
    j=int(np.clip(np.searchsorted(levels,x)-1,0,len(levels)-2));a,b=levels[j:j+2];t=np.clip((x-a)/(b-a),0,1)
    def slope(i):
        lo=max(0,i-1);hi=min(len(levels)-1,i+1);return (values[hi]-values[lo])/(levels[hi]-levels[lo])
    return (2*t**3-3*t*t+1)*values[j]+(t**3-2*t*t+t)*(b-a)*slope(j)+(-2*t**3+3*t*t)*values[j+1]+(t**3-t*t)*(b-a)*slope(j+1)
Z=[-.5,0,1,2,3,4,5,6,7,8,10,12,16,20,40]
def panel_theta(z):return curve(z,[0,3,5,7,9,12,20,33,36,38.5],[2.15,2.0,1.72,1.15,.92,1.02,1.05,1.05,.92,.62])
def raw_surface(side,theta,z):
    front=curve(z,Z,[23,23,22.7,22.1,20.6,18.3,15.6,11.8,9.0,7.1,5.7,5.25,5.3,5.5,6.85]);back=curve(z,Z,[-6.9,-6.9,-6.9,-6.8,-6.7,-6.65,-6.55,-6.4,-6.2,-6.,-5.6,-5.25,-5.3,-5.5,-6.85]);width=curve(z,Z,[5.72,5.72,5.72,5.68,5.60,5.42,5.10,4.90,4.65,4.4,4.14,4.05,4.5,5.2,6.35])
    v=(front+back)*.5+(front-back)*.5*math.cos(theta);u=width*math.sin(theta)*(1+.11*math.cos(theta)*(1-float(smooth(5,12,z))))
    low=g.foot_point(side,u,v,z);high=g.shaft_point(side,theta,z);blend=float(smooth(9,18,z));p=low*(1-blend)+high*blend
    lower_lift=(.95*(1-smooth(-2,10,v))+.15*smooth(17,23,v))*(1-smooth(-.5,4,z));p[2]+=lower_lift
    p[2]+=.32*max(0,math.cos(theta))*float(smooth(34,38,z))
    angular=.12+.88*abs(math.sin(theta))**1.5;fold=0.
    for center,amp,width,tilt,phase in [(12.8,.20,.48,.8,0),(16.5,.28,.67,1.5,-.6),(21.4,.19,.82,2.2,.3),(26.3,.08,.95,1.2,1.1)]:
        center+=tilt*math.sin(theta+phase);fold+=amp*math.exp(-((z-center)/width)**2)
    fold*=angular;s=1 if side=='l' else -1;p+=np.array([s*math.sin(theta),math.cos(theta),0])*fold
    delta=abs(abs((theta+math.pi)%math.tau-math.pi)-panel_theta(z));groove=.045*math.exp(-(delta/.036)**2)*float(smooth(1,3,z));p-=np.array([s*math.sin(theta),math.cos(theta),0])*groove
    return p
def normal(side,theta,z):
    dt=raw_surface(side,theta+.002,z)-raw_surface(side,theta-.002,z);dz=raw_surface(side,theta,z+.002)-raw_surface(side,theta,z-.002);n=g.unit(np.cross(dt,dz));rad=np.array([(1 if side=='l' else -1)*math.sin(theta),math.cos(theta),0]);return n*(1 if n@rad>0 else -1)
def surface(side,theta,z,offset=0):return raw_surface(side,theta,z)+normal(side,theta,z)*offset if offset else raw_surface(side,theta,z)
def tube(name,path,radius,side,slot=3,closed=False,sides=6):
    path=np.asarray(path);points=[];faces=[];count=len(path)
    for i,p in enumerate(path):
        tangent=g.unit(path[(i+1)%count]-path[(i-1)%count]) if closed else g.unit(path[min(i+1,count-1)]-path[max(i-1,0)]);a=g.unit(np.cross(tangent,[0,0,1] if abs(tangent[2])<.9 else [0,1,0]));b=np.cross(tangent,a);points.extend(p+radius*(math.cos(t)*a+math.sin(t)*b) for t in np.arange(sides)*math.tau/sides)
    for i in range(count if closed else count-1):
        for k in range(sides):faces.append([i*sides+k,i*sides+(k+1)%sides,((i+1)%count)*sides+(k+1)%sides,((i+1)%count)*sides+k])
    if not closed:faces.extend([list(reversed(range(sides))),list(range((count-1)*sides,count*sides))])
    return append_mesh(name,points,faces,side,'flex',slot)
def stitch(name,path,side,normals,spacing=.38,radius=.024):
    path=np.asarray(path);normals=np.asarray(normals);length=np.linalg.norm(np.diff(path,axis=0),axis=1);cum=np.r_[0,np.cumsum(length)];points=[];faces=[]
    def at(t):
        j=min(len(path)-2,max(0,np.searchsorted(cum,t,side='right')-1));s=(t-cum[j])/max(length[j],1e-8);return path[j]*(1-s)+path[j+1]*s,g.unit(normals[j]*(1-s)+normals[j+1]*s)
    for distance in np.arange(.08,cum[-1]-.28,spacing):
        a,n=at(distance);b,nb=at(distance+.25);n=g.unit(n+nb);axis=g.unit(b-a);across=g.unit(np.cross(axis,n));up=np.cross(axis,across);start=len(points)
        for j in range(3):
            t=j/2;p=a*(1-t)+b*t+n*(-.01+.035*math.sin(t*math.pi));points.extend(p+radius*(math.cos(q)*across+math.sin(q)*up) for q in np.arange(4)*math.tau/4)
        for j in range(2):
            for k in range(4):faces.append([start+j*4+k,start+j*4+(k+1)%4,start+(j+1)*4+(k+1)%4,start+(j+1)*4+k])
        faces.extend([list(reversed(range(start,start+4))),list(range(start+8,start+12))])
    append_mesh(name,points,faces,side,'flex',3)
def rounded(w,h,r):
    result=[]
    for cx,cy,start in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for a in np.linspace(start,start+90,9,endpoint=False):t=math.radians(a);result.append((cx+r*math.cos(t),cy+r*math.sin(t)))
    return result
for side in ('l','r'):
    N=128;angles=np.arange(N)*math.tau/N;zs=np.unique(np.r_[np.linspace(-.5,38.1,133),38.2]);rows=[];uvrows=[];slots=[]
    for z in zs:rows.append(np.array([surface(side,t,float(z)) for t in angles]))
    distances=np.zeros(N)
    for j,row in enumerate(rows):
        if j:distances+=np.linalg.norm(row-rows[j-1],axis=1)
        # Integer wrap and a rear seam prevent a changing-perimeter UV seam
        # from appearing as a hard strip across the front shin and instep.
        perimeter=2.;uvrows.append([[((i/N+.5)%1)*perimeter,distances[i]/25,perimeter] for i in range(N)])
    outer_rows=len(rows)
    for lift,offset in [(.12,-.055),(.18,-.17),(.10,-.30),(-.04,-.36)]:rows.append(np.array([surface(side,t,38.2,offset)+[0,0,lift] for t in angles]));uvrows.append(uvrows[-1])
    rim_end=len(rows)
    for z in np.linspace(37.8,.25,100):rows.append(np.array([surface(side,t,float(z),-.36) for t in angles]));uvrows.append([[i/N*1.65,z/25,1.65] for i in range(N)])
    points=[p for row in rows for p in row];uvs=[p for row in uvrows for p in row];faces=[]
    for j in range(len(rows)-1):
        for i in range(N):
            faces.append([j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i]);theta=angles[i]+math.pi/N
            if j>=rim_end-1:slot=6
            elif j>=outer_rows-1:slot=4
            else:
                slot=1
            slots.append(slot)
    faces.append(list(range((len(rows)-1)*N,len(rows)*N)));slots.append(6)
    last=list(range(N));base=rows[0]
    for layer,(expand,dz) in enumerate([(.18,-.02),(.38,-.10),(.44,-.34),(.43,-.75),(.40,None),(.30,None)]):
        ring=[]
        for i,t in enumerate(angles):
            p=base[i].copy();rad=g.unit(np.array([p[0]-(14.798 if side=='l' else -14.798),p[1]-5.3,0]));p+=rad*expand;v=station(p,side);bottom=min(base[i][2]-.98,-2.55+.22*float(smooth(17,23,v))+1.48*float(smooth(.2,3,v)*(1-smooth(7,11,v))));p[2]=base[i][2]+dz if dz is not None else bottom+(.16 if layer==4 else 0);ring.append(len(points));points.append(p);uvs.append([i/N*2.6,p[2]/25,2.6])
        for i in range(N):faces.append([last[i],ring[i],ring[(i+1)%N],last[(i+1)%N]]);slots.append(5 if layer<5 else 2)
        last=ring
    bottom_outline=np.asarray([points[i] for i in last]);center=g.foot_point(side,0,8,0)
    def bottom_z(p):
        v=station(p,side);return min(-.5+.95*(1-float(smooth(-2,10,v)))+.15*float(smooth(17,23,v))-.98,-2.55+.22*float(smooth(17,23,v))+1.48*float(smooth(.2,3,v)*(1-smooth(7,11,v))))
    for scale in (.85,.65,.45,.25,.1):
        ring=[]
        for i in range(N):
            p=center+(bottom_outline[i]-center)*scale;p[2]=bottom_z(p);ring.append(len(points));points.append(p);uvs.append([i/N*2.6,p[2]/25,2.6])
        for i in range(N):faces.append([last[i],ring[i],ring[(i+1)%N],last[(i+1)%N]]);slots.append(2)
        last=ring
    center[2]=bottom_z(center);ci=len(points);points.append(center);uvs.append([0,center[2]/25,2.6])
    for i in range(N):faces.append([last[i],ci,last[(i+1)%N]]);slots.append(2)
    ob,rec=append_mesh('BootFoundation_'+side,points,faces,side,'flex',slots,uv_coords=uvs);foundations[side]=rec
    assert rec['vertices']==len(points)
    rec['outer_surface_triangles']=(outer_rows-1)*N*2
    # Smooth vertex finish follows the exact curved sewing line instead of
    # changing material on a staircase of grid faces beside the thread.
    for j,z in enumerate(zs):
        for i,t in enumerate(angles):
            idx=rec['first_vertex']+j*N+i;a=abs((t+math.pi)%math.tau-math.pi);panel=float(smooth(panel_theta(z)-.025,panel_theta(z)+.025,a));toe=float(smooth(13.95,14.2,station(rows[j][i],side)))*(1-float(smooth(4.8,5.3,z)));shade=1.-.12*max(panel,toe)
            d['colors'][idx][:3]=[x*shade for x in d['colors'][idx][:3]]
    for idx in range(rec['first_vertex']+(rim_end-1)*N,rec['first_vertex']+len(rows)*N):d['colors'][idx][:3]=[x*.16 for x in d['colors'][idx][:3]]
    for sign in (-1,1):
        for offset in (-.014,.014):
            params=[(sign*(panel_theta(z)+offset),z) for z in np.linspace(2.3,37.7,190)];stitch('CurvedQuarter_'+side+'_'+str(sign)+'_'+str(offset),[surface(side,t,z,.035) for t,z in params],side,[normal(side,t,z) for t,z in params])
    for z in (37.78,38.03):
        ts=np.linspace(0,math.tau,230);stitch('FoldedCuff_'+side+'_'+str(z),[surface(side,t,z,.025) for t in ts],side,[normal(side,t,z) for t in ts])
    for target in (14.15,14.43):
        params=[]
        for theta in np.linspace(-1.12,1.12,121):
            lo=-.5;hi=6.
            for _ in range(16):
                mid=(lo+hi)*.5
                if station(surface(side,theta,mid),side)>target:lo=mid
                else:hi=mid
            if station(surface(side,theta,-.5),side)>=target:params.append((theta,(lo+hi)*.5))
        stitch('AnatomicalToeSeam_'+side+'_'+str(target),[surface(side,t,z,.035) for t,z in params],side,[normal(side,t,z) for t,z in params])
    ts=np.linspace(0,math.tau,260);weltpath=[]
    for t in ts:
        p=surface(side,t,-.5);rad=g.unit([p[0]-(14.798 if side=='l' else -14.798),p[1]-5.3,0]);weltpath.append(p+rad*.20+[0,0,.015])
    stitch('FullWeltStitch_'+side,weltpath,side,[[0,0,1]]*len(weltpath),spacing=.40,radius=.027)
    for index,z in enumerate((12.8,33.3)):
        verts=[];faces=[];height=1.65;ns=160
        for row in range(5):
            zz=z-height/2+height*row/4
            for t in np.arange(ns)*math.tau/ns:verts.append(surface(side,t,zz,.14))
        for j in range(4):
            for i in range(ns):a=j*ns+i;faces.append([a,j*ns+(i+1)%ns,(j+1)*ns+(i+1)%ns,(j+1)*ns+i])
        append_mesh('FittedBelt_'+side+'_'+str(index),verts,faces,side,'flex',4,thickness=.14,bevel=.035)
        for zz in (z-.63,z+.63):stitch('BeltSeam_'+side+'_'+str(zz),[surface(side,t,zz,.175) for t in ts],side,[normal(side,t,zz) for t in ts],spacing=.38,radius=.022)
        theta=1.12;n=normal(side,theta,z);horizontal=g.unit(surface(side,theta+.01,z)-surface(side,theta-.01,z));vertical=g.unit(np.cross(n,horizontal));vertical*=1 if vertical[2]>0 else -1;center=surface(side,theta,z,.28)
        outer=rounded(2.65,2.2,.29);inner=rounded(2.04,1.59,.20);verts=[];faces=[];count=len(outer)
        for depth,contour in [(-.08,outer),(.13,outer),(.13,inner),(-.08,inner)]:verts.extend(center+horizontal*x+vertical*y+n*depth for x,y in contour)
        for row in range(4):
            for i in range(count):faces.append([row*count+i,row*count+(i+1)%count,((row+1)%4)*count+(i+1)%count,((row+1)%4)*count+i])
        append_mesh('AgedBuckleFrame_'+side+'_'+str(index),verts,faces,side,'flex',0,bevel=.045);tube('BucklePin_'+side+'_'+str(index),[center+horizontal*x+n*.10 for x in np.linspace(-1.12,1.02,13)],.075,side,0,sides=8)
        for hole in range(3):
            th=theta-.37-hole*.11;cp=surface(side,th,z,.153);nn=normal(side,th,z);hh=g.unit(surface(side,th+.01,z)-surface(side,th-.01,z));vv=g.unit(np.cross(nn,hh));path=[cp+.10*(math.cos(a)*hh+math.sin(a)*vv) for a in np.linspace(0,math.tau,24,endpoint=False)];tube('HoleRim_'+side+'_'+str(index)+'_'+str(hole),path,.017,side,4,True,sides=5);pp=[cp-nn*.012]+[p-nn*.012 for p in path];ff=[[0,1+i,1+(i+1)%len(path)] for i in range(len(path))];append_mesh('StrapWell_'+side+'_'+str(index)+'_'+str(hole),pp,ff,side,'flex',6)
d['contract']='TailoredV2: continuous shared upper/welt/shaft/cuff/lining; native Jason foot-ball-calf skin; curved quarters and soft folds'
path=R/'Authored/ue_leather_boots/Jason.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(__import__('json').dumps(d,separators=(',',':')),encoding='utf-8')
write(R/'authored.json',dict(completed=True,file=str(path),vertices=len(d['positions']),triangles=len(d['triangles']),parts=len(d['parts']),foundations=foundations,continuous_shaft_upper=True,native_skeleton_preserved=True,runtime_tested=False))
print('TAILORED_CONTINUOUS_BOOT_AUTHORED',len(d['positions']),len(d['triangles']),flush=True)
