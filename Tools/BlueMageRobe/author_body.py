"""Tailored full-body robe and continuous skirt, in each native body binding."""
import sys,math,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import *
from paired_surface import relax
from tailor_volume import tailor

def arm_sets(bones):
    byid={v['index']:n for n,v in bones.items()};result={}
    for side in ('l','r'):
        def belongs(name):
            while name in bones:
                if name=='upperarm_'+side:return True
                parent=bones[name]['parent']
                if parent<0:break
                name=byid[parent]
            return False
        result[side]={n for n in bones if belongs(n)}
    return result

def mass(w,names):return sum(v for n,v in w.items() if n in names)

def split_arm_boundary(p,f,ws,arm_names):
    points=p.tolist();weights=copy.deepcopy(ws);values=[mass(w,arm_names) for w in ws];cache={};out=[];regions=[]
    for row in f:
        for arm in (False,True):
            poly=[]
            for aa,bb in zip(row,np.roll(row,-1)):
                a,b=int(aa),int(bb);ina=(values[a]>.4)==arm;inb=(values[b]>.4)==arm
                if ina:poly.append(a)
                if ina!=inb:
                    edge=tuple(sorted((a,b)))
                    if edge not in cache:
                        t=(.4-values[a])/(values[b]-values[a]);cache[edge]=len(points)
                        points.append((p[a]+(p[b]-p[a])*t).tolist());weights.append(blend_weights(ws[a],ws[b],t));values.append(.4)
                    poly.append(cache[edge])
            for k in range(1,len(poly)-1):out.append([poly[0],poly[k],poly[k+1]]);regions.append(arm)
    return np.array(points),np.array(out),weights,np.array(regions)

def bm_loops(bm):
    edges={e for e in bm.edges if e.is_boundary};result=[]
    while edges:
        edge=edges.pop();start,current=edge.verts;ring=[start,current]
        while current!=start:
            following=[e for e in current.link_edges if e in edges]
            if not following:raise RuntimeError('Noncontinuous native clothing boundary')
            edge=following[0];edges.remove(edge);current=edge.other_vert(current)
            if current!=start:ring.append(current)
        result.append(ring)
    return result

