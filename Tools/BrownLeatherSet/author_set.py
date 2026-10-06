"""Author the accepted brown leather boots and trousers as editable native gear."""
import copy,json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BrownLeatherSet20261004'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
native=json.loads((R/'native_reference.json').read_text());bones=native['bones'];g.bone_ids={b['name']:b['index'] for b in bones}
cloth_source=json.loads((P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2/Jason_ChainmailPants.json').read_text())
cloth_parts=[];triangle_start=0
for part in cloth_source['parts']:
    if part['name'].startswith(('Mail','Lining','HemBinding')):cloth_parts.append((part,triangle_start))
    triangle_start+=part['triangles']
cloth_ids=[i for part,_ in cloth_parts for i in range(part['first_vertex'],part['first_vertex']+part['vertices'])]
tree=KDTree(len(cloth_ids))
for vi in cloth_ids:tree.insert(Vector(cloth_source['positions'][vi]),vi)
tree.balance()
surface_faces=[list(reversed(t)) for part,start in cloth_parts if part['name'].startswith('Mail') for t in cloth_source['triangles'][start:start+part['triangles']]]
surface=BVHTree.FromPolygons([Vector(p) for p in cloth_source['positions']],surface_faces,all_triangles=True)
original_skin=g.skin
def weights(side,p,mode):
    if mode!='pants':return original_skin(side,p,mode)
    nearest=tree.find_n(Vector(p),3);total={};den=0.
    for _,vi,d in nearest:
        w=1/max(d,.08)**2;den+=w
        for bi,bw in cloth_source['weights'][vi]:total[bi]=total.get(bi,0)+w*bw
    chosen=sorted(total.items(),key=lambda x:-x[1])[:8];scale=sum(w for _,w in chosen)
    return {bi:w/scale for bi,w in chosen if w/scale>1e-7}
g.skin=weights

def project(point,offset=.06):
    p,n,_,_=surface.find_nearest(Vector(point));return np.array(p)+np.array(n)*offset

def patch(name,side,fn,nu,nv,mode,slot=1,thickness=.09,bevel=.035):
    vertices=[fn(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)];faces=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;faces.append([a,a+1,a+nu+2,a+nu+1])
    return g.mesh_object(name,vertices,faces,side,mode,slot,thickness,bevel)

def closed_curve(points,steps=5):
    points=np.array(points,float);out=[]
    for i,b in enumerate(points):
        a=points[(i-1)%len(points)];c=points[(i+1)%len(points)];d=points[(i+2)%len(points)]
        for t in np.linspace(0,1,steps,endpoint=False):
            out.append((2*t**3-3*t*t+1)*b+(t**3-2*t*t+t)*(c-a)*.37+(-2*t**3+3*t*t)*c+(t**3-t*t)*(d-b)*.37)
    return np.array(out)

def stitched(name,path,side,mode,normal,closed=False,spacing=.48,radius=.024):
    line=np.array(path,float)
    if closed and np.linalg.norm(line[0]-line[-1])>.00001:line=np.r_[line,line[:1]]
    lengths=np.linalg.norm(np.diff(line,axis=0),axis=1);cumulative=np.r_[0,np.cumsum(lengths)];total=cumulative[-1]
    def at(t):
        i=min(len(line)-2,max(0,np.searchsorted(cumulative,t,side='right')-1));f=(t-cumulative[i])/max(lengths[i],1e-9)
        return line[i]*(1-f)+line[i+1]*f
    vertices=[];faces=[]
    for d in np.arange(.08,total-.30,spacing):
        p0=at(d);p1=at(d+.29);n=g.unit(normal((p0+p1)*.5));axis=g.unit(p1-p0);a=g.unit(np.cross(axis,n));b=np.cross(axis,a)
        start=len(vertices)
        for i,p in enumerate([p0,(p0+p1)*.5+n*.035,p1]):
            vertices.extend(p+radius*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,math.tau,4,endpoint=False))
        for j in range(2):
            for i in range(4):faces.append([start+j*4+i,start+j*4+(i+1)%4,start+(j+1)*4+(i+1)%4,start+(j+1)*4+i])
        faces.extend([[start+3,start+2,start+1,start],[start+8,start+9,start+10,start+11]])
    if vertices:return g.mesh_object(name,vertices,faces,side,mode,3)

def buckle(name,side,center,horizontal,vertical,mode,width=3.0,height=2.25):
    center=np.array(center);h=g.unit(horizontal);v=g.unit(vertical);normal=g.unit(np.cross(h,v))
    contour=[];rounding=.25
    for cx,cy,start in [(width/2-rounding,height/2-rounding,0),(-width/2+rounding,height/2-rounding,90),(-width/2+rounding,-height/2+rounding,180),(width/2-rounding,-height/2+rounding,270)]:
        for a in np.linspace(start,start+90,6,endpoint=False):
            t=math.radians(a);contour.append(center+h*(cx+rounding*math.cos(t))+v*(cy+rounding*math.sin(t)))
    g.tube(name,contour,.12,side,mode,0,True)
    g.tube(name+'_Bar',[center+v*x for x in np.linspace(-height/2+.1,height/2-.1,8)],.08,side,mode,0)
    g.tube(name+'_Tongue',[center+h*x+normal*.11 for x in np.linspace(-.2,width/2,8)],.065,side,mode,0)

def boots():
    for side in ['l','r']:
        first=len(g.objects);g.leather(side)
        # The existing fitted foot last is shared, while the exposed brown boot
        # adds actual cap/quarter panels, decorative construction seams and straps.
        for ob in g.objects[first:]:
            if ob.name.startswith('LayeredLeatherSole'):
                # A shallow arch and separate low heel silhouette, keeping the
                # existing sole's lowest native point rather than lowering feet.
                sign=1 if side=='l' else -1
                for v in ob.data.vertices:
                    x,y,z=v.co.x*100,-v.co.y*100,v.co.z*100
                    station=(sign*x-14.798)*.1533+(y+2.45465)*.9882
                    lift=.95*g.smooth(.5,4.0,station)*(1-g.smooth(7.5,11.0,station))
                    v.co.z+=lift*max(0,min(1,(-z-.6)/1.8))*.01
                ob.data.update()
        def toe(u,v):return g.dorsal(side,14.5+v*9.45,(u*2-1)*2.02,.095)
        patch('LeatherToeCap_'+side,side,toe,36,13,'foot',4,.085,.035)
        for station in [14.65,14.93]:
            path=[g.dorsal(side,station,t,.20) for t in np.linspace(-1.97,1.97,80)]
            stitched('ToeDoubleStitch_%s_%s'%(side,station),path,side,'foot',lambda p:[0,0,1])
        # Rear counter and curved side quarters are supple leather patches.
        patch('ReinforcedHeel_'+side,side,lambda u,v:g.shaft_point(side,math.pi+(u*2-1)*1.40,1.25+9.1*v,.12),42,12,'foot',4,.09,.04)
        for edge in [-1,1]:
            theta=edge*1.5
            path=[g.shaft_point(side,theta+.05*math.sin(z*.18),z,.14) for z in np.linspace(11,37.9,70)]
            for offset in [-.08,.08]:
                displaced=[p+np.array([0,offset,0]) for p in path]
                stitched('ShaftPanelSeam_%s_%s_%s'%(side,edge,offset),displaced,side,'flex',lambda p:[1 if side=='l' else -1,0,0])
        # Soft rolled opening, stitched twice like the accepted glove wrist.
        for z in [37.86,38.14]:
            path=[g.shaft_point(side,t,z+.48*max(0,math.cos(t)),.08) for t in np.linspace(0,math.tau,120)]
            stitched('CollarSeam_%s_%s'%(side,z),path,side,'calf',lambda p:[p[0]-(12.7 if side=='l' else -12.7),p[1]+2.35,0],True)
        for index,z in enumerate([13.0,33.8]):
            slot=4;mode='flex' if index==0 else 'calf'
            patch('LeatherWrapStrap_%s_%s'%(side,index),side,lambda u,v:g.shaft_point(side,-1.63+u*math.tau,z+(v-.5)*1.90,.22),94,4,mode,slot,.13,.045)
            for dz in [-.72,.72]:
                path=[g.shaft_point(side,t,z+dz,.28) for t in np.linspace(-1.63,math.tau-1.63,120)]
                stitched('WrapStrapSeam_%s_%s_%s'%(side,index,dz),path,side,mode,lambda p:[p[0]-(g.profile(p[2])[0] if side=='l' else -g.profile(p[2])[0]),p[1]-g.profile(p[2])[1],0],True)
            center=g.shaft_point(side,1.53,z,.49);sign=1 if side=='l' else -1
            buckle('SideBuckle_%s_%s'%(side,index),side,center,[0,1,0],[0,0,1],mode,3.0,2.2)
            patch('StrapTail_%s_%s'%(side,index),side,lambda u,v:g.shaft_point(side,1.53+(-4.0+4.7*u)/6.5,z+(v-.5)*1.5,.39),20,3,mode,4,.12,.04)
            for t in [1.07,1.22]:
                # Dark inset holes made as very small solid dark discs.
                point=g.shaft_point(side,t,z,.55);before=len(g.objects)
                g.rivet('StrapHole_%s_%s_%s'%(side,index,t),point,[sign,0,0],side,mode,.105)
                for ob in g.objects[before:]:ob['material_slot']=2
    for ob in g.objects:ob['item']='boots'

def torso(z,t,offset=0):
    rx=np.interp(z,[80,85,90,95,100.2],[18.3,18.7,18.3,17.7,17.1])+offset
    ry=np.interp(z,[80,85,90,95,100.2],[13.8,14.4,14.2,13.7,12.7])+offset
    return np.array([rx*math.sin(t),.8+ry*math.cos(t),z])
def leg(z,t,side):
    sign=1 if side=='l' else -1;hs=[11.8,20,30,40,47.35,58,67,72]
    cx=np.interp(z,hs,[14.8,14.2,13.5,12.6,12.04,11.2,10.5,9.8]);cy=np.interp(z,hs,[-2.5,-2.,-1.2,-.4,.8,1.7,2.3,2.6])
    rx=np.interp(z,hs,[5.65,6.1,6.8,6.7,6.55,7.55,8.6,9.1]);ry=np.interp(z,hs,[6.5,7.2,8.,8.3,8.55,9.4,10.4,10.6])
    return np.array([sign*(cx+rx*math.sin(t)),cy+ry*math.cos(t),z])

def curved_patch(name,side,outline,fn):
    outline=closed_curve(outline,6);center=np.mean(outline,axis=0);n=len(outline);vertices=[fn(*center)];faces=[]
    for r in [.18,.38,.59,.78,.92,1.]:vertices.extend(fn(*(center+(p-center)*r)) for p in outline)
    for i in range(n):faces.append([0,1+i,1+(i+1)%n])
    for j in range(5):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n;faces.append([a,b,b+n,a+n])
    g.mesh_object(name,vertices,faces,side,'pants',4,.095,.035)
    for scale in [.945,.98]:
        path=[fn(*(center+(p-center)*scale))+[0,.04,0] for p in outline]
        stitched(name+'_Seam_'+str(scale),path,side,'pants',lambda p:[0,1,0],True)

def pants():
    start=len(g.objects)
    for part,first_triangle in cloth_parts:
        first=part['first_vertex'];count=part['vertices'];points=np.array(cloth_source['positions'][first:first+count])
        faces=[[i-first for i in reversed(t)] for t in cloth_source['triangles'][first_triangle:first_triangle+part['triangles']]]
        name=part['name'].replace('Mail','Leather');slot=1 if part['material']==0 else 4
        g.mesh_object(name,points,faces,'l','pants',slot)
    # A flexible waist band with separate belt, slots and small steel buckle.
    patch('LeatherWaistband','l',lambda u,v:torso(96.1+4.0*v,u*math.tau,.08),112,6,'pants',4,.13,.045)
    patch('LeatherBelt','l',lambda u,v:torso(97.1+2.30*v,.04+u*(math.tau-.08),.29),120,4,'pants',4,.16,.05)
    for z in [96.34,99.90]:stitched('WaistSeam_'+str(z),[torso(z,t,.22) for t in np.linspace(0,math.tau,200)],'l','pants',lambda p:[p[0],p[1]-.8,0],True)
    for i,t in enumerate([.30,1.12,2.1,3.14,4.2,5.16,5.98]):
        patch('BeltLoop_'+str(i),'l',lambda u,v,t=t:torso(96.1+4.2*v,t+(u-.5)*.087,.55),4,8,'pants',1,.18,.045)
    buckle('WaistBuckle','l',torso(98.15,0,.64),[1,0,0],[0,0,1],'pants',4.3,3.15)
    # Flat leather fly, inset pockets and curved thigh panels; steel is confined
    # to the functional closure rather than applied to the knees.
    patch('LeatherFly','l',lambda u,v:project(torso(83.2+13*v,.012+u*.085),.14),5,20,'pants',4,.10,.04)
    stitched('FlySeam',[project(torso(z,.13),.18) for z in np.linspace(83.6,96.0,60)],'l','pants',lambda p:[0,1,0])
    for side,sign in [('l',1),('r',-1)]:
        for shift in [-.006,.006]:
            path=[project(torso(95.6-11.6*t,sign*(.44+.50*t+shift)),.16) for t in np.linspace(0,1,60)]
            stitched('InsetPocket_%s_%s'%(side,shift),path,side,'pants',lambda p:[sign*.35,1,0])
        for edge in [0,1]:
            path=[]
            for z in np.linspace(82,53,95):
                t=(82-z)/29;angle=.97-.39*t if edge==0 else 1.78-.14*t
                if z>=80:p=torso(z,sign*angle)
                elif z>66:p=torso(80,sign*angle)*(z-66)/14+leg(66,angle,side)*(80-z)/14
                else:p=leg(z,angle,side)
                path.append(project(p,.14))
            stitched('ThighPanelSeam_%s_%s'%(side,edge),path,side,'pants',lambda p:[sign*.45,1,0])
        outline=[[-.39,55.1],[.30,55.1],[.49,51.4],[.39,46.2],[.29,40.2],[-.23,39.8],[-.40,44.8],[-.50,51.1]]
        curved_patch('SoftKneePatch_'+side,side,outline,lambda t,z,side=side:project(leg(z,t,side),.17))
        for angle in [1.58,4.7]:
            path=[project(leg(z,angle,side),.12) for z in np.linspace(12.4,64,120)]
            stitched('LegSideSeam_%s_%s'%(side,angle),path,side,'pants',lambda p:[sign,0,0])
        for z in [12.25,13.35]:
            path=[project(leg(z,t,side),.14) for t in np.linspace(0,math.tau,100)]
            stitched('CuffStitch_%s_%s'%(side,z),path,side,'pants',lambda p:[p[0]-sign*14.8,p[1]+2.5,0],True)
    for ob in g.objects[start:]:ob['item']='pants'

boots();pants()

def export(kind):
    d={k:[] for k in ['positions','triangles','weights','uv','normals','triangle_materials','parts']}
    for ob in [x for x in g.objects if x['item']==kind]:
        mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active;start=len(d['positions'])
        points=np.array([[v.co.x*100,-v.co.y*100,v.co.z*100] for v in mesh.vertices]);d['positions'].extend(points.tolist())
        for p in points:d['weights'].append([[bi,float(w)] for bi,w in weights(ob['side'],p,ob['weight_zone']).items() if w>1e-7])
        count=0
        for tri in mesh.loop_triangles:
            p=points[list(tri.vertices)]
            if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-9:continue
            d['triangles'].append([start+i for i in tri.vertices]);mapped=np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops]);d['uv'].append(g.valid_uv(mapped,p).tolist())
            d['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops]);d['triangle_materials'].append(int(ob['material_slot']));count+=1
        d['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(points),triangles=count,material=int(ob['material_slot'])))
    d.update(source=native['source'],skeleton=native['skeleton'],bones=bones,contract='BrownLeatherSet20261004 '+kind+': Jason native rig, UE centimetres, per-corner UV and normals')
    (R/('Jason_Leather'+kind.title()+'.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
    return dict(vertices=len(d['positions']),triangles=len(d['triangles']),parts=len(d['parts']))

receipt={kind:export(kind) for kind in ['boots','pants']}
(R/'production.json').write_text(json.dumps(dict(models=receipt,matching_gloves='ue_field_gloves',rear_geometry='authored from garment construction; no rear concept supplied',runtime_tested=False),indent=2))
# Keep a construction master immediately; the following finishing step adds
# packed materials, native rig and the two shoe-fit variants to the full file.
bpy.ops.wm.save_as_mainfile(filepath=str(R/'LeatherSet_Construction.blend'))
print('BROWN_LEATHER_SET_AUTHORED',receipt,flush=True)
