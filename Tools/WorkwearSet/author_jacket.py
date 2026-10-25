"""Sewn jacket construction on native garment bindings and measured trouser waists."""
import copy,gc,math,sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import author_tailored_finish as tailored
import repair_collar as r
from geometry import unit,smooth,norm_weights,blend_weights,vertex,face,tube
r.R=R;r.ITEM=KEY;r.a.SLOTS=['WorkCanvas','WorkLeather','WorkLining','WorkBrass','WorkBlueThread','ExposedTorsoSkin']
base_shell=r.shell
def shell(d,points,faces,weights,ns,uvs,slot,offset=.025,thickness=.12):
    first=len(d['triangles'])
    if len(points)==128*61 and slot==1:
        ids,edges=tailored.refined_shell(d,points,faces,weights,ns,uvs,slot,offset,thickness)
        neck=np.array(d['bones']['neck_01']['position']);shoulder=np.mean([d['bones']['upperarm_'+s]['position'][2] for s in ('l','r')])
        for fi in range(first,len(d['triangles'])):
            if d['triangle_materials'][fi]!=1:continue
            q=np.mean([d['positions'][i] for i in d['triangles'][fi]],0)
            # The design has small leather shoulder yokes, a CLOTH collar and upper chest.
            if abs(q[0]-neck[0])<8.6 or q[2]>shoulder+3.5:d['triangle_materials'][fi]=0
        return ids,edges
    return base_shell(d,points,faces,weights,ns,uvs,slot,offset,thickness)
r.shell=shell
original_clip=r.clip_patch
def clip(d,indices,field,slot=1):
    if field.__name__=='forearm':
        def elbow_and_cuff(p,w):
            side=r.a.arm_side(w)
            if side is None:return -50.
            e=np.array(d['bones']['lowerarm_'+side]['position']);hand=np.array(d['bones']['hand_'+side]['position']);axis=unit(hand-e);t=(p-e)@axis;prox=-(p-hand)@axis
            seed=unit(np.array(d['bones']['lowerarm_'+side]['axes'][2]));rad=unit(p-e-axis*t)
            return max(3.1-prox,min(t+4.5,7.-t,(rad@seed-.1)*7))
        return original_clip(d,indices,elbow_and_cuff,slot)
    return original_clip(d,indices,field,slot)