def upper_surface(skin,profile,waist,top):
    bones=skin['bones'];names=sorted(bones);arms=arm_sets(bones);all_arm=arms['l']|arms['r'];bm=bmesh.new();dw=bm.verts.layers.deform.verify()
    allowed=(0,1,2,3) if profile=='Jason' else (1,2,3)
    fs=[f for f,m in zip(skin['triangles'],skin['triangle_materials']) if m in allowed]
    used=sorted({i for f in fs for i in f});vs={i:bm.verts.new(skin['positions'][i]) for i in used}
    for i,v in vs.items():
        for n,w in skin['weights'][i].items():v[dw][names.index(n)]=w
    for face_ids in fs:bm.faces.new([vs[i] for i in face_ids])
    if profile=='Jason':
        head=read(P/'SourceAssets/ST6Refine20261018/NeckClosure/native_head_neck.json');byid={b['index']:n for n,b in head['bones'].items()};hv=[]
        for p,w in zip(head['positions'],head['weights']):
            v=bm.verts.new(p);hv.append(v);mapped={}
            for n,value in w.items():
                while n not in bones:n=byid[head['bones'][n]['parent']]
                mapped[n]=mapped.get(n,0)+value
            for n,value in norm_weights(mapped).items():v[dw][names.index(n)]=value
        for face_ids in head['triangles']:bm.faces.new([hv[i] for i in face_ids])
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    boundary_vertices={v for e in bm.edges if e.is_boundary for v in e.verts}
    bmesh.ops.remove_doubles(bm,verts=list(boundary_vertices),dist=.04)
    # Trim the waist without cutting the low cuff of either hanging arm.
    torso_faces=[f for f in bm.faces if max(sum(value for idx,value in v[dw].items() if names[idx] in all_arm) for v in f.verts)<.2]
    torso_edges={e for f in torso_faces for e in f.edges};torso_verts={v for f in torso_faces for v in f.verts}
    bmesh.ops.bisect_plane(bm,geom=list(torso_verts)+list(torso_edges)+torso_faces,plane_co=Vector((0,0,waist-3.2)),plane_no=Vector((0,0,1)),dist=.00001,clear_inner=True,clear_outer=False)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector((0,0,top)),plane_no=Vector((0,0,1)),dist=.00001,clear_inner=False,clear_outer=True)
    for side in ('l','r'):
        e=np.array(bones['lowerarm_'+side]['position']);w=np.array(bones['hand_'+side]['position']);axis=unit(w-e)
        for distance,trim in ((1.,True),(4.5,False)):
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector(w-axis*distance),plane_no=Vector(axis),dist=.00001,clear_inner=False,clear_outer=trim)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    # The independent facial mesh and torso have a native nonplanar neck seam.
    # If their boundary samples differ, join only that matching neck contour.
    neck_loops=[ring for ring in bm_loops(bm) if all(v.co.z>130 and v.co.z<top-.1 and abs(v.co.x)<16 for v in ring)]
    if len(neck_loops)==2:
        edges=[e for e in bm.edges if e.is_boundary and any(all(v in ring for v in e.verts) for ring in neck_loops)]
        bmesh.ops.bridge_loops(bm,edges=edges,use_pairs=True)
    elif neck_loops:raise RuntimeError('Native neck seam needs explicit contour pairing '+profile+' '+str([len(r) for r in neck_loops]))
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
    p=np.array([v.co[:] for v in bm.verts]);f=np.array([[v.index for v in face_ids.verts] for face_ids in bm.faces]);ws=[norm_weights({names[i]:x for i,x in v[dw].items()}) for v in bm.verts];bm.free()
    p,f,ws=tailor(p,f,ws,bones,waist,top)
    p,f,ws,region=split_arm_boundary(p,f,ws,all_arm)
    arm_mass=np.array([mass(w,all_arm) for w in ws]);clearance=np.full(len(p),.72)
    for side in ('l','r'):
        e=np.array(bones['lowerarm_'+side]['position']);w=np.array(bones['hand_'+side]['position']);axis=unit(w-e);prox=-(p-w)@axis
        which=np.array([mass(x,arms[side])>.4 for x in ws]);clearance[which]=.32+.30*smooth((prox[which]-4.5)/4)
    neck=(p[:,2]>top-6)&(np.abs(p[:,0])<9);clearance[neck]=.32+.18*smooth((top-p[neck,2])/6)
    # tailor() already produced the eased outer cloth surface.
    clearance.fill(0.)
    p,n,construction=relax(p,f,boundary(f),clearance,np.array([0,0,top]),np.array([0,0,1]),thickness=.14)
    return p,f,ws,region,clearance,n,arms,construction

def emit_upper(skin,profile,owner,data,waist,top):
    p,f,ws,region,clearance,n,arms,construction=data;d=new_mesh(profile+('_Owner' if owner else ''),skin)
    if owner:f=f[~region]
    # Retain the native surface coordinates for deterministic UV and cuff bands.
    def face_material(fi,ids):
        w={name:sum(ws[int(i)].get(name,0) for i in ids)/3 for name in set().union(*(ws[int(i)] for i in ids))}
        if mass(w,arms['l']|arms['r'])>.4:
            side=max(('l','r'),key=lambda s:mass(w,arms[s]));b=skin['bones'];e=np.array(b['lowerarm_'+side]['position']);hand=np.array(b['hand_'+side]['position']);prox=-((p[ids]-hand)@unit(hand-e)).mean()
            return 2 if prox<4.5 else 1
        return 6 if p[ids,2].mean()>top-4.3 else 0
    def texture(ids,_):
        mat=face_material(0,ids);pts=p[ids]
        if mat in (1,2):
            side=max(('l','r'),key=lambda s:sum(mass(ws[int(i)],arms[s]) for i in ids));b=skin['bones'];a,e,w=[np.array(b[x+'_'+side]['position']) for x in ('upperarm','lowerarm','hand')];axis=unit(w-e);up=unit(e-a);seed=unit(np.cross(up,axis));cross=np.cross(axis,seed);q=pts-w
            theta=np.arctan2(q@cross,q@seed)/math.tau;v=(-(q@axis)-1)/3.5 if mat==2 else (q@axis)/25
            uv=np.column_stack((theta,v));uv[:,0][uv[:,0]<0]+=1
            if np.ptp(uv[:,0])>.5:uv[:,0][uv[:,0]<.5]+=1
            return uv
        theta=np.arctan2(pts[:,0],-(pts[:,1]-1.))/math.tau;theta[theta<0]+=1
        if np.ptp(theta)>.5:theta[theta<.5]+=1
        return np.column_stack((theta if mat==6 else theta*3.,(top-pts[:,2])/4.3 if mat==6 else pts[:,2]/25))
    def inner(fi,ids):return 3 if face_material(fi,ids) in (1,2) else 10
    paired(d,p,f,ws,clearance,.14,face_material,texture,inner,n)
    # Unused arm vertices are intentionally not exported in the owner variant.
    if owner:
        used=sorted({i for f in d['triangles'] for i in f});remap={v:i for i,v in enumerate(used)}
        d['positions']=[d['positions'][i] for i in used];d['weights']=[d['weights'][i] for i in used];d['triangles']=[[remap[i] for i in f] for f in d['triangles']]
    return d

