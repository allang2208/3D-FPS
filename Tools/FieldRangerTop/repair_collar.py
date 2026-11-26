"""Re-tailor the three torso meshes from the actual native neckline topology.

Blender background entry. The 23 first-person arm assets are not regenerated.
"""
import copy, gc, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME'); BASE=P/'SourceAssets/FieldRangerTop20261020'
R=BASE/'CollarRepair20261021'; ITEM='ue_field_sweater'
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import author as a
from geometry import unit, smooth, norm_weights, blend_weights, boundary, vertex, face, tube, normals
read=a.read; write=a.write

def loops(faces):
    neighbors={}
    for i,j in boundary(faces):
        neighbors.setdefault(i,[]).append(j);neighbors.setdefault(j,[]).append(i)
    remaining=set(neighbors);result=[]
    while remaining:
        start=min(remaining);ring=[start];previous=None;current=start
        while True:
            nxt=next(v for v in neighbors[current] if v!=previous)
            if nxt==start:break
            ring.append(nxt);previous,current=current,nxt
        remaining.difference_update(ring);result.append(ring)
    return result

def shell(d,points,faces,weights,ns,uvs,slot,offset=.025,thickness=.12):
    # Correct per-corner sidewall UVs, including the second triangle of each quad.
    start=len(d['positions']);count=len(points)
    for amount in (offset+thickness,offset):
        for p,n,w in zip(points,ns,weights):vertex(d,np.array(p)+np.array(n)*amount,w)
    for f,uv in zip(faces,uvs):
        face(d,[start+i for i in f],slot,uv)
        face(d,[start+count+i for i in f[::-1]],slot,np.array(uv)[::-1])
    edges=boundary(faces)
    for i,j in edges:
        ids=[start+j,start+i,start+count+i,start+count+j]
        length=float(np.linalg.norm(np.array(points[i])-points[j]))/8
        uv=[[0,0],[length,0],[length,thickness/8],[0,thickness/8]]
        for t in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in t],slot,[uv[k] for k in t])
    return [start+i for i in range(count)],edges

def shared_normals(ps,fs):
    # The UE capture splits UV/material seams. Those splits are not tailoring creases.
    cross=-np.cross(ps[fs[:,1]]-ps[fs[:,0]],ps[fs[:,2]]-ps[fs[:,0]])
    sums=np.zeros_like(ps)
    for k in range(3):np.add.at(sums,fs[:,k],cross)
    _,inverse=np.unique(np.round(ps,5),axis=0,return_inverse=True);merged=np.zeros((inverse.max()+1,3))
    np.add.at(merged,inverse,sums);ns=merged[inverse]
    return ns/np.maximum(np.linalg.norm(ns,axis=1)[:,None],1e-12)

def clip_patch(d,indices,field,slot=1):
    points=[];ws=[];ns=[];ff=[];uvs=[];lookup={}
    ps=np.array(d['positions']);fs=np.array(d['triangles']);smooth_ns=shared_normals(ps,fs[indices])
    def put(v):
        p,n,w,tex,value=v;key=tuple(np.round(p,6))
        if key not in lookup:
            lookup[key]=len(points);points.append(p);ns.append(n);ws.append(w)
        return lookup[key]
    for fi in indices:
        tri=fs[fi];poly=[(ps[i],smooth_ns[i],d['weights'][i],np.array(d['uv'][fi][c]),field(ps[i],d['weights'][i])) for c,i in enumerate(tri)]
        clipped=[]
        for u,v in zip(poly,poly[1:]+poly[:1]):
            if u[4]>=0:clipped.append(u)
            if (u[4]>=0)!=(v[4]>=0):
                t=u[4]/(u[4]-v[4]);clipped.append((u[0]+t*(v[0]-u[0]),unit(u[1]+t*(v[1]-u[1])),blend_weights(u[2],v[2],t),u[3]+t*(v[3]-u[3]),0))
        for j in range(1,len(clipped)-1):
            poly=[clipped[0],clipped[j],clipped[j+1]];ff.append([put(v) for v in poly]);uvs.append([v[3] for v in poly])
    if not ff:return
    ids,edges=shell(d,points,ff,ws,ns,uvs,slot)
    # Connected seam paths avoid thousands of separately capped seam segments.
    seam_loops=loops(ff)
    print('TAILORING_SEAMS',d['profile'],field.__name__,[len(r) for r in seam_loops],flush=True)
    for ring in seam_loops:
        path=[np.array(d['positions'][ids[i]])+ns[i]*.025 for i in ring]
        weights=[ws[i] for i in ring]
        tube(d,path,.023,4,lambda x:weights[int(np.argmin(np.linalg.norm(np.array(path)-x,axis=1)))],closed=True,sides=5)

