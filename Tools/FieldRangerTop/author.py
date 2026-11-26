"""Tailored ranger panels, real leather thickness and native-bound garment details."""
import copy, gc, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from geometry import unit, smooth, norm_weights, blend_weights, boundary, vertex, face, tube
SLOTS=['RangerCloth','RangerLeather','RangerLining','RangerBrass','RangerThread','ExposedTorsoSkin']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def arm_side(w):
    masses={s:sum(v for n,v in w.items() if n.endswith('_'+s) and any(t in n for t in ('upperarm','lowerarm','hand','thumb','index','pinky','middle','ring'))) for s in ('l','r')}
    side=max(masses,key=masses.get)
    return side if masses[side]>.35 else None
def bary(p,tri):
    a,b,c=tri;v=b-a;w=c-a;q=p-a
    vv=v@v;ww=w@w;vw=v@w;den=vv*ww-vw*vw
    if abs(den)<1e-12:return np.array([1.,0,0])
    y=(ww*(q@v)-vw*(q@w))/den;z=(vv*(q@w)-vw*(q@v))/den
    x=np.clip([1-y-z,y,z],0,1);return x/max(x.sum(),1e-12)
def button(d,p,n,w,slot=3,radius=.32):
    n=unit(n);a=unit(np.cross(n,[0,0,1] if abs(n[2])<.9 else [0,1,0]));b=np.cross(n,a)
    rings=[]
    for height,r in ((0,radius*.93),(.10,radius),(.15,radius*.82)):
        rings.append([vertex(d,p+n*height+r*(a*math.cos(t)+b*math.sin(t)),w) for t in np.linspace(0,math.tau,24,endpoint=False)])
    for first,second in zip(rings,rings[1:]):
        for j in range(24):
            ids=[first[j],first[(j+1)%24],second[(j+1)%24],second[j]]
            for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],slot,[[0,0],[1,0],[1,1]],unit(np.mean([d['positions'][ids[k]] for k in tri],0)-p))
    for ring,sign in ((rings[0],-1),(rings[-1],1)):
        center=vertex(d,np.mean([d['positions'][i] for i in ring],0),w)
        for j in range(24):face(d,[center,ring[j],ring[(j+1)%24]],slot,[[.5,.5],[0,0],[1,0]],n*sign)
def append_shell(d,points,faces,weights,normals,uvs,slot,offset=.035,thickness=.12):
    start=len(d['positions']);points=np.asarray(points);normals=np.asarray(normals);count=len(points)
    for amount in (offset+thickness,offset):
        for p,n,w in zip(points,normals,weights):vertex(d,p+n*amount,w)
    for fi,tri in enumerate(faces):
        face(d,[start+i for i in tri],slot,uvs[fi])
        face(d,[start+count+i for i in tri[::-1]],slot,np.asarray(uvs[fi])[::-1])
    edges=boundary(faces)
    for a,b in edges:
        ids=[start+b,start+a,start+count+a,start+count+b]
        length=np.linalg.norm(points[a]-points[b])
        for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],slot,[[0,0],[length/8,0],[length/8,thickness/8]])
    return [start+i for i in range(count)],edges
def finish(d):
    # Weld only the normal calculation, preserving all native vertex and UV seams.
    p=np.asarray(d['positions']);f=np.asarray(d['triangles']);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    sums=np.zeros_like(p)
    for k in range(3):np.add.at(sums,f[:,k],cross)
    keys=np.round(p,5);_,inverse=np.unique(keys,axis=0,return_inverse=True);weld=np.zeros((inverse.max()+1,3))
    np.add.at(weld,inverse,sums);sums=weld[inverse];sums/=np.maximum(np.linalg.norm(sums,axis=1)[:,None],1e-12)
    d['normals']=sums[f].tolist()
    d['contract']='Approved ranger Concept01; native shirt bindings; closed leather yoke/collar/cuffs; twill cloth; original skin coverage retained; no animation changes'
    return d
