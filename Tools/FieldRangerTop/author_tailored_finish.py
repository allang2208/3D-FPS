"""Refine the active ranger yoke: contact, tapered edges, stitches and closure."""
import copy,gc,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/FieldRangerTop20261020';R=BASE/'TailoredFinish20261021'
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import repair_collar as r
from geometry import unit,smooth,blend_weights,norm_weights,normals,vertex,face,tube
original_shell=r.shell;original_write=r.write;r.R=R
color_lookup={}
def key(p):return tuple(round(float(x),7) for x in p)

def seam(d,path,weights,ns,pitch=.32,length=.20,radius=.016,closed=True):
    path=np.array(path);ns=np.array(ns);count=len(path)
    edges=np.linalg.norm(np.roll(path,-1,axis=0)-path,axis=1) if closed else np.linalg.norm(np.diff(path,axis=0),axis=1)
    arc=np.r_[0,np.cumsum(edges)];total=arc[-1]
    def sample(distance):
        distance=distance%total if closed else float(np.clip(distance,0,total-1e-8))
        i=min(int(np.searchsorted(arc,distance,side='right')-1),len(edges)-1);t=(distance-arc[i])/max(edges[i],1e-9);j=(i+1)%count
        return path[i]*(1-t)+path[j]*t,unit(ns[i]*(1-t)+ns[j]*t),blend_weights(weights[i],weights[j],t)
    for center in np.arange(pitch*.5,total-pitch*.3,pitch):
        pp=[];ww=[]
        for t in (0.,.333,.667,1.):
            p,n,w=sample(center+(t-.5)*length);pp.append(p+n*(.004+.016*math.sin(math.pi*t)));ww.append(w)
        tube(d,pp,radius,4,lambda x,pp=pp,ww=ww:ww[int(np.argmin(np.linalg.norm(np.array(pp)-x,axis=1)))],sides=4)