def clean_upper(d,source,garment_faces):
    """A new continuous leather yoke and collar enclosing the legacy crew rim."""
    ps=np.array(d['positions']);fs=np.array(d['triangles']);bones=d['bones'];neck=np.array(bones['neck_01']['position'])
    shoulder=np.mean([bones['upperarm_'+s]['position'][2] for s in ('l','r')])
    base_z=max(bones['neck_02']['position'][2]-2.6,149.0 if d['profile']=='Jason' else 158.0)
    width=np.mean([abs(bones['upperarm_'+s]['position'][0]-neck[0]) for s in ('l','r')])+9
    chosen=[fi for fi in garment_faces if abs(ps[fs[fi],0].mean()-neck[0])<width]
    tree=BVHTree.FromPolygons([Vector(p) for p in ps],fs[chosen].tolist(),all_triangles=True)
    if d['profile']=='Jason':
        skin=read(P/'SourceAssets/FieldHat20261019/native_head_jason.json');sp=skin['positions'];sf=skin['triangles']
    else:
        sp=source['positions'];sf=[f for f,s in zip(source['triangles'],source['triangle_materials']) if s in (3,4)]
    skin_tree=BVHTree.FromPolygons([Vector(p) for p in sp],sf,all_triangles=True)
    count=128;angles=np.linspace(0,math.tau,count,endpoint=False);height=[];minimum=[]
    for row in range(49+12):
        zs=[];rs=[]
        for theta in angles:
            direction=np.array([math.sin(theta),math.cos(theta),0.])
            low=shoulder-6.3+7.0*abs(math.sin(theta))**3
            z=low+(base_z-low)*min(row/48,1) if row<=48 else base_z+(row-48)/12*(3.25-.38*max(math.cos(theta),0)**6)
            center=np.r_[neck[:2],z];origin=center+direction*40
            hit,_,_,_=tree.ray_cast(Vector(origin),Vector(-direction),40)
            body_radius=max(0,float((np.array(hit)-center)@direction)) if hit is not None else 0
            hit,_,_,_=skin_tree.ray_cast(Vector(origin),Vector(-direction),40)
            skin_radius=max(0,float((np.array(hit)-center)@direction)) if hit is not None else 0
            fallback=(1-min(row/48,1))*12+min(row/48,1)*5.8
            rs.append(max(body_radius+.42,skin_radius+.6,fallback));zs.append(z)
        minimum.append(rs);height.append(zs)
    minimum=np.array(minimum);height=np.array(height)
    # Smooth an expanded envelope, so isolated source folds cannot leave steps
    # along the shoulder silhouette while the real cloth stays underneath.
    padded=np.pad(minimum,((4,4),(0,0)),mode='edge');radii=minimum.copy()
    for dy in range(9):
        for dx in range(-3,4):radii=np.maximum(radii,np.roll(padded[dy:dy+len(minimum)],dx,axis=1))
    for _ in range(12):
        radii=.5*radii+.125*(np.roll(radii,1,1)+np.roll(radii,-1,1)+np.r_[radii[:1],radii[:-1]]+np.r_[radii[1:],radii[-1:]])
    radii=np.maximum(minimum,radii)
    points=[];weights=[]
    for row in range(len(radii)):
        for i,theta in enumerate(angles):
            p=np.r_[neck[:2],height[row,i]]+np.array([math.sin(theta),math.cos(theta),0])*radii[row,i]
            hit,_,fi,_=tree.find_nearest(Vector(p));tri=fs[chosen[fi]];bc=a.bary(np.array(hit),ps[tri]);names=set().union(*(d['weights'][v] for v in tri))
            w=norm_weights({n:sum(d['weights'][v].get(n,0)*c for v,c in zip(tri,bc)) for n in names})
            blend=float(smooth((height[row,i]-(base_z-5))/5))
            collar={'spine_05':.25,'neck_01':.65,'neck_02':.10} if row<=48 else {'spine_05':.25*(1-(row-48)/12),'neck_01':.65+.15*(row-48)/12,'neck_02':.10+.10*(row-48)/12}
            weights.append(blend_weights(w,collar,blend));points.append(p)
    points=np.array(points);ff=[];uv=[];v=np.zeros_like(radii)
    for row in range(1,len(radii)):v[row]=v[row-1]+np.linalg.norm(points.reshape(-1,count,3)[row]-points.reshape(-1,count,3)[row-1],axis=1)/8
    for row in range(len(radii)-1):
        for i in range(count):
            j=(i+1)%count;ids=[row*count+i,row*count+j,(row+1)*count+j,(row+1)*count+i]
            tex=[[i/count*math.tau*10/8,v[row,i]],[(i+1)/count*math.tau*10/8,v[row,j]],[(i+1)/count*math.tau*10/8,v[row+1,j]],[i/count*math.tau*10/8,v[row+1,i]]]
            for t in ((0,1,2),(0,2,3)):
                tri=[ids[k] for k in t];out=np.mean(points[tri],0)-np.r_[neck[:2],np.mean(points[tri,2])]
                order=list(t)
                if np.cross(points[tri[1]]-points[tri[0]],points[tri[2]]-points[tri[0]])@out>0:order.reverse()
                ff.append([ids[k] for k in order]);uv.append([tex[k] for k in order])
    ns=normals(points,ff);first=len(d['triangles']);ids,_=shell(d,points,ff,weights,ns,uv,1,0,.18)
    outer=list(range(first,first+len(ff)*2,2))
    for row in (0,48,len(radii)-1):
        path=[np.array(d['positions'][ids[row*count+i]])+ns[row*count+i]*.025 for i in range(count)]
        tube(d,path,.025,4,lambda p,row=row,path=path:weights[row*count+int(np.argmin(np.linalg.norm(np.array(path)-p,axis=1)))],closed=True,sides=5)
    d['collar_repair']=dict(method='Continuous 128-column envelope yoke and standing collar; old folded rim enclosed',base_height_cm=base_z,top_height_cm=base_z+3.25,shell_thickness_cm=.18,skin_clearance_cm=.6,garment_clearance_cm=.42)
    return outer,base_z

