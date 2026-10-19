"""V2 slim suit trousers: welded seat/crotch, eased legs, native Jason binding."""
import sys,math,copy,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
g=module('mage_pants_geometry','Tools/ST6LowerSet/geometry.py');bpy.ops.wm.read_factory_settings(use_empty=True)
native=read(P/'SourceAssets/BrownLeatherSet20261004/native_reference.json');bones=native['bones']
donor=read(P/'SourceAssets/BootsEquipment20261004/jeans.json');dp=np.array(donor['positions']);df=np.array(donor['triangles']);ids={b['name']:b['index'] for b in bones};remap={b['index']:ids[b['name']] for b in donor['bones']}
trees={}
for side,sign in [('l',1),('r',-1),('both',0)]:
    fs=df if sign==0 else df[np.mean(dp[df,0],1)*sign>=-.15];trees[side]=(BVHTree.FromPolygons(dp.tolist(),fs.tolist(),all_triangles=True),fs)
def donor_weights(point,side):
    tree,faces=trees[side];hit,_,fi,_=tree.find_nearest(Vector(point));face=faces[fi];a,b,c=dp[face];v0=b-a;v1=c-a;v2=np.array(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
    if abs(den)<1e-12:coeff=np.array([1.,0,0])
    else:
        x=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;y=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den;coeff=np.maximum([1-x-y,x,y],0);coeff/=coeff.sum()
    out={}
    for vi,f in zip(face,coeff):
        for bi,w in donor['weights'][vi]:out[remap[bi]]=out.get(remap[bi],0)+float(w*f)
    return out
def binding(p,side):
    if p[2]>80:out=donor_weights(p,'both')
    elif p[2]>=66 and abs(p[0])<6:
        a,b=donor_weights(p,'l'),donor_weights(p,'r');t=np.clip(abs(p[0])/6,0,1);t=t*t*(3-2*t);share=.5+(.5*t if p[0]>=0 else -.5*t);out={n:share*a.get(n,0)+(1-share)*b.get(n,0) for n in a.keys()|b.keys()}
    else:out=donor_weights(p,side)
    pairs=sorted(out.items(),key=lambda kv:-kv[1])[:8];total=sum(w for _,w in pairs);return [[int(n),w/total] for n,w in pairs if w>1e-7]
sys.path.insert(0,str(P/'Tools/SmokeGreyCapri'));from waist_fit import fitted_torso
def torso(z,t,offset=0):
    p=fitted_torso(z,t,offset);ease=.20*math.sin(math.pi*np.clip((z-80)/20.2,0,1));p[:2]+=ease*np.array([math.sin(t),math.cos(t)])
    # Small forward pleat, tapering away above the crotch; not a full hip bulge.
    front=math.exp(-((z-90)/6.5)**2)
    for angle in (.36,math.tau-.36):
        distance=(t-angle+math.pi)%math.tau-math.pi;p[1]+=.20*math.exp(-(distance/.045)**2)*front
    return p
def leg(z,t,side,offset=0):
    sign=1 if side=='l' else -1;levels=[10,16,26,36,47.35,58,66,72]
    cx=np.interp(z,levels,[14.8,14.6,13.8,12.95,12.04,11.2,10.6,9.8]);cy=np.interp(z,levels,[-2.45,-2.4,-1.6,-.6,.8,1.7,2.3,2.6])
    rx=np.interp(z,levels,[6.3,6.4,6.75,7.1,7.35,8.1,9.,9.5]);ry=np.interp(z,levels,[6.35,6.55,7.2,8.1,8.85,10.1,11.0,11.2])
    crease=.22*math.exp(-(math.sin(t)/.105)**2)*math.exp(-((z-44)/44)**4)
    # Long clean drape planes, a soft knee fold and a modest shoe break.
    fold=.12*math.sin(z*.34+1.1*math.cos(t))*math.exp(-((z-45)/8)**2)
    fold+=.24*math.sin((z-10)*.9+1.4*math.sin(t))*math.exp(-((z-14)/3.4)**2)
    return np.array([sign*(cx+(rx+offset+fold)*math.sin(t)),cy+(ry+offset+fold+crease)*math.cos(t),z])
def grid(name,rows,side,slot=0,thickness=0,closed=False):
    rows=np.array(rows);h,w=rows.shape[:2];faces=[]
    for j in range(h-1):
        for i in range(w if closed else w-1):
            a=j*w+i;b=j*w+(i+1)%w;faces.append([a,b,b+w,a+w])
    return g.mesh_object(name,rows.reshape(-1,3),faces,side,'pants',slot,thickness)
def patch(name,side,fn,nu,nv,slot=0,thickness=.08):return grid(name,[[fn(u,v) for u in np.linspace(0,1,nu+1)] for v in np.linspace(0,1,nv+1)],side,slot,thickness)
theta=np.linspace(0,math.tau,97)
grid('Worsted_WaistAndSeat',[[torso(z,t) for t in theta] for z in np.linspace(100.2,80,24)],'both')
for side,sign in [('l',1),('r',-1)]:
    top=[]
    for i,t in enumerate(theta):
        if i<=48:top.append(torso(80,sign*t))
        else:
            a=(i-48)/48*math.pi;top.append(np.array([0.,.8-13.8*math.cos(a),80-8.5*math.sin(a)]))
    top=np.array(top);target=np.array([leg(66,t,side) for t in theta]);rows=[top]
    for alpha in np.linspace(.125,1,8):rows.append(top*(1-alpha)+target*alpha)
    for z in np.linspace(64.8,10,54):rows.append(np.array([leg(z,t,side) for t in theta]))
    grid('Worsted_Leg_'+side,rows,side)
    # A sewn turned hem; the ankle remains an open, uncinched trouser leg.
    grid('Hem_Return_'+side,[[leg(10+dz,t,side,inset) for t in theta] for dz,inset in [(0,0),(.08,-.09),(.2,-.14),(1.0,-.15),(2.4,-.15)]],side,4)
grid('Waist_InnerFacing',[[torso(100.2+dz,t,off) for t in theta] for dz,off in [(0,0),(-.08,-.1),(-.2,-.16),(-2.9,-.16)]],'both',4)
# Weld the continuous body before weight transfer. Both crotch halves receive
# one shared weight set instead of coincident but independently moving edges.
bpy.ops.object.select_all(action='DESELECT');shells=[ob for ob in g.objects if ob.name.startswith('Worsted_')];others=[ob for ob in g.objects if ob not in shells]
for ob in shells:ob.select_set(True)
bpy.context.view_layer.objects.active=shells[0];bpy.ops.object.join();shell=bpy.context.object;shell.name='Worsted_ContinuousWaistSeatAndLegs'
bm=bmesh.new();bm.from_mesh(shell.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2.e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(shell.data);bm.free();shell.data.update();shell['side']='both';g.objects=[shell]+others
shell.data.calc_loop_triangles();points=[(v.co.x*100,-v.co.y*100,v.co.z*100) for v in shell.data.vertices];faces=[list(reversed(t.vertices)) for t in shell.data.loop_triangles]
surface=BVHTree.FromPolygons(points,faces,all_triangles=True)
def project(p,offset=.06):hit,n,_,_=surface.find_nearest(Vector(p));return np.array(hit)+np.array(n)*offset
def seam(name,path,side,slot=3,radius=.022):return g.tube(name,path,radius,side,'pants',slot,False,5)
def stitches(name,path,side,slot=3):
    path=np.array(path);lengths=np.linalg.norm(np.diff(path,axis=0),axis=1);dist=np.r_[0,np.cumsum(lengths)];verts=[];fs=[]
    def at(t):
        i=min(len(lengths)-1,max(0,np.searchsorted(dist,t)-1));a=(t-dist[i])/max(lengths[i],1e-9);return path[i]*(1-a)+path[i+1]*a
    for s in np.arange(.08,dist[-1]-.23,.46):
        line=[at(s),at(s+.11)+[0,.012,0],at(s+.23)];start=len(verts)
        for i,p in enumerate(line):
            tangent=g.unit(line[min(i+1,2)]-line[max(i-1,0)]);a=g.unit(np.cross(tangent,[0,0,1] if abs(tangent[2])<.9 else [0,1,0]));b=np.cross(tangent,a)
            verts.extend(p+.018*(a*math.cos(t)+b*math.sin(t)) for t in np.linspace(0,math.tau,4,endpoint=False))
        for j in range(2):
            for k in range(4):fs.append([start+j*4+k,start+j*4+(k+1)%4,start+(j+1)*4+(k+1)%4,start+(j+1)*4+k])
    if verts:g.mesh_object(name,verts,fs,side,'pants',slot)
# A periodic ring has no end caps to merge at the front seam.
grid('Tailored_Waistband',[[torso(z,t,.075) for t in theta[:-1]] for z in np.linspace(97,100.2,5)],'both',0,.12,closed=True)
for i,t in enumerate((.50,1.55,math.pi,4.73,5.78)):
    patch('BeltLoop_'+str(i),'both',lambda u,v,t=t:torso(96.9+3.6*v,t+(u-.5)*.065,.20+.08*math.sin(math.pi*v)),3,7,0,.08)
for z in (97.2,100.0):stitches('Waist_Stitch_'+str(z),[torso(z,t,.19) for t in theta],'both')
patch('Concealed_Fly','both',lambda u,v:project(torso(84.5+12.4*v,.014+u*.075),.065),4,18,0,.06)
stitches('Fly_Stitch',[project(torso(z,.095),.13) for z in np.linspace(84.7,96.7,45)],'both')
for side,sign in [('l',1),('r',-1)]:
    def hand(u,v):return project(torso(95.8-11*u,sign*(.47+.48*u+(v-.5)*.04)),.075+.04*math.sin(math.pi*v))
    patch('SlantedPocketOpening_'+side,side,hand,28,3,4,.06)
    for edge in (0,1):stitches('PocketLip_'+side+str(edge),[hand(u,edge)+[0,.025,0] for u in np.linspace(0,1,50)],side)
    def rear(u,v):return project(torso(89+v*.42,sign*(2.32+.50*u)),.08)
    patch('BackWelt_'+side,side,rear,20,3,4,.07)
    for edge in (-.10,1.1):stitches('BackWeltLip_'+side+str(edge),[rear(u,edge) for u in np.linspace(0,1,35)],side)
    # Narrow blue strip follows the shared cloth shell through hip and knee.
    def outer(z,t):
        if z>=80:p=torso(z,sign*t)
        elif z<=66:p=leg(z,t,side)
        else:p=torso(80,sign*t)*(z-66)/14+leg(66,t,side)*(80-z)/14
        return project(p,.065)
    strip=[]
    for z in np.linspace(10.1,96.9,115):strip.append([outer(z,math.pi/2+.044*(u-.5)*2) for u in np.linspace(0,1,4)])
    grid('Cobalt_SidePiping_'+side,strip,side,1,.055)
    for offset in (-.055,.055):seam('PipingEdge_'+side+str(offset),[outer(z,math.pi/2+offset) for z in np.linspace(10.2,96.8,115)],side,3)
    for z in (10.45,11.7):stitches('Hem_Stitch_'+side+str(z),[leg(z,t,side,.05) for t in theta],side)
    # Small silver vine embroidery follows the pocket fabric; no armor panels.
    base=[]
    for v in np.linspace(0,1,52):base.append(project(torso(84.8+9*v,sign*(.71+.06*math.sin(v*math.tau))),.10))
    seam('SilverPocketVine_'+side,base,side,2,.025)
    for j,v in enumerate((.18,.36,.54,.72,.88)):
        branch=[];turn=1 if j%2 else -1
        for a in np.linspace(0,1,16):branch.append(project(torso(84.8+9*v+1.2*a,sign*(.71+.06*math.sin(v*math.tau)+turn*.065*math.sin(math.pi*a))),.11))
        seam('SilverVineLeaf_'+side+str(j),branch,side,2,.023)
# Low-profile silver star clasp with inset sapphire, attached at the waist.
center=torso(98.6,0,.35);ring=[]
for i in range(16):
    a=i*math.tau/16;rad=1.15 if i%2==0 else .46;ring.append(center+[rad*math.sin(a),0,rad*math.cos(a)])
g.mesh_object('Silver_StarClasp',[center]+ring,[[0,i+1,(i+1)%16+1] for i in range(16)],'both','pants',5,.12,.045)
bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,location=(center[0]*.01,-(center[1]+.095)*.01,center[2]*.01));gem=bpy.context.object;gem.name='Inset_Sapphire';gem.scale=(.0032,.0014,.0032);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
gem['material_slot']=6;gem['side']='both';gem['weight_zone']='pants';g.objects.append(gem)
# Bake object translations into the model data, retaining centimetre UE space.
data={k:[] for k in ('positions','triangles','weights','uv','normals','triangle_materials','parts')}
for ob in g.objects:
    mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active;start=len(data['positions']);coords=np.array([(ob.matrix_world@v.co)[:] for v in mesh.vertices]);points=coords*np.array([100,-100,100]);data['positions'].extend(points.tolist())
    for p in points:data['weights'].append(binding(p,'l' if p[0]>=0 else 'r'))
    count=0
    for t in mesh.loop_triangles:
        pp=points[list(t.vertices)]
        if np.linalg.norm(np.cross(pp[1]-pp[0],pp[2]-pp[0]))<1.e-9:continue
        data['triangles'].append([start+i for i in t.vertices]);tex=np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in t.loops]) if uv else np.array([[0,0],[1,0],[0,1]])
        data['uv'].append(g.valid_uv(tex,pp).tolist());data['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in t.loops]);data['triangle_materials'].append(int(ob['material_slot']));count+=1
    data['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(points),triangles=count,material=int(ob['material_slot'])))
data.update(source=native['source'],skeleton=native['skeleton'],bones=bones,material_slots=SLOTS,contract='Approved V2 modern slim suit trousers: fitted natural waist, shallow pleats, comfortable hip/thigh ease, pressed leg crease, gently tapered calf and flat open hem; continuous welded crotch; native Jason weights')
write(R/'Authored/Jason_BlueMagePants_Garment.json',data);write(R/'native_reference.json',native)
write(R/'construction_receipt.json',dict(reference='Design/black-mage-pants-concept-v02.png',vertices=len(data['positions']),triangles=len(data['triangles']),parts=len(data['parts']),hem_cm=10,body_source=native['source'],runtime_tested=False))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'BlueMagePants_Construction.blend'));print('MAGE_PANTS_GEOMETRY_AUTHORED',len(data['positions']),len(data['triangles']),flush=True)