def refined_shell(d,points,faces,weights,ns,uvs,slot,offset=.025,thickness=.12):
    if len(points)!=128*61 or slot!=1:return original_shell(d,points,faces,weights,ns,uvs,slot,offset,thickness)
    points=np.asarray(points);grid=points.reshape(61,128,3);neck=np.array(d['bones']['neck_01']['position'])
    source_ps=np.array(d['positions']);source_fs=np.array(d['triangles']);slots=np.array(d['triangle_materials'])
    tree=BVHTree.FromPolygons([Vector(p) for p in source_ps],source_fs[np.isin(slots,[0,2])].tolist(),all_triangles=True)
    selected=source_fs[np.isin(slots,[0,2])]
    if d['profile']=='Jason':
        skin=r.read(P/'SourceAssets/FieldHat20261019/native_head_jason.json');skin_ps=skin['positions'];skin_fs=skin['triangles']
    else:
        skin=r.read(BASE/'Sources/Body.json');skin_ps=skin['positions'];skin_fs=[f for f,s in zip(skin['triangles'],skin['triangle_materials']) if s in (3,4)]
    skin_tree=BVHTree.FromPolygons([Vector(p) for p in skin_ps],skin_fs,all_triangles=True)
    for row in range(16):
        target=[]
        for p in grid[row]:
            direction=unit(np.r_[p[:2]-neck[:2],0]);center=np.r_[neck[:2],p[2]];origin=center+direction*40
            hit,_,_,_=tree.ray_cast(Vector(origin),Vector(-direction),40);body_r=float((np.array(hit)-center)@direction) if hit is not None else 0
            hit,_,_,_=skin_tree.ray_cast(Vector(origin),Vector(-direction),40);skin_r=float((np.array(hit)-center)@direction) if hit is not None else 0
            target.append(max(body_r+.13,skin_r+.38))
        target=np.array(target);expanded=target.copy()
        for j in (-2,-1,1,2):expanded=np.maximum(expanded,np.roll(target,j))
        for _ in range(3):expanded=.5*expanded+.25*(np.roll(expanded,1)+np.roll(expanded,-1))
        target=np.maximum(target,expanded);blend=.88*(1-float(smooth(row/15)))
        for i,p in enumerate(grid[row]):
            direction=unit(np.r_[p[:2]-neck[:2],0]);old_radius=float(np.linalg.norm(p[:2]-neck[:2]));radius=old_radius*(1-blend)+min(old_radius,target[i])*blend
            grid[row,i]=np.r_[neck[:2],p[2]]+direction*radius
            if row<5:
                hit,_,fi,_=tree.find_nearest(Vector(grid[row,i]));tri=selected[fi];bc=r.a.bary(np.array(hit),source_ps[tri]);names=set().union(*(d['weights'][v] for v in tri))
                fit=norm_weights({n:sum(d['weights'][v].get(n,0)*b for v,b in zip(tri,bc)) for n in names})
                weights[row*128+i]=blend_weights(weights[row*128+i],fit,.8*(1-float(smooth(row/5))))
    ns[:]=normals(points,faces)
    # Both axes use measured surface distance, removing the enlarged shoulder grain.
    arc=np.zeros((61,129));v=np.zeros((61,128))
    for row in range(61):
        arc[row,1:]=np.cumsum(np.linalg.norm(np.roll(grid[row],-1,axis=0)-grid[row],axis=1))/8
        if row:v[row]=v[row-1]+np.linalg.norm(grid[row]-grid[row-1],axis=1)/8
    for fi,tri in enumerate(faces):
        seam_cross=any(i%128==0 for i in tri) and any(i%128==127 for i in tri)
        uvs[fi]=[[arc[i//128,128 if seam_cross and i%128==0 else i%128],v[i//128,i%128]] for i in tri]
    start=len(d['positions']);count=len(points)
    for layer in (0,1):
        for i,(p,n,w) in enumerate(zip(points,ns,weights)):
            row=i//128;edge=min(row,60-row);gauge=.075+.055*float(smooth(edge/3))
            q=p+n*(gauge if layer==0 else 0);vertex(d,q,w)
            pressure=math.exp(-edge/1.7);shade=1-.07*pressure
            color_lookup[key(q)]=[shade,shade*.995,shade*.985,1-.055*pressure] if layer==0 else [.65,.62,.58,1.]
    for tri,uv in zip(faces,uvs):
        face(d,[start+i for i in tri],1,uv);face(d,[start+count+i for i in tri[::-1]],2,np.array(uv)[::-1])
    edges=r.boundary(faces)
    for i,j in edges:
        ids=[start+j,start+i,start+count+i,start+count+j];length=np.linalg.norm(points[i]-points[j])/8;uv=[[0,0],[length,0],[length,.075/8],[0,.075/8]]
        for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],1,[uv[k] for k in tri])
    outer=[start+i for i in range(count)]
    for row in (.8,1.8,47.4,59.2):
        lo=int(row);t=row-lo;path=[];ww=[];nn=[]
        for i in range(128):
            ia=lo*128+i;ib=(lo+1)*128+i
            p=np.array(d['positions'][outer[ia]])*(1-t)+np.array(d['positions'][outer[ib]])*t
            path.append(p);nn.append(unit(ns[ia]*(1-t)+ns[ib]*t));ww.append(blend_weights(weights[ia],weights[ib],t))
        seam(d,path,ww,nn)
    d['tailored_finish']=dict(edge_thickness_cm=.075,panel_thickness_cm=.13,stitch_pitch_cm=.32,stitch_length_cm=.20,stitch_diameter_cm=.032,lower_edge_fit='locally seated against real shirt and skin envelope',uv='measured circumferential and longitudinal arc lengths')
    return outer,edges

def tailored_details(d,outer_faces,base_z):
    ps=np.array(d['positions']);fs=np.array(d['triangles']);neck=np.array(d['bones']['neck_01']['position'])
    chosen=[i for i in outer_faces if abs(ps[fs[i],0].mean()-neck[0])<24];tris=fs[chosen]
    tree=BVHTree.FromPolygons([Vector(p) for p in ps],tris.tolist(),all_triangles=True);ns=r.shared_normals(ps,tris)
    def project(x,z):
        hit,_,fi,_=tree.ray_cast(Vector((x,50,z)),Vector((0,-1,0)),100)
        if hit is None:raise RuntimeError('Tailored closure projection missed')
        tri=tris[fi];b=r.a.bary(np.array(hit),ps[tri]);names=set().union(*(d['weights'][i] for i in tri))
        w=norm_weights({n:sum(d['weights'][i].get(n,0)*a for i,a in zip(tri,b)) for n in names});normal=unit(np.sum(ns[tri]*b[:,None],0))
        if normal[1]<0:normal=-normal
        return np.array(hit),normal,w
    def ribbon(path,width,slot,bridge=False):
        path=np.array(path);columns=9;pp=[];nn=[];ww=[];uv=[];ff=[];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
        for i,(x,z) in enumerate(path):
            tangent=unit(path[min(i+1,len(path)-1)]-path[max(i-1,0)]);across=np.array([tangent[1],-tangent[0]])
            taper=.87+.13*float(smooth(min(i,len(path)-1-i)/2))
            for t in np.linspace(-.5,.5,columns):
                sample=np.array([x,z])+across*width*t*taper;p,n,w=project(*sample);pp.append(p);nn.append(n);ww.append(w)
        pp=np.array(pp);nn=np.array(nn)
        if bridge:
            yy=pp[:,1].reshape(-1,columns);smoothed=yy.copy()
            for _ in range(6):smoothed=.5*smoothed+.25*(np.r_[smoothed[:1],smoothed[:-1]]+np.r_[smoothed[1:],smoothed[-1:]])
            yy[:]=np.maximum(yy,smoothed+.045)
        for i in range(len(path)-1):
            for j in range(columns-1):
                ids=[i*columns+j,i*columns+j+1,(i+1)*columns+j+1,(i+1)*columns+j]
                tex=[[width*j/(columns-1)/8,arc[i]/8],[width*(j+1)/(columns-1)/8,arc[i]/8],[width*(j+1)/(columns-1)/8,arc[i+1]/8],[width*j/(columns-1)/8,arc[i+1]/8]]
                for t in ((0,1,2),(0,2,3)):
                    order=list(t);q=pp[[ids[k] for k in order]]
                    if np.cross(q[1]-q[0],q[2]-q[0])[1]>0:order.reverse()
                    ff.append([ids[k] for k in order]);uv.append([tex[k] for k in order])
        nn=normals(pp,ff);ids,_=original_shell(d,pp,ff,ww,nn,uv,slot,.045,.075)
        for side in (1,columns-2):
            used=[i*columns+side for i in range(len(path))];seam(d,[d['positions'][ids[i]] for i in used],[ww[i] for i in used],[nn[i] for i in used],pitch=.30,length=.19,closed=False)
        return ids
    center=[p for p in ps[np.unique(tris)] if abs(p[0]-neck[0])<3 and p[1]>neck[1]+3];hem=min(p[2] for p in center)+1.1
    ribbon([(neck[0],z) for z in np.linspace(hem,base_z+2.35,140)],2.35,0,True)
    for sign in (-1,1):ribbon([(neck[0]+sign*(10+2.8*t),hem+8+10*t) for t in np.linspace(0,1,28)],.70,1)
    ribbon([(neck[0]+x,base_z+1.25) for x in np.linspace(-.95,2.65,22)],1.18,1)
    p,n,w=project(neck[0]+1.95,base_z+1.25);r.a.button(d,p+n*.20,n,w,radius=.33)

def output(path,data):
    if path.parent.name=='ue_field_sweater':
        if not data['profile'].startswith('Owner'):data['colors']=[color_lookup.get(key(p),[1.,1.,1.,1.]) for p in data['positions']]
        data['collar_repair'].update(shell_thickness_cm=.13,edge_thickness_cm=.075,lower_skin_clearance_cm=.38,lower_garment_clearance_cm=.13)
        data['contract']='TailoredFinish20261021: seated tapered leather edges, arc-spaced stitches, continuous closure and collar fastening tab; isotropic leather and fine twill; native weights retained'
    return original_write(path,data)

def main():
    r.shell=refined_shell;r.details=tailored_details;r.write=output
    records=[]
    for profile in ('Body','Jason'):
        color_lookup.clear();d=r.body(profile)
        if profile=='Jason':r.owner(d)
        del d;gc.collect()
    for profile,group in (('Body','Body'),('Jason','Body'),('Owner_Jason','Owner')):records.append(dict(profile=profile,group=group,authored=str(R/'Authored/ue_field_sweater'/(profile+'.json'))))
    original_write(R/'authored.json',dict(completed=True,records=records,runtime_tested=False,preview_rendered=False))
if __name__=='__main__':main()