r.clip_patch=clip
def details(d,outer_faces,base_z):
    ps=np.array(d['positions']);fs=np.array(d['triangles']);neck=np.array(d['bones']['neck_01']['position']);cx=neck[0]
    selected=[i for i in outer_faces if abs(ps[fs[i],0].mean()-cx)<25];tris=fs[selected]
    tree=BVHTree.FromPolygons([Vector(p) for p in ps],tris.tolist(),all_triangles=True);ns=r.shared_normals(ps,tris)
    def project(x,z,front=True):
        sign=1 if front else -1;hit,_,fi,_=tree.ray_cast(Vector((x,sign*55,z)),Vector((0,-sign,0)),110)
        if hit is None:raise RuntimeError('Jacket panel outside native torso '+str((x,z)))
        tri=tris[fi];b=r.a.bary(np.array(hit),ps[tri]);names=set().union(*(d['weights'][i] for i in tri));w=norm_weights({n:sum(d['weights'][i].get(n,0)*v for i,v in zip(tri,b)) for n in names});normal=unit(b@ns[tri])
        if normal[1]*sign<0:normal=-normal
        return np.array(hit),normal,w
    def patch(fn,slot=0,raised=.08,bulge=.0,front=True,nu=22,nv=22,stitch=True):
        pp=[];nn=[];ww=[];ff=[];uv=[]
        for v in np.linspace(0,1,nv):
            for u in np.linspace(0,1,nu):
                x,z=fn(u,v);p,n,w=project(x,z,front);q=p+n*(raised+bulge*math.sin(math.pi*u)*math.sin(math.pi*v));pp.append(q);nn.append(n);ww.append(w)
        for j in range(nv-1):
            for i in range(nu-1):
                ids=[j*nu+i,j*nu+i+1,(j+1)*nu+i+1,(j+1)*nu+i]
                for t in ((0,1,2),(0,2,3)):
                    order=[ids[k] for k in t];normal=np.mean([nn[k] for k in order],0);q=np.array([pp[k] for k in order])
                    if np.cross(q[1]-q[0],q[2]-q[0])@normal>0:order.reverse()
                    ff.append(order);uv.append([[pp[k][0]/8,pp[k][2]/8] for k in order])
        ids,_=base_shell(d,pp,ff,ww,nn,uv,slot,.025,.10)
        if stitch:
            ring=list(range(1,nu-1))+[j*nu+nu-2 for j in range(1,nv-1)]+list(range((nv-2)*nu+nu-2,(nv-2)*nu,-1))+[j*nu+1 for j in range(nv-2,0,-1)]
            tailored.seam(d,[d['positions'][ids[k]] for k in ring],[ww[k] for k in ring],[nn[k] for k in ring],pitch=.30,length=.19,radius=.018)
        return ids
    # Continuous cloth storm flap with actual width, lining and snap lips.
    low=94.8 if d['profile']=='Jason' else 99.8
    patch(lambda u,v:(cx+(u-.5)*2.45,low+(base_z+2.25-low)*v),0,.16,.03,nu=9,nv=112)
    for z in np.arange(low+2,base_z+2,7.7):
        p,n,w=project(cx,z);r.a.button(d,p+n*.38,n,w,radius=.29)
    chest=base_z-17
    for sign in (-1,1):
        x0=cx+sign*9.0
        # Patch pocket with a gusseted central fold and independently thick flap.
        patch(lambda u,v,x0=x0:(x0+(u-.5)*10.0,chest-6.0+10.5*v),0,.16,.60)
        patch(lambda u,v,x0=x0:(x0+(u-.5)*10.4,chest+2.1+3.6*v-.75*(1-v)*(1-abs(2*u-1))),0,.83,.08,nu=24,nv=10)
        p,n,w=project(x0,chest+3.35);r.a.button(d,p+n*1.05,n,w,radius=.28)
        patch(lambda u,v,x0=x0:(x0+(u-.5)*.38,chest-5.5+7.1*v),0,.38,.36,nu=4,nv=20)
        # Angled hand pockets, deep lining and rolled entry welts.
        def opening(u,v,sign=sign):return (cx+sign*(9.4+3.1*v)+(u-.5)*1.1,low+10.5+10.0*v)
        patch(opening,2,.08,.02,nu=6,nv=28,stitch=False)
        patch(lambda u,v,sign=sign:(cx+sign*(9.4+3.1*v)+(u-.5)*.65,low+10.5+10*v),1,.24,.02,nu=6,nv=28)
        # Functional back action pleats, collapsed towards the waist.
        patch(lambda u,v,sign=sign:(cx+sign*(8.0+1.8*v)+(u-.5)*1.7,low+8+(base_z-low-13)*v),0,.05,.27,False,nu=9,nv=50)
        # Short horizontal waist adjustment straps and brass closure.
        patch(lambda u,v,sign=sign:(cx+sign*(11.8+3.3*u),low+.6+1.65*v),1,.25,.03,nu=18,nv=5)
        p,n,w=project(cx+sign*14.5,low+1.4);r.a.button(d,p+n*.47,n,w,radius=.30)
    d['workwear_details']='4 pockets, articulated elbow patches, cloth collar, leather shoulder yokes, blue curved stitches, brass snaps, back movement pleats, waist tabs'
r.details=details

