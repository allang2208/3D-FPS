"""Tailor mid-calf cotton trousers and transfer Jason weights on donor triangles."""
import importlib.util,json,math
from pathlib import Path
import bpy,bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004'
spec=importlib.util.spec_from_file_location('capri_geometry',str(P/'Tools/BrownLeatherSet/geometry.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
bpy.ops.wm.read_factory_settings(use_empty=True)
native=json.loads((P/'SourceAssets/BrownLeatherSet20261004/native_reference.json').read_text());bones=native['bones']
donor=json.loads((P/'SourceAssets/BootsEquipment20261004/jeans.json').read_text())
dp=np.asarray(donor['positions']);df=np.asarray(donor['triangles'],int)
native_ids={b['name']:b['index'] for b in bones};bone_remap={b['index']:native_ids[b['name']] for b in donor['bones']}
trees={}
for side,sign in [('l',1),('r',-1),('both',0)]:
    faces=df if sign==0 else df[np.mean(dp[df,0],axis=1)*sign>=-.15]
    trees[side]=(BVHTree.FromPolygons(dp.tolist(),faces.tolist(),all_triangles=True),faces)

def donor_weights(p,side):
    tree,faces=trees[side]
    q,_,idx,_=tree.find_nearest(Vector(p))
    ids=faces[idx];a,b,c=dp[ids];v0=b-a;v1=c-a;v2=np.array(q)-a
    d00=v0@v0;d01=v0@v1;d11=v1@v1;d20=v2@v0;d21=v2@v1;den=d00*d11-d01*d01
    if abs(den)<1e-12:coeff=np.array([1.,0,0])
    else:
        v=(d11*d20-d01*d21)/den;w=(d00*d21-d01*d20)/den;coeff=np.maximum([1-v-w,v,w],0);coeff/=coeff.sum()
    result={}
    for vi,fac in zip(ids,coeff):
        for bi,w in donor['weights'][vi]:
            bi=bone_remap[bi];result[bi]=result.get(bi,0)+float(w*fac)
    return result

def binding(p,side):
    # Centre crotch vertices belong to both sewn halves, rather than being
    # sampled separately by leg. Transition into the ipsilateral thigh.
    if p[2]>80:result=donor_weights(p,'both')
    elif p[2]>=66 and abs(p[0])<6:
        left=donor_weights(p,'l');right=donor_weights(p,'r')
        t=min(1.,max(0.,abs(p[0])/6));t=t*t*(3-2*t)
        share=.5+.5*t if p[0]>=0 else .5-.5*t
        result={bi:share*left.get(bi,0)+(1-share)*right.get(bi,0) for bi in left.keys()|right.keys()}
    else:result=donor_weights(p,side)
    pairs=sorted(result.items(),key=lambda x:(-x[1],x[0]))[:8];total=sum(w for _,w in pairs)
    return [[int(bi),w/total] for bi,w in pairs if w>1e-7]

def torso(z,t,offset=0):
    rx=np.interp(z,[80,85,90,95,100.2],[18.3,18.7,18.3,17.7,17.1])+offset
    ry=np.interp(z,[80,85,90,95,100.2],[13.8,14.4,14.2,13.7,12.7])+offset
    return np.array([rx*math.sin(t),.8+ry*math.cos(t),z])

def leg(z,t,side,offset=0):
    sign=1 if side=='l' else -1;hs=[30,40,47.35,58,67,72]
    cx=np.interp(z,hs,[13.5,12.6,12.04,11.2,10.5,9.8]);cy=np.interp(z,hs,[-1.2,-.4,.8,1.7,2.3,2.6])
    rx=np.interp(z,hs,[6.65,6.7,6.65,7.7,8.65,9.1]);ry=np.interp(z,hs,[7.85,8.3,8.55,9.4,10.4,10.6])
    fold=(.13*math.sin(z*.63+1.4*math.sin(t))+.08*math.sin(5*t+z*.31))
    fold*=min(1,max(0,(z-31)/5))*min(1,max(0,(72-z)/8))
    knee=.15*math.sin(z*1.4+math.sin(t))*math.exp(-((z-46)/4)**2)
    return np.array([sign*(cx+(rx+fold+offset)*math.sin(t)),cy+(ry+fold+knee+offset)*math.cos(t),z])

def grid(name,rows,side,slot=1,thick=0):
    rows=np.asarray(rows);h,w=rows.shape[:2];faces=[]
    for j in range(h-1):
        for i in range(w-1):
            a=j*w+i;faces.append([a,a+1,a+w+1,a+w])
    points=rows.reshape(-1,3)
    # Set garment-facing winding before Solidify. Mirroring a trouser leg or
    # reversing the vertical panel parameter must not turn its front inward.
    score=0.
    for f in faces:
        a,b,c=points[f[:3]];center=points[f].mean(0);z=center[2]
        if z>=80:origin=np.array([0.,.8,center[2]])
        else:
            sg=1 if center[0]>=0 else -1
            origin=np.array([sg*np.interp(z,[30,40,47.35,58,67,80],[13.5,12.6,12.04,11.2,10.5,0]),np.interp(z,[30,47.35,67,80],[-1.2,.8,2.3,.8]),z])
        score+=np.cross(b-a,c-a)@(center-origin)
    inward='InnerFacing' in name or 'DoubleTurn' in name
    if (score<0)!=inward:faces=[list(reversed(f)) for f in faces]
    return g.mesh_object(name,points,faces,side,'pants',slot,thick)

def patch(name,side,fn,nu,nv,slot=1,thick=.09):
    return grid(name,[[fn(u,v) for u in np.linspace(0,1,nu+1)] for v in np.linspace(0,1,nv+1)],side,slot,thick)

def stitched(name,path,side,normal,closed=False):
    path=np.asarray(path,float)
    if closed:path=np.vstack([path,path[0]])
    lengths=np.linalg.norm(np.diff(path,axis=0),axis=1);dist=np.r_[0,np.cumsum(lengths)]
    def at(t):
        i=min(len(lengths)-1,max(0,np.searchsorted(dist,t)-1));a=(t-dist[i])/max(lengths[i],1e-8)
        p=path[i]*(1-a)+path[i+1]*a;return p+g.unit(normal(p))*.018
    # Disconnected small thread segments live in one object and one material.
    points=[];faces=[]
    for start in np.arange(.08,dist[-1]-.26,.48):
        line=[at(start),at(start+.12),at(start+.26)];offset=len(points)
        for i,p in enumerate(line):
            tangent=g.unit(line[min(i+1,2)]-line[max(i-1,0)]);a=g.unit(np.cross(tangent,g.unit(normal(p))));b=np.cross(tangent,a)
            points.extend(p+.023*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,math.tau,4,endpoint=False))
        for j in range(2):
            for k in range(4):faces.append([offset+j*4+k,offset+j*4+(k+1)%4,offset+(j+1)*4+(k+1)%4,offset+(j+1)*4+k])
    if points:g.mesh_object(name,points,faces,side,'pants',3)

# Continuous seat and saddle crotch follow the established Jason proportions.
theta=np.linspace(0,math.tau,97)
grid('Twill_WaistAndSeat',[[torso(z,t) for t in theta] for z in np.linspace(100.2,80,19)],'both')
for side,sign in [('l',1),('r',-1)]:
    top=[]
    for i,t in enumerate(theta):
        if i<=48:top.append(torso(80,sign*t))
        else:
            a=(i-48)/48*math.pi;top.append(np.array([0.,.8-13.8*math.cos(a),80-8.5*math.sin(a)]))
    top=np.array(top);target=np.array([leg(66,t,side) for t in theta]);rows=[top]
    for alpha in np.linspace(.125,1,8):rows.append(top*(1-alpha)+target*alpha)
    for z in np.linspace(64.8,30,30):
        row=[]
        for t in theta:
            # A 2.4 cm outer vent is an authored hem notch, with a sewn return.
            gap=abs((t-math.pi/2+math.pi)%math.tau-math.pi)
            vent=2.4*max(0,1-gap/.10)*max(0,1-(z-30)/3.0)
            row.append(leg(z+vent,t,side))
        rows.append(row)
    grid('Twill_Leg_'+side,rows,side)
    hem=np.array(rows[-1]);lining=[]
    for dz,inset in [(0,0),(.08,.09),(.2,.14),(.8,.15),(1.8,.15)]:
        ring=hem.copy();center=np.array([sign*13.5,-1.2]);rad=ring[:,:2]-center;rad/=np.linalg.norm(rad,axis=1)[:,None]
        ring[:,:2]-=rad*inset;ring[:,2]+=dz;lining.append(ring)
    grid('Hem_DoubleTurn_'+side,lining,side,4)
    g.tube('Hem_Edge_'+side,hem[:-1],.073,side,'pants',1,True,6)
waist=np.array([torso(100.2,t) for t in theta]);lining=[]
for dz,off in [(0,0),(-.08,-.1),(-.2,-.18),(-2.8,-.18)]:lining.append([torso(100.2+dz,t,off) for t in theta])
grid('Waist_InnerFacing',lining,'both',4)

# Sew the three cloth shells before transferring weights or projecting trim.
# UV loops stay split as needed; geometry and skin weights at the seams do not.
bpy.ops.object.select_all(action='DESELECT')
shells=[ob for ob in g.objects if ob.name.startswith('Twill_')]
others=[ob for ob in g.objects if ob not in shells]
for ob in shells:ob.select_set(True)
bpy.context.view_layer.objects.active=shells[0]
bpy.ops.object.join();shell=bpy.context.object;shell.name='Twill_ContinuousWaistSeatAndLegs'
bm=bmesh.new();bm.from_mesh(shell.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(shell.data);bm.free();shell.data.update();shell['side']='both'
shell.data.set_sharp_from_angle(angle=math.radians(52))
g.objects=[shell]+others

# Project pocket and panel construction onto the tailored outer cloth.
surface_points=[];surface_faces=[]
for ob in g.objects:
    if not ob.name.startswith('Twill_'):continue
    ob.data.calc_loop_triangles();start=len(surface_points)
    surface_points.extend([(v.co.x*100,-v.co.y*100,v.co.z*100) for v in ob.data.vertices])
    surface_faces.extend([[start+i for i in reversed(t.vertices)] for t in ob.data.loop_triangles])
surface=BVHTree.FromPolygons(surface_points,surface_faces,all_triangles=True)
def project(point,off=.06):
    q,n,_,_=surface.find_nearest(Vector(point));return np.array(q)+np.array(n)*off

patch('Tailored_Waistband','both',lambda u,v:torso(96.7+3.5*v,u*math.tau,.08),96,5,1,.13)
for i,t in enumerate([.45,1.52,math.pi,4.76,5.83]):
    patch('Five_BeltLoop_'+str(i),'both',lambda u,v,t=t:torso(96.4+4.05*v,t+(u-.5)*.075,.28+.12*math.sin(v*math.pi)),4,8,1,.14)
for z in [97.0,99.95]:stitched('Waist_DoubleStitch_'+str(z),[torso(z,t,.23) for t in theta[:-1]],'both',lambda p:[p[0],p[1]-.8,0],True)
patch('Zip_Fly_Facing','both',lambda u,v:project(torso(84+12.6*v,.012+u*.093),.12),5,20,1,.09)
stitched('Zip_Fly_Stitch',[project(torso(z,.115),.18) for z in np.linspace(84.3,96.6,55)],'both',lambda p:[0,1,0])
g.rivet('Dark_Gunmetal_WaistButton',torso(98.45,0,.4),[0,1,0],'both','pants',.52)

for side,sign in [('l',1),('r',-1)]:
    outward=lambda p,sign=sign:[sign*.5,1,0]
    # Narrow inset pocket mouth, two stitched lips and actual turned fabric.
    def hand(u,v):return project(torso(95.7-11.4*u,sign*(.45+.5*u+(v-.5)*.038)),.085+.08*math.sin(v*math.pi))
    patch('Slanted_HandPocket_'+side,side,hand,32,4,4,.085)
    for edge in [0,1]:stitched('HandPocket_Stitch_%s_%s'%(side,edge),[hand(t,edge) for t in np.linspace(0,1,65)],side,outward)
    # Back welt pockets retain a distinct opening without a bulky patch bag.
    def rear(u,v):return project(torso(88.4+v*.62,sign*(2.32+u*.52)),.16)
    patch('Rear_WeltOpening_'+side,side,rear,22,3,4,.09)
    for v in [-.17,1.17]:stitched('Rear_WeltStitch_%s_%s'%(side,v),[rear(t,v) for t in np.linspace(0,1,45)],side,lambda p:[0,-1,0])
    # Low-profile side bag 15 cm tall; subdued flap with concealed snaps.
    def cargo(u,v,extra=0):
        z=56.2+15.1*v;t=.81+1.11*u
        pt=leg(min(z,66),t,side) if z<=66 else torso(80,sign*t)*(z-66)/14+leg(66,t,side)*(80-z)/14
        return project(pt,.16+.27*math.sin(u*math.pi)*math.sin(v*math.pi)+extra)
    patch('Flat_CargoPocket_'+side,side,cargo,24,24,1,.11)
    patch('Cargo_PocketFlap_'+side,side,lambda u,v:cargo(u,.80+.22*v,.15+.05*math.sin(v*math.pi)),24,7,1,.12)
    for edge in [0,1]:
        stitched('Cargo_VerticalStitch_%s_%s'%(side,edge),[cargo(.025+.95*edge,v,.075) for v in np.linspace(.035,.97,60)],side,lambda p,sign=sign:[sign,0,0])
    for edge in [.025,.805,.998]:
        stitched('Cargo_HorizontalStitch_%s_%s'%(side,edge),[cargo(u,edge,.075 if edge<.8 else .20) for u in np.linspace(.025,.975,60)],side,lambda p,sign=sign:[sign,0,0])
    # Soft cotton articulated knee, gently shaped corners, no rigid kneecap.
    def knee(u,v):
        z=41.5+12*v;spread=.50*(.72+.28*math.sin(math.pi*v));t=(u-.5)*2*spread
        return project(leg(z,t,side),.09)
    patch('Soft_KneeFacing_'+side,side,knee,22,20,1,.08)
    for edge in [0,1]:stitched('Knee_VerticalDart_%s_%s'%(side,edge),[knee(edge,v)+[0,.05,0] for v in np.linspace(.03,.97,60)],side,lambda p:[0,1,0])
    for edge in [0,1]:stitched('Knee_HorizontalDart_%s_%s'%(side,edge),[knee(u,edge)+[0,.05,0] for u in np.linspace(.025,.975,55)],side,lambda p:[0,1,0])
    for angle in [math.pi/2,3*math.pi/2]:
        path=[project(leg(z,angle,side),.09) for z in np.linspace(33,64.7,90)]
        stitched('Leg_Seam_%s_%s'%(side,angle),path,side,lambda p,sign=sign:[p[0]-sign*13,p[1]+.5,0])
    for z in [30.55,31.45]:
        path=[]
        for t in theta[:-1]:
            gap=abs((t-math.pi/2+math.pi)%math.tau-math.pi)
            lift=2.4*max(0,1-gap/.10)
            path.append(leg(z+lift,t,side,.085))
        stitched('Hem_DoubleStitch_%s_%s'%(side,z),path,side,lambda p,sign=sign:[p[0]-sign*13.5,p[1]+1.2,0],True)

data={k:[] for k in ['positions','triangles','weights','uv','normals','triangle_materials','parts']}
for ob in g.objects:
    mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active;start=len(data['positions'])
    points=np.array([[v.co.x*100,-v.co.y*100,v.co.z*100] for v in mesh.vertices]);data['positions'].extend(points.tolist())
    side=ob['side']
    for p in points:data['weights'].append(binding(p,side if side!='both' else ('l' if p[0]>=0 else 'r')))
    count=0
    for t in mesh.loop_triangles:
        p=points[list(t.vertices)]
        if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-9:continue
        data['triangles'].append([start+i for i in t.vertices]);mapped=np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in t.loops])
        data['uv'].append(g.valid_uv(mapped,p).tolist())
        data['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in t.loops])
        data['triangle_materials'].append(int(ob['material_slot']));count+=1
    data['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(points),triangles=count,material=int(ob['material_slot'])))
data.update(source=native['source'],skeleton=native['skeleton'],bones=bones,contract='SmokeGreyCapri20261004 CrotchSeamFix20261005: native Jason; UE cm; mid-calf hem 30cm; welded continuous waist/seat/legs; paired crotch weights blend to same-side thigh over 6cm; per-corner UV and normals')
(R/'Jason_SmokeGreyCapri_Garment.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(R/'native_reference.json').write_text(json.dumps(native,separators=(',',':')),encoding='utf-8')
(R/'production.json').write_text(json.dumps(dict(vertices=len(data['positions']),triangles=len(data['triangles']),parts=len(data['parts']),hem_height_cm=30,matching_shirt='ue_field_sweater_charcoal',revision='CrotchSeamFix20261005',crotch_construction='welded continuous shell; identical centre seam binding with bilateral 6cm falloff',runtime_tested=False),indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Capri_Construction.blend'))
print('CAPRI_GEOMETRY_AUTHORED',len(data['positions']),len(data['triangles']),flush=True)