def native_weight(skin,tri,point):
    a,b,c=np.array([skin['positions'][i] for i in tri]);v0=b-a;v1=c-a;v2=np.asarray(point)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
    if abs(den)<1e-12:return copy.deepcopy(skin['weights'][tri[0]])
    x=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;y=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den;bb=np.maximum([1-x-y,x,y],0);bb/=bb.sum();result={}
    for i,k in enumerate(tri):
        for n,v in skin['weights'][k].items():result[n]=result.get(n,0)+v*bb[i]
    return norm_weights(result)

def fitted_tree(d):
    points=copy.deepcopy(d['positions']);faces=copy.deepcopy(d['triangles']);weights=copy.deepcopy(d['weights']);mats=list(d['triangle_materials'])
    faces=[f for f,m in zip(faces,mats) if m in (0,6)]
    tree=BVHTree.FromPolygons([Vector(p) for p in points],faces,all_triangles=True)
    src=dict(positions=points,weights=weights)
    def cast(origin,direction):
        origin=np.asarray(origin,float);direction=np.asarray(direction,float)
        hit,no,index,distance=tree.ray_cast(Vector(origin),Vector(direction),80)
        if hit is None:raise RuntimeError('Missing fitted torso intersection '+str(origin))
        return np.array(hit),native_weight(src,faces[index],hit)
    return cast