def crop(d,cut):
    out={k:copy.deepcopy(v) for k,v in d.items() if k not in ('positions','weights','triangles','uv','normals','triangle_materials','colors')}
    for k in ('positions','weights','triangles','uv','normals','triangle_materials'):out[k]=[]
    p=np.array(d['positions']);lookup={}
    for fi,tri in enumerate(d['triangles']):
        vals=p[tri,2]-cut
        if d['triangle_materials'][fi]==5:vals=np.ones(3)
        poly=[]
        for a,b in zip(np.eye(3),np.roll(np.eye(3),-1,axis=0)):
            va=a@vals;vb=b@vals
            if va>=0:poly.append(a)
            if (va>=0)!=(vb>=0):poly.append(a+va/(va-vb)*(b-a))
        for j in range(1,len(poly)-1):
            ids=[];uv=[];nn=[]
            for b in (poly[0],poly[j],poly[j+1]):
                q=b@p[tri];w=norm_weights({n:sum(d['weights'][i].get(n,0)*a for i,a in zip(tri,b)) for n in set().union(*(d['weights'][i] for i in tri))})
                # Native skin sections can share positions while remaining
                # separate topology. Only merge the same original vertex/edge.
                origin=tuple(sorted((int(v),round(float(a),8)) for v,a in zip(tri,b) if a>1e-8))
                key=(origin,*np.round(q,7),tuple(sorted((n,round(v,7)) for n,v in w.items())))
                if key not in lookup:lookup[key]=vertex(out,q,w)
                ids.append(lookup[key]);uv.append((b@np.array(d['uv'][fi])).tolist());nn.append(unit(b@np.array(d['normals'][fi])).tolist())
            if len(set(ids))==3:out['triangles'].append(ids);out['uv'].append(uv);out['normals'].append(nn);out['triangle_materials'].append(d['triangle_materials'][fi])
    return out

def fit_waist(d,group):
    pants=read(group['guide']);pp=np.array(pants['positions']);pf=np.array(pants['triangles'][:pants.get('outer_shell_triangles',len(pants['triangles']))]);tree=BVHTree.FromPolygons([Vector(p) for p in pp],pf.tolist(),all_triangles=True)
    top=group['waist_top_cm'];cut=top-3.4
    source=copy.deepcopy(d);sp=np.array(source['positions']);shift=top-96.511
    for i,q in enumerate(sp):
        if q[2]<115 and r.a.arm_side(source['weights'][i]) is None:q[2]+=shift*(1-float(smooth((q[2]-103)/12)))
    source['positions']=sp.tolist();out=crop(source,cut);p=np.array(out['positions']);f=np.array(out['triangles']);edited=np.zeros(len(p),bool)
    outer=f[np.array(out['triangle_materials'])==0];outertree=BVHTree.FromPolygons([Vector(q) for q in p],outer.tolist(),all_triangles=True)
    # All visible hem layers follow the same measured outer envelope. Their
    # separation is retained; the hidden tucked extension is authored separately.
    center=np.array([0.,.8,0.]);cache={}
    def sample(q):
        direction=unit(np.r_[q[:2]-center[:2],0]);angle=round(math.atan2(direction[1],direction[0]),3);z=min(float(q[2]),top-.12);key=(angle,round(z,2))
        if key in cache:return cache[key]
        origin=np.array([0.,.8,z]);hit,_,fi,_=tree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
        if hit is None:
            origin[2]=top-1.;hit,_,fi,_=tree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
        if hit is None:raise RuntimeError('Missing waistband surface '+str(q))
        hit=np.array(hit);tri=pf[fi];bc=r.a.bary(hit,pp[tri]);w=norm_weights({n:sum(pants['weights'][v].get(n,0)*a for v,a in zip(tri,bc)) for n in set().union(*(pants['weights'][v] for v in tri))});value=(hit,direction,w);cache[key]=value;return value
    cloth=np.unique(f[np.isin(out['triangle_materials'],[0,1,2,3,4])])
    for i in cloth:
        q=p[i]
        if q[2]>top+9 or sum(w for n,w in out['weights'][i].items() if any(x in n for x in ('arm','hand','thumb','index','middle','ring','pinky')))>.3:continue
        hit,direction,w=sample(q);radius=np.linalg.norm(q[:2]-center[:2]);target=np.linalg.norm(hit[:2]-center[:2])+.65
        origin=np.array([0.,.8,q[2]]);anchor,_,_,_=outertree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
        base_radius=np.linalg.norm(np.array(anchor)[:2]-center[:2]) if anchor is not None else radius
        fade=1-float(smooth((q[2]-top-.3)/8.5));p[i]+=direction*(target-base_radius)*fade
        out['weights'][i]=blend_weights(out['weights'][i],w,1-float(smooth((q[2]-top+1.5)/8.5)));edited[i]=True
    out['positions']=p.tolist()
    # Rolled outer hem and a separate hidden cloth extension inside the trousers.
    path=[];ww=[]
    for a in np.linspace(0,math.tau,144,endpoint=False):
        q=np.array([math.cos(a)*18,.8+math.sin(a)*14,cut+.13]);hit,direction,w=sample(q);path.append(np.r_[hit[:2]+direction[:2]*.69,cut+.13]);ww.append(w)
    tube(out,path,.11,0,lambda q:ww[int(np.argmin(np.linalg.norm(np.array(path)-q,axis=1)))],closed=True,sides=6)
    rings=[];rw=[]
    for z in (top-1.9,top-.7,top+.5,top+1.7):
        row=[]
        for a in np.linspace(0,math.tau,144,endpoint=False):
            q=np.array([math.cos(a)*18,.8+math.sin(a)*14,z]);hit,direction,w=sample(q);row.append(vertex(out,np.r_[hit[:2]-direction[:2]*.45,z],w));rw.append(w)
        rings.append(row)
    for row in range(3):
        for i in range(144):
            j=(i+1)%144;ids=[rings[row][i],rings[row][j],rings[row+1][j],rings[row+1][i]]
            for t in ((0,1,2),(0,2,3)):
                v=[ids[k] for k in t];q=np.array([out['positions'][k] for k in v]);n=unit(np.r_[q.mean(0)[:2]-center[:2],0]);face(out,v,2,[[i/16,row*.15],[(i+1)/16,row*.15],[(i+1)/16,(row+1)*.15]],n)
    r.a.finish(out);out['contract']='Workwear outer jacket: physical pocket and seam construction; native skin binding; measured outer waist overlap plus tucked inner extension; native arm motion'
    out['waist_fit']=dict(mode='outer_jacket_with_inner_tuck',guide=group['guide'],guide_sha256=sha(group['guide']),top_cm=top,outer_overlap_cm=3.4,outer_clearance_cm=.65,inner_clearance_cm=.45)
    return out