def build(row):
    if row['group']!='FP':
        # Torso authoring now uses native boundary topology and paired lining.
        # Keep this entry point from regenerating the superseded radial-neck fit.
        from repair_collar import body, owner, R as repaired_root
        data=body('Jason' if row['profile']=='Owner_Jason' else row['profile'])
        if row['profile']=='Owner_Jason':owner(data)
        file=repaired_root/'Authored/ue_field_sweater'/(row['profile']+'.json')
        data=read(file)
        return dict(**row,authored=str(file),triangles=len(data['triangles']),vertices=len(data['positions']))
    source=read(row['file']);profile=row['profile'];world=row['group']!='FP';owner=row['group']=='Owner'
    bones=source['bones'];ps=np.array(source['positions']);fs=np.array(source['triangles']);oldslots=np.array(source['triangle_materials'])
    frames={}
    for side in ('l','r'):
        a,e,w=[np.array(bones[n+'_'+side]['position']) for n in ('upperarm','lowerarm','hand')]
        up,lo=unit(e-a),unit(w-e)
        index=np.array(bones.get('index_01_'+side,bones['hand_'+side])['position'])-w
        pinky=np.array(bones.get('pinky_01_'+side,bones['hand_'+side])['position'])-w
        dorsal=unit(np.cross(index,pinky))*(1 if side=='l' else -1)
        if np.linalg.norm(dorsal)<.5:dorsal=unit(np.array(bones['lowerarm_'+side]['axes'][2]))
        frames[side]=(a,e,w,up,lo,dorsal)
    shoulder_z=np.mean([frames[s][0][2] for s in frames])
    neck=np.array(bones['neck_01']['position']) if world else np.mean([frames[s][0] for s in frames],axis=0)
    sides=[arm_side(w) for w in source['weights']]
    if not world:
        for side,(a,e,w,up,lo,dorsal) in frames.items():
            ids=np.flatnonzero(np.array(sides)==side)
            if not len(ids):continue
            half=len(ids)//2;outer,inner=ids[:half],ids[half:]
            middle=(ps[outer]+ps[inner])*.5
            radial=ps[outer]-ps[inner];radial/=np.maximum(np.linalg.norm(radial,axis=1)[:,None],1e-9)
            prox=-(middle-w)@lo;along=(middle-e)@lo
            fade=smooth((prox-3.2)/5)*smooth(((middle-a)@up-2)/6)
            ripple=.20+.12*np.sin(along*.75+radial@dorsal*2)
            ripple+=.11*np.sin(along*1.8)*np.exp(-along**2/35)
            delta=radial*(fade*np.maximum(ripple,.02))[:,None]
            ps[outer]+=delta;ps[inner]+=delta
    else:
        cloth_ids=np.unique(fs[(oldslots%5)==0])
        for i in cloth_ids:
            if sides[i] is not None or ps[i,1]>neck[1]-4:continue
            x,z=ps[i,0]-neck[0],ps[i,2]
            fold=np.exp(-((abs(x)-9.)/.7)**2)-.55*np.exp(-((abs(x)-9.8)/.6)**2)
            fade=float(smooth((shoulder_z-3-z)/4)*smooth((z-shoulder_z+25)/5))
            ps[i,1]-=.18*fold*fade
    source['positions']=ps.tolist()
    def coords(p,side):
        if side:
            a,e,w,up,lo,dorsal=frames[side];t=(p-e)@lo;blend=float(smooth((t+4)/8));axis=unit(up*(1-blend)+lo*blend)
            origin=e+lo*t if t>0 else a+up*((p-a)@up)
            radial=unit(p-origin);seed=unit(dorsal-axis*(dorsal@axis));across=np.cross(axis,seed)
            angle=math.atan2(radial@across,radial@seed)/math.tau
            uv=np.array([angle*math.tau*max(np.linalg.norm(p-origin),2.)/8,(np.linalg.norm(e-a)+(p-e)@axis)/8])
            prox=-(p-w)@lo
            leather=max(3.1-prox,min(t+2.0,prox-3.5,(radial@seed-.08)*7))
            return uv,radial,leather
        radial=unit(np.array([p[0]-neck[0],p[1]-neck[1],0.]))
        return np.array([p[0]/8,p[2]/8]),radial,p[2]-(shoulder_z-5.8+.12*abs(p[0]-neck[0]))
    values=[coords(p,sides[i]) for i,p in enumerate(ps)]
    d=dict(profile=profile,binding_source=source.get('binding_source',source.get('source')),bones=bones,
        positions=ps.tolist(),weights=copy.deepcopy(source['weights']),triangles=[],uv=[],triangle_materials=[],
        material_slots=SLOTS+(['OwnerHidden_'+s for s in SLOTS] if owner else []))
    # Shared coordinate field for cloth and its lining; current wrist endpoints stay fixed.
    for fi,tri in enumerate(fs):
        original_slot=int(oldslots[fi]);hidden=owner and original_slot>=5;slot=original_slot%5 if owner else original_slot
        if world and slot in (3,4):
            face(d,tri,5+(6 if hidden else 0),source['uv'][fi]);continue
        n=np.mean(source['normals'][fi],0);radial=np.mean([values[i][1] for i in tri],0)
        outside=slot!=2 if not world else n@radial>0
        uv=np.array([values[i][0] for i in tri])
        if all(sides[i] is not None for i in tri):
            # Use existing seam-aware longitudinal mapping, rescaled to 8 cm.
            uv=np.asarray(source['uv'][fi])*25/8
        face(d,tri,(0 if outside else 2)+(6 if hidden else 0),uv)
    # Clip leather patch borders through triangles rather than painting jagged face blocks.
    for hidden in ((False,True) if owner else (False,)):
        points=[];weights=[];normals=[];triangles=[];uvs=[];lookup={}
        def put(p,n,w,tex):
            key=tuple(np.round(p,6))
            if key not in lookup:
                lookup[key]=len(points);points.append(p);weights.append(w);normals.append(unit(n))
            return lookup[key]
        for fi,tri in enumerate(fs):
            if d['triangle_materials'][fi]!=(6 if hidden else 0):continue
            polygon=[]
            for c,i in enumerate(tri):
                polygon.append((ps[i],np.array(source['normals'][fi][c]),source['weights'][i],np.array(d['uv'][fi][c]),values[i][2]))
            clipped=[]
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                if a[4]>=0:clipped.append(a)
                if (a[4]>=0)!=(b[4]>=0):
                    t=a[4]/(a[4]-b[4]);clipped.append((a[0]+t*(b[0]-a[0]),unit(a[1]+t*(b[1]-a[1])),blend_weights(a[2],b[2],t),a[3]+t*(b[3]-a[3]),0))
            for j in range(1,len(clipped)-1):
                poly=[clipped[0],clipped[j],clipped[j+1]]
                triangles.append([put(*v[:4]) for v in poly]);uvs.append([v[3] for v in poly])
        ids,edges=append_shell(d,points,triangles,weights,normals,uvs,1+(6 if hidden else 0))
        # Fine raised piping follows each actual cut edge and shares its native weights.
        for a,b in edges:
            p,q=np.array(d['positions'][ids[a]]),np.array(d['positions'][ids[b]])
            if np.linalg.norm(q-p)<.07:continue
            tube(d,[p,q],.025,4+(6 if hidden else 0),lambda x,a=a,b=b,p=p,q=q:blend_weights(weights[a],weights[b],float(np.clip(np.linalg.norm(x-p)/np.linalg.norm(q-p),0,1))),sides=4)
    # Low-profile cuff closures on each physically present arm.
    for side in frames:
        candidates=[i for i,s in enumerate(sides) if s==side and 1.<-(ps[i]-frames[side][2])@frames[side][4]<2.6]
        if not candidates:continue
        i=max(candidates,key=lambda i:values[i][1]@frames[side][5])
        hidden=owner
        button(d,ps[i]+values[i][1]*.19,values[i][1],source['weights'][i],3+(6 if hidden else 0))
    if world:body_details(d,source,values,sides,neck,shoulder_z)
    finish(d)
    if world:
        for fi,slot in enumerate(oldslots):
            if int(slot)%5 in (3,4):d['normals'][fi]=source['normals'][fi]
    file=R/'Authored/ue_field_sweater'/(profile+'.json');write(file,d)
    print('RANGER_AUTHORED',profile,len(d['positions']),len(d['triangles']),flush=True)
    return dict(**row,authored=str(file),triangles=len(d['triangles']),vertices=len(d['positions']))