def append_skirt(d,skin,cast,waist,bottom,proxy=False):
    segments,rows=(64,30) if proxy else (128,66);start=len(d['positions']);height=waist-bottom
    theta=np.linspace(0,math.tau,segments,endpoint=False);center=np.array([0.,1.,waist]);rings=[]
    samples=[]
    for angle in theta:
        direction=np.array([math.sin(angle),-math.cos(angle),0]);hit,w=cast(center,direction);samples.append((hit,w))
    for j,t in enumerate(np.linspace(0,1,rows)):
        row=[];z=waist-t*height
        for i,angle in enumerate(theta):
            native,w=samples[i];xy=native[:2]-center[:2];direction=unit(xy);ease=smooth(t/.35)
            # Broad front/back inverted pleats keep one connected skirt.
            da=min(abs(angle),abs(angle-math.tau));db=abs(angle-math.pi)
            fold=sum(-1.45*math.exp(-(v/.14)**2)+.8*math.exp(-((v-.20)/.10)**2) for v in (da,db))
            flutter=(.48*math.cos(8*angle)+.2*math.cos(12*angle))*smooth(t/.3)
            flare=np.array([18.0*math.sin(angle),-13.0*math.cos(angle)])*(t**.82)
            pos=np.array([*(center[:2]+xy+direction*(.12+ease*(fold+flutter))+flare),z])
            wt=blend_weights(w,{'pelvis':1.},float(smooth((waist-z-4)/8)))
            row.append(vertex(d,pos,wt))
        rings.append(row)
    mat=9 if proxy else 4
    for j in range(rows-1):
        for i in range(segments):
            ids=[rings[j][i],rings[j][(i+1)%segments],rings[j+1][(i+1)%segments],rings[j+1][i]]
            uv=[[i/segments,j/(rows-1)],[(i+1)/segments,j/(rows-1)],[(i+1)/segments,(j+1)/(rows-1)],[i/segments,(j+1)/(rows-1)]]
            out=np.array([math.sin((i+.5)*math.tau/segments),-math.cos((i+.5)*math.tau/segments),0])
            for k in ((0,1,2),(0,2,3)):face(d,[ids[v] for v in k],mat,[uv[v] for v in k],out)
    if not proxy:
        # A physical turned hem, captured by the same cloth asset as the skirt.
        prior=rings[-1]
        for inward,up in ((.12,.05),(.17,.25),(.17,.85)):
            nxt=[]
            for i,vi in enumerate(rings[-1]):
                p=np.array(d['positions'][vi]);q=p-np.array([math.sin(theta[i]),-math.cos(theta[i]),0])*inward+np.array([0,0,up]);nxt.append(vertex(d,q,d['weights'][vi]))
            for i in range(segments):
                ids=[prior[i],prior[(i+1)%segments],nxt[(i+1)%segments],nxt[i]];uv=[[i/segments,1.],[(i+1)/segments,1.],[(i+1)/segments,1.-up/height],[i/segments,1.-up/height]]
                for k in ((0,1,2),(0,2,3)):face(d,[ids[v] for v in k],4,[uv[v] for v in k])
            prior=nxt
    return dict(vertices=len(d['positions'])-start,waist_cm=waist,hem_cm=bottom,segments=segments,rows=rows,proxy=proxy)