def main():
    if '--body-only' in sys.argv:
        manifest=read(R/'authored.json');manifest['completed']=False;write(R/'authored.json',manifest)
        d=r.body('Body');d=crop(d,99.8);d['profile']='Body';r.a.finish(d);compact(R/'Authored'/KEY/'Body.json',d)
        manifest['completed']=True;write(R/'authored.json',manifest);print('WORK_JACKET_BODY_TOPOLOGY_REPAIRED',flush=True);return
    inputs=read(R/'inputs.json');records=[]
    d=r.body('Jason');compact(R/'Inputs/Jason_LongAuthor.json',d)
    for name,group in inputs['groups'].items():
        out=fit_waist(d,group);profile='Jason_'+name;out['profile']=profile;file=R/'Authored'/KEY/(profile+'.json');compact(file,out)
        records.append(dict(profile=profile,file=str(file),rig='Jason',group=name,item=KEY))
        # Preserve native owner arm hiding at the exact weight boundary.
        old_write=r.write;r.write=lambda path,data:compact(R/'Authored'/KEY/('Owner_'+profile+'.json'),data)
        r.owner(out);r.write=old_write
        owner=read(R/'Authored'/KEY/('Owner_'+profile+'.json'));owner['profile']='Owner_'+profile;compact(R/'Authored'/KEY/(owner['profile']+'.json'),owner)
        records.append(dict(profile=owner['profile'],file=str(R/'Authored'/KEY/(owner['profile']+'.json')),rig='Jason',group=name,item=KEY,owner=True))
        print('WORK_JACKET_WAIST_AUTHORED',profile,len(out['triangles']),flush=True);del out,owner;gc.collect()
    # No-trousers appearance uses the cargo envelope without hiding extra body sections.
    cargo=next(g for g,x in inputs['groups'].items() if 'ue_cargo_pants' in x['items']);write(R/'authored.json',dict(completed=False,records=records,default_group=cargo,runtime_tested=False))
    d=r.body('Body');d=crop(d,99.8);d['profile']='Body';r.a.finish(d);compact(R/'Authored'/KEY/'Body.json',d);records.append(dict(profile='Body',file=str(R/'Authored'/KEY/'Body.json'),rig='Body',item=KEY))
    write(R/'authored.json',dict(completed=True,records=records,default_group=cargo,runtime_tested=False));print('WORK_JACKET_BODY_AUTHORED',len(records),flush=True)
if __name__=='__main__':main()