def details(d,outer_faces,base_z):
    ps=np.array(d['positions']);fs=np.array(d['triangles']);neck=np.array(d['bones']['neck_01']['position'])
    selected=[i for i in outer_faces if abs(ps[fs[i],0].mean()-neck[0])<24]
    tree=BVHTree.FromPolygons([Vector(p) for p in ps],fs[selected].tolist(),all_triangles=True)
    ns=shared_normals(ps,fs[selected])
    def project(x,z):
        hit,_,idx,_=tree.ray_cast(Vector((x,50,z)),Vector((0,-1,0)),100)
        if hit is None:raise RuntimeError('Closure projection missed '+str((d['profile'],x,z)))
        tri=fs[selected[idx]];bc=a.bary(np.array(hit),ps[tri]);names=set().union(*(d['weights'][i] for i in tri))
        w=norm_weights({n:sum(d['weights'][i].get(n,0)*v for i,v in zip(tri,bc)) for n in names})
        normal=unit(np.sum(ns[tri]*bc[:,None],axis=0))
        if normal[1]<0:normal=-normal
        return np.array(hit),normal,w
    def strip(path,width,slot):
        points=[];ws=[];ns=[];ff=[];uv=[];length=[0.]
        columns=7
        for i,(x,z) in enumerate(path):
            if i:length.append(length[-1]+float(np.linalg.norm(np.array(path[i])-path[i-1])))
            for sign in np.linspace(-1,1,columns):
                p,n,w=project(x+sign*width*.5,z);points.append(p);ns.append(n);ws.append(w)
        for i in range(len(path)-1):
            for j in range(columns-1):
                ids=[i*columns+j,i*columns+j+1,(i+1)*columns+j+1,(i+1)*columns+j]
                left=width*j/(columns-1)/8;right=width*(j+1)/(columns-1)/8
                tex=[[left,length[i]/8],[right,length[i]/8],[right,length[i+1]/8],[left,length[i+1]/8]]
                for t in ((0,1,2),(0,2,3)):
                    order=list(t);pp=np.array([points[ids[k]] for k in order])
                    if np.cross(pp[1]-pp[0],pp[2]-pp[0])[1]>0:order.reverse()
                    ff.append([ids[k] for k in order]);uv.append([tex[k] for k in order])
        ids,_=shell(d,points,ff,ws,ns,uv,slot,.20,.10)
        for side in (0,columns-1):
            path=[np.array(d['positions'][ids[i*columns+side]])+ns[i*columns+side]*.03 for i in range(len(path))]
            tube(d,path,.023,4,lambda x:ws[int(np.argmin(np.linalg.norm(np.array(points)-x,axis=1)))],sides=5)
    center=[p for p in ps[np.unique(fs[outer_faces])] if abs(p[0]-neck[0])<3 and p[1]>neck[1]+3]
    hem=min(p[2] for p in center)+1.1
    strip([(float(neck[0]),float(z)) for z in np.linspace(hem,base_z+2.3,90)],2.45,0)
    for sign in (-1,1):
        strip([(float(neck[0]+sign*(10+2.8*t)),float(hem+8+10*t)) for t in np.linspace(0,1,25)],.72,1)
    p,n,w=project(float(neck[0]+1.5),base_z+1.5);a.button(d,p+n*.25,n,w,radius=.40)