def append_trim(d,cast,waist,top,hood):
    # Native Body/Jason face toward their toe bones (+Y), independently of
    # Blender's reflected display coordinates. Sample the correct torso side
    # again so the adornments retain that side's actual surface and weights.
    bones=d['bones']
    front=1. if sum(bones['ball_'+s]['position'][1]-bones['foot_'+s]['position'][1] for s in ('l','r'))>0 else -1.
    back=-front
    # Center embroidery follows the actual fitted chest rather than a flat card.
    for x in (-1.15,1.15):
        strips=[]
        for z in np.linspace(waist+2,top-4.4,68):
            row=[]
            for dx in (-.32,.32):
                hit,w=cast([x+dx,1,z],[0,front,0]);hit[1]+=.055*front;row.append(vertex(d,hit,w))
            strips.append(row)
        for j in range(len(strips)-1):
            ids=strips[j]+strips[j+1][::-1];uv=[[j/24,0],[j/24,1],[(j+1)/24,1],[(j+1)/24,0]]
            for k in ((0,1,2),(0,2,3)):face(d,[ids[v] for v in k],6,[uv[v] for v in k],[0,front,0])
    # Narrow navy leather belt, with a rounded real edge.
    rings=[];steps=128
    for z,offset in [(waist-2,.18),(waist-1.85,.28),(waist+1.85,.28),(waist+2,.18),(waist+1.85,.10),(waist-1.85,.10)]:
        ring=[]
        for angle in np.linspace(0,math.tau,steps,endpoint=False):
            axis=np.array([math.sin(angle),-math.cos(angle),0]);hit,w=cast([0,1,z],axis);ring.append(vertex(d,hit+axis*offset,w))
        rings.append(ring)
    for j in range(len(rings)):
        for i in range(steps):
            ids=[rings[j][i],rings[j][(i+1)%steps],rings[(j+1)%len(rings)][(i+1)%steps],rings[(j+1)%len(rings)][i]]
            for k in ((2,1,0),(3,2,0)):face(d,[ids[v] for v in k],7,[[i/steps,j/5],[(i+1)/steps,j/5],[(i+1)/steps,(j+1)/5]])
    hit,w=cast([0,1,waist],[0,front,0]);yy=hit[1]+.5*front
    path=[[-1.7,yy,waist-1.35],[1.7,yy,waist-1.35],[1.7,yy,waist+1.35],[-1.7,yy,waist+1.35]]
    tube(d,path,.14,8,w,closed=True,sides=10);tube(d,[[0,yy+.06*front,waist-1.3],[0,yy+.06*front,waist+1.3]],.10,8,w)
    # Collar clasp and blue inset. Both share the fitted native neck weights.
    hit,nw=cast([0,1,top-2.1],[0,front,0]);hit[1]+=.22*front
    circle=[hit+np.array([.72*math.cos(t),0,.72*math.sin(t)]) for t in np.linspace(0,math.tau,32,endpoint=False)];tube(d,circle,.13,8,nw,closed=True)
    center=vertex(d,hit+[0,.32*front,0],nw);edge=[vertex(d,hit+np.array([.58*math.cos(t),.10*front,.58*math.sin(t)]),nw) for t in np.linspace(0,math.tau,12,endpoint=False)]
    for i in range(12):face(d,[center,edge[i],edge[(i+1)%12]],11,[[.5,.5],[0,0],[1,0]],[0,front,0])
    if not hood:return
    # Compact dropped hood: body-skinned, with a sewn lining and a closed tip.
    pp=[];ww=[];ff=[];segments=64;rows=28
    for j,t in enumerate(np.linspace(0,1,rows)):
        z=top-3.4-t*20;surface,wt=cast([0,1,z],[0,back,0]);width=(5.0+9.0*math.sin(math.pi*t))*(1-t)+.18*t;depth=1.2+3.2*math.sin(math.pi*t)
        for angle in np.linspace(0,math.tau,segments,endpoint=False):
            pp.append([width*math.sin(angle),surface[1]+back*(1.2+depth*(.5+.5*math.cos(angle))),z]);ww.append(wt)
    for j in range(rows-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;c=(j+1)*segments+(i+1)%segments;e=(j+1)*segments+i
            ff.extend([[a,b,c],[a,c,e]])
    pp=np.array(pp);ff=np.array(ff)
    # Correct the loft to UE outward winding once from its radial geometry.
    if back>0:ff=ff[:,::-1]
    paired(d,pp,ff,ww,0.,.14,lambda fi,ids:5,lambda ids,_:np.array([[((int(i)%segments)/segments),int(i)//segments/(rows-1)] for i in ids]),lambda fi,ids:10)

def build(row):
    skin=read(row['file']);profile=row['profile'];bones=skin['bones'];scale=np.linalg.norm(np.array(bones['thigh_l']['position'])-np.array(bones['calf_l']['position']))/39.1
    waist=float(bones['spine_02']['position'][2]+5.2*scale);top=float(bones.get('neck_02',bones['neck_01'])['position'][2]-.45*scale);bottom=float(min(bones['foot_l']['position'][2],bones['foot_r']['position'][2])+3.5*scale)
    data=upper_surface(skin,profile,waist,top);report={}
    for owner in (False,True):
        d=emit_upper(skin,profile,owner,data,waist,top);cast=fitted_tree(d);append_trim(d,cast,waist,top,not owner)
        skirt=append_skirt(d,skin,cast,waist,bottom);proxy=append_skirt(d,skin,cast,waist,bottom,True)
        d['cloth_dimensions']=dict(waist_cm=waist,hem_cm=bottom,length_cm=waist-bottom,scale=scale)
        from hip_fit import apply as fit_hips
        fit_hips(d,skin);finish(d);label=profile+('_Owner' if owner else '')
        write(R/'Authored/Body'/(label+'.json'),d);report[label]=dict(vertices=len(d['positions']),triangles=len(d['triangles']),skirt=skirt,proxy=proxy,upper_construction=data[-1])
        print('BLUE_ROBE_BODY_AUTHORED',label,len(d['triangles']),flush=True)
    return report

if __name__=='__main__':
    report={}
    for row in read(R/'input_inventory.json')['rows']:
        if row['profile'] not in ('Body','Jason'):continue
        report.update(build(row));write(R/'body_authoring.json',report)