def body_details(d,source,values,sides,neck,shoulder_z):
    p=np.array(source['positions']);f=np.array(source['triangles']);old=np.array(source['triangle_materials'])
    cloth=np.unique(f[(old%5)==0]);near=cloth[(p[cloth,2]>shoulder_z-7)&(abs(p[cloth,0]-neck[0])<20)]
    angle=np.arctan2(p[near,0]-neck[0],p[near,1]-neck[1]);rad=np.linalg.norm(p[near,:2]-neck[:2],axis=1)
    ring=[];ws=[]
    for theta in np.linspace(0,math.tau,96,endpoint=False):
        delta=abs(np.angle(np.exp(1j*(angle-theta))));pick=np.flatnonzero(delta<.12)
        if not len(pick):pick=np.argsort(delta)[:8]
        index=pick[np.argmin(rad[pick])];vi=near[index];ring.append(p[vi]);ws.append(source['weights'][vi])
    ring=np.array(ring)
    for _ in range(3):ring=.5*ring+.25*np.roll(ring,1,0)+.25*np.roll(ring,-1,0)
    # Bridge the old broad crew neckline into the fitted standing collar.
    rings=[];rw=[];rn=[]
    for j in range(9):
        t=j/8;row=[]
        for i,theta in enumerate(np.linspace(0,math.tau,96,endpoint=False)):
            r=ring[i].copy();r[:2]+=unit(np.r_[r[:2]-neck[:2],0])[:2]*.45;r[2]-=.18
            target=neck+np.array([6.0*math.sin(theta),5.3*math.cos(theta),-.65])
            pos=r*(1-t)+target*t
            row.append(pos);rw.append(blend_weights(ws[i],{'spine_05':.6,'neck_01':.4} if 'spine_05' in d['bones'] else {'spine_03':.6,'neck_01':.4},float(t)))
        rings.append(row)
    for j in range(1,5):
        rings.append([neck+np.array([(6.-.10*j/4)*math.sin(t),(5.3-.10*j/4)*math.cos(t),-.65+j*.68]) for t in np.linspace(0,math.tau,96,endpoint=False)])
        rw.extend([blend_weights({'spine_05':1} if 'spine_05' in d['bones'] else {'spine_03':1},{'neck_01':1},.4+.12*j)]*96)
    pp=np.array(rings).reshape(-1,3);ff=[];uv=[]
    for j in range(len(rings)-1):
        for i in range(96):
            ids=[j*96+i,j*96+(i+1)%96,(j+1)*96+(i+1)%96,(j+1)*96+i]
            for tri in ((0,1,2),(0,2,3)):
                faceids=[ids[k] for k in tri]
                out=unit(pp[faceids].mean(0)-np.r_[neck[:2],neck[2]-10])
                if np.cross(pp[faceids[1]]-pp[faceids[0]],pp[faceids[2]]-pp[faceids[0]])@out>0:faceids=faceids[::-1]
                ff.append(faceids);uv.append([[((vi%96) if i!=95 or vi%96 else 96)*math.tau*6/96/8,(vi//96)*1.0/8] for vi in faceids])
    from geometry import normals
    ns=normals(pp,ff);top_ids,_=append_shell(d,pp,ff,rw,ns,uv,1,.03,.15)
    for j in (0,len(rings)-1):
        path=[np.array(d['positions'][top_ids[j*96+i]])+ns[j*96+i]*.02 for i in range(96)]
        tube(d,path,.025,4,lambda x,j=j:rw[j*96+int(np.argmin(np.linalg.norm(np.array(path)-x,axis=1)))],closed=True,sides=5)
    button(d,neck+np.array([1.5,5.37,.8]),np.array([0,1,0]),{'neck_01':.7,'spine_03':.3})
    # Surface-projected front closure and narrow inset-pocket welts.
    chosen=[i for i,tri in enumerate(f) if old[i]%5==0 and np.mean(source['normals'][i],0)[1]>.15 and abs(p[tri,0].mean())<23]
    tree=BVHTree.FromPolygons([Vector(x) for x in p],f[chosen].tolist(),all_triangles=True)
    def project(x,z):
        hit,n,idx,dist=tree.ray_cast(Vector((x,50,z)),Vector((0,-1,0)),100)
        if hit is None:raise RuntimeError('Front tailoring projection missed '+d['profile']+' '+str((x,z)))
        tri=f[chosen[idx]];bc=bary(np.array(hit),p[tri]);w=norm_weights({n:sum(source['weights'][int(v)].get(n,0)*a for v,a in zip(tri,bc)) for n in set().union(*(source['weights'][int(v)] for v in tri))})
        return np.array(hit),unit(np.array([0,1,0])),w
    center=cloth[(abs(p[cloth,0]-neck[0])<3)&(p[cloth,1]>neck[1]+3)]
    hem=float(p[center,2].min())+1.2;top=float(ring[:12,2].mean())-1
    def strip(path,width,mat):
        points=[];normals=[];weights=[];ff=[];uv=[]
        for i,(x,z) in enumerate(path):
            for sign in (-1,1):
                v,n,w=project(x+sign*width*.5,z);points.append(v);normals.append(n);weights.append(w)
        for i in range(len(path)-1):
            ids=[i*2,i*2+1,i*2+3,i*2+2]
            for tri in ((0,1,2),(0,2,3)):ff.append([ids[k] for k in tri]);uv.append([[width*(k%2)/8,i*.6/8] for k in tri])
        ids,_=append_shell(d,points,ff,weights,normals,uv,mat,.05,.12)
        for side in (0,1):
            line=[np.array(d['positions'][ids[i*2+side]])+np.array([0,.035,0]) for i in range(len(path))]
            tube(d,line,.022,4,lambda x:weights[int(np.argmin(np.linalg.norm(np.array(points)-x,axis=1)))],sides=4)
    strip([(float(neck[0]),float(z)) for z in np.linspace(hem,top,max(12,int((top-hem)/.7)))],2.4,0)
    for sign in (-1,1):
        strip([(float(neck[0]+sign*(10+3*t)),float(hem+8+10*t)) for t in np.linspace(0,1,24)],.75,1)
if __name__=='__main__':
    manifest=read(R/'inputs.json');records=[]
    for row in manifest['rows']:
        records.append(build(row));gc.collect()
        write(R/'authored.json',dict(completed=len(records)==len(manifest['rows']),records=records,runtime_tested=False))