def body(profile):
    source=read(BASE/'Sources'/(profile+'.json'));before=read(R/'Before'/(profile+'.json'))
    canonical=read(P/'SourceAssets/FieldSweaterSurfaceRepair20260930/Authored/Body.json')
    cf=np.array(canonical['triangles']);outer_count=len(canonical['positions'])//2
    of=np.flatnonzero(np.max(cf,axis=1)<outer_count);inner=np.flatnonzero(np.min(cf,axis=1)>=outer_count)
    d=dict(profile=profile,binding_source=source.get('binding_source',source.get('source')),bones=source['bones'],positions=copy.deepcopy(before['positions'][:len(source['positions'])]),weights=copy.deepcopy(source['weights']),triangles=[],uv=[],triangle_materials=[],material_slots=a.SLOTS)
    outer_faces=[];skin_normals={};counts={'corrected_outer_to_cloth':0,'corrected_inner_to_lining':0,'removed_neck_rim_faces':0}
    ofs=set(of);ins=set(inner)
    for fi,tri in enumerate(source['triangles']):
        # The original closed shirt stays beneath the new continuous yoke.
        if fi in ofs:
            slot=0;outer_faces.append(len(d['triangles']));counts['corrected_outer_to_cloth']+=before['triangle_materials'][fi]==2
        elif fi in ins:slot=2;counts['corrected_inner_to_lining']+=before['triangle_materials'][fi]==0
        elif fi<len(cf):slot=2
        else:slot=5;skin_normals[len(d['triangles'])]=source['normals'][fi]
        tex=np.array(before['uv'][fi])
        if slot in (0,2):
            p=np.array([d['positions'][i] for i in tri]);area=abs(np.linalg.det(np.stack([tex[1]-tex[0],tex[2]-tex[0]])))
            if area<1e-8:
                normal=abs(np.cross(p[1]-p[0],p[2]-p[0]));axes=[i for i in range(3) if i!=np.argmax(normal)];tex=p[:,axes]/8
        face(d,tri,slot,tex)
    new_upper,base_z=clean_upper(d,source,list(range(len(cf))))
    frames={s:[np.array(source['bones'][n+'_'+s]['position']) for n in ('upperarm','lowerarm','hand')] for s in ('l','r')}
    def forearm(p,w):
        side=a.arm_side(w)
        if side is None:return -50.
        upper,elbow,hand=frames[side];lo=unit(hand-elbow);t=(p-elbow)@lo;prox=-(p-hand)@lo
        seed=np.array(source['bones']['lowerarm_'+side]['axes'][2]);radial=unit(p-(elbow+lo*t))
        return max(3.1-prox,min(t+2,prox-3.5,(radial@seed-.08)*7))
    clip_patch(d,outer_faces,forearm)
    for side,(upper,elbow,hand) in frames.items():
        lo=unit(hand-elbow);pool=[i for i in np.unique(np.array(d['triangles'])[outer_faces]) if a.arm_side(d['weights'][i])==side and 1<-(np.array(d['positions'][i])-hand)@lo<2.6]
        if pool:
            i=max(pool,key=lambda v:d['positions'][v][1]);p=np.array(d['positions'][i]);n=unit(p-(elbow+lo*((p-elbow)@lo)));a.button(d,p+n*.22,n,d['weights'][i])
    details(d,outer_faces+new_upper,base_z)
    a.finish(d)
    for fi,n in skin_normals.items():d['normals'][fi]=n
    d['contract']='CollarRepair20261021: topology-derived native shirt; continuous skin-and-garment-envelope leather yoke and 3.25cm standing collar; closed .18cm leather shell; projected closure with nondegenerate UV; native weights'
    d['collar_repair'].update(counts)
    # Remove superseded/unreferenced points before export; no global geometric weld.
    used=sorted({i for f in d['triangles'] for i in f});mapping={v:i for i,v in enumerate(used)}
    d['positions']=[d['positions'][i] for i in used];d['weights']=[d['weights'][i] for i in used];d['triangles']=[[mapping[i] for i in f] for f in d['triangles']]
    write(R/'Authored'/ITEM/(profile+'.json'),d)
    print('COLLAR_AUTHORED',profile,len(d['triangles']),d['collar_repair'],flush=True)
    return d

def owner(d):
    result=copy.deepcopy(d);result['profile']='Owner_Jason';result['material_slots']=a.SLOTS+['OwnerHidden_'+s for s in a.SLOTS]
    for key in ('triangles','uv','normals','triangle_materials'):result[key]=[]
    bones=d['bones'];names={v['index']:k for k,v in bones.items()};arms=set()
    for name in bones:
        current=name
        while current in bones:
            if current in ('upperarm_l','upperarm_r'):arms.add(name);break
            current=names.get(bones[current]['parent'])
    mass=[sum(v for n,v in w.items() if n in arms) for w in d['weights']];lookup={};positions=np.array(d['positions']);colors=np.array(d['colors']) if 'colors' in d else None
    for fi,tri in enumerate(d['triangles']):
        values=[mass[i] for i in tri];slot=d['triangle_materials'][fi]
        if min(values)>=.4 or max(values)<=.4:
            face(result,tri,slot+(6 if min(values)>=.4 else 0),d['uv'][fi]);result['normals'].append(d['normals'][fi]);continue
        for hidden in (False,True):
            poly=[(np.eye(3)[i],values[i]) for i in range(3)];part=[]
            for x,y in zip(poly,poly[1:]+poly[:1]):
                ix=x[1]>=.4 if hidden else x[1]<=.4;iy=y[1]>=.4 if hidden else y[1]<=.4
                if ix:part.append(x[0])
                if ix!=iy:part.append(x[0]+(.4-x[1])/(y[1]-x[1])*(y[0]-x[0]))
            for k in range(1,len(part)-1):
                bs=[part[0],part[k],part[k+1]];ids=[];ns=[];uv=[]
                for b in bs:
                    p=np.sum(positions[tri]*b[:,None],axis=0);key=tuple(np.round(p,7))
                    if key not in lookup:
                        weights=norm_weights({n:sum(d['weights'][v].get(n,0)*a for v,a in zip(tri,b)) for n in set().union(*(d['weights'][v] for v in tri))});lookup[key]=vertex(result,p,weights)
                        if colors is not None:result['colors'].append(np.sum(colors[tri]*b[:,None],axis=0).tolist())
                    ids.append(lookup[key]);ns.append(unit(np.sum(np.array(d['normals'][fi])*b[:,None],axis=0)).tolist());uv.append(np.sum(np.array(d['uv'][fi])*b[:,None],axis=0))
                if len(set(ids))<3:continue
                face(result,ids,slot+(6 if hidden else 0),uv);result['normals'].append(ns)
    write(R/'Authored'/ITEM/'Owner_Jason.json',result)
    print('COLLAR_AUTHORED Owner_Jason',len(result['triangles']),flush=True)

def main():
    rows=[]
    for profile in ('Body','Jason'):
        d=body(profile)
        if profile=='Jason':owner(d)
        del d;gc.collect()
    for profile,group in (('Body','Body'),('Jason','Body'),('Owner_Jason','Owner')):
        rows.append(dict(profile=profile,group=group,authored=str(R/'Authored'/ITEM/(profile+'.json'))))
    write(R/'authored.json',dict(completed=True,records=rows,runtime_tested=False))

if __name__=='__main__':main()
