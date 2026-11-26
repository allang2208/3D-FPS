"""Concept03 production: continuous cut panels, authored drape and open pockets.

Blender background authoring. The folds are sculpted analytic surface fields,
not a cloth simulation. No rendering, validation or UE asset mutation.
"""
import copy, gc, json, math, sys
from pathlib import Path
import bpy
import numpy as np

P = Path('D:/FPS3D/FPSGAME')
BASE = P / 'SourceAssets/RangerLeatherPants20261021'
R = BASE / 'RealisticCutV3'
sys.path.insert(0, str(P / 'Tools/RangerLeatherPants'))
import author as lib
from refine_geometry import RefinedTailor
from author import unit, smooth, normals, norm_weights, blend_weights, boundary, read, write


def coordinates(p):
    p = np.asarray(p); x, y, z = p.T
    s = np.where(x >= 0, 1., -1.)
    cx = s*np.interp(z, [11.8,20,30,40,47.35,58,67,80], [14.8,14.2,13.5,12.6,12.04,11.2,10.5,9.8])
    cy = np.interp(z, [11.8,20,30,40,47.35,58,67,80], [-2.5,-2,-1.2,-.4,.8,1.7,2.3,2.6])
    t = np.arctan2(s*(x-cx), y-cy)
    return s, cx, cy, t, z


def pattern_fields(p):
    p = np.asarray(p); s,cx,cy,t,z = coordinates(p)
    back = np.arctan2(np.sin(t-math.pi), np.cos(t-math.pi))
    inner = np.arctan2(np.sin(t+math.pi/2), np.cos(t+math.pi/2))
    # Broad angular flex panel wrapping behind the knee, not an oval sticker.
    back_top = 54.2 + 1.0*np.cos(back)
    back_bottom = 39.6 + 3.0*(np.abs(back)/1.20)**1.4
    knee_cloth = np.minimum.reduce([back_top-z, z-back_bottom, (1.20-np.abs(back))*8])
    gusset_width = .22 + .16*smooth((z-60)/19)
    gusset = np.minimum.reduce([(gusset_width-np.abs(inner))*8, z-60.0, 82.8-z])
    cloth = np.maximum(knee_cloth, gusset)
    upper = 54.6 + 1.1*np.cos(t)
    lower = 39.4 + 3.5*(np.abs(t)/1.36)**1.6
    knee = np.minimum.reduce([upper-z, z-lower, (1.36-np.abs(t))*8])
    # A single continuous yoke follows the rear waist and joins the side seams.
    yoke_z = 91.4 + 1.8*(np.abs(p[:,0])/17.8)**1.6
    yoke = np.minimum.reduce([z-yoke_z, -p[:,1]-.1, 96.1-z])
    return cloth, np.maximum(knee, yoke)


def pocket_field(p, rear=False):
    p=np.asarray(p); x=np.abs(p[:,0]); y=p[:,1]; z=p[:,2]
    a=np.array([4.6,91.0]) if rear else np.array([7.0,95.35])
    b=np.array([12.4,90.6]) if rear else np.array([14.8,85.6])
    vec=b-a; length=np.linalg.norm(vec); tangent=vec/length; across=np.array([-tangent[1],tangent[0]])
    q=np.c_[x,z]-a; u=(q@tangent)/length
    half=(.25 if rear else .12)+(.03 if rear else .68)*np.sin(np.pi*np.clip(u,0,1))
    side=(-y-4.) if rear else y-5.
    return np.minimum.reduce([u*length,(1-u)*length,half-np.abs(q@across),side])


def curve_field(q, controls, amp, width, bias=0.):
    """A tapered, asymmetric ridge/valley along a cubic garment crease."""
    c=np.array(controls,float); u=np.linspace(0,1,25)
    path=(1-u[:,None])**3*c[0]+3*(1-u[:,None])**2*u[:,None]*c[1]+3*(1-u[:,None])*u[:,None]**2*c[2]+u[:,None]**3*c[3]
    distance=np.full(len(q),1e20); signed=np.zeros(len(q)); along=np.zeros(len(q))
    for i,(a,b) in enumerate(zip(path[:-1],path[1:])):
        v=b-a; w=q-a; f=np.clip((w@v)/(v@v),0,1); delta=w-f[:,None]*v
        d=(delta*delta).sum(1); use=d<distance
        distance[use]=d[use]; signed[use]=np.sign(v[0]*delta[use,1]-v[1]*delta[use,0])*np.sqrt(d[use]); along[use]=(i+f[use])/24
    strength=np.sin(np.pi*along)**.65
    wid=width*(.60+.45*np.sin(np.pi*along))
    a=(signed-bias)/wid
    return amp*strength*(np.exp(-a*a)-.46*np.exp(-((a+1.15)/.72)**2))


def sculpt(ps,fs):
    s,cx,cy,t,z=coordinates(ps)
    # Tailored straight drape: reduce muscular bulges, allow knee ease, keep the
    # native waist and crotch junction. It is intentionally not a tight body cast.
    rx=np.interp(z,[12,18,28,38,47,58,67,76],[5.15,5.35,5.95,6.4,6.8,7.9,8.65,8.9])
    ry=np.interp(z,[12,18,28,38,47,58,67,76],[6.2,6.35,7.15,7.9,8.7,9.5,10.1,11.2])
    factor=.66*(1-smooth((z-67)/10))
    ps[:,0]=ps[:,0]*(1-factor)+(cx+s*rx*np.sin(t))*factor
    ps[:,1]=ps[:,1]*(1-factor)+(cy+ry*np.cos(t))*factor
    ns=normals(ps,fs); displacement=np.zeros(len(ps))
    # Controls are (angle * 8 cm, height cm); non-identical left/right tailoring
    # remains anatomically symmetric but avoids mirrored wrinkles.
    front_curves=[
        ([( -8,87),(-4,84.6),(3,83.2),(9,85.2)], .45,.67),
        ([(-9,83.1),(-5,81.4),(0,79.4),(7.5,81.6)], .64,.74),
        ([(-10,79.6),(-4.5,77.8),(2.6,77),(8.7,78.9)], .38,.52),
        ([(-8,76.3),(-4,73.7),(1,72.4),(5.8,73.6)], .32,.66),
        ([(3,93.1),(5,89),(7.8,87.1),(11.8,85.8)], .26,.57),
        ([(10,82),(7.7,77),(4.2,73),(5.8,68)], .30,.76),
        ([(-7,69),(-4.8,65.9),(-5.4,60),(-2,57.2)], .24,.85),
        ([(-8.5,59.7),(-4,58.6),(1.8,57.4),(7.9,58.8)], .38,.56),
        ([(7.6,54.3),(3.1,52.7),(-.2,52.8),(-4.6,51)], .31,.58),
        ([(-8,47),(-4.2,45.3),(0,44.1),(4.8,46)], .42,.62),
        ([(7,43.8),(3.4,41.2),(-3.7,41.8),(-8.5,43.2)], .47,.71),
        ([(-7,37.4),(-3,36.9),(1.9,35.3),(7,37.1)], .29,.61),
        ([(5.1,36.0),(3.6,32),(4.9,28),(3.1,24)], .21,.91),
        ([(-7.5,25.6),(-3.1,23.8),(1.1,24.0),(7.5,25.7)], .44,.56),
        ([(8.2,22.9),(4.1,20.7),(-2.6,21.6),(-8.2,22.3)], .52,.60),
        ([(-8,19.7),(-4,18.0),(1.5,18.5),(6.5,20.1)], .49,.57),
        ([(5.6,17.3),(1,15.6),(-2.8,15.8),(-7.6,17.2)], .33,.46),
    ]
    rear_curves=[
        ([(-9,86.9),(-4,84.9),(2.5,84.5),(8,86.4)], .30,.78),
        ([(-10,82.9),(-4,79.9),(3.4,80.2),(10,82.6)], .57,.80),
        ([(-9,78.8),(-4,76.5),(2.6,77.2),(8,78.5)], .34,.61),
        ([(8,69),(4,65),(4.5,61),(1,58.4)], .25,.92),
        ([(-10,55),(-4,52.9),(2,53.4),(9,55.1)], .48,.64),
        ([(9,51.6),(3,49.1),(-3,50.1),(-9,51.4)], .61,.62),
        ([(-9,48.1),(-4,45.7),(3.5,46.5),(9.5,48.0)], .68,.70),
        ([(9,44.2),(4,42.1),(-3,43.2),(-8,43.7)], .48,.58),
        ([(-9,38.5),(-4,37.4),(3,38.1),(8,39.7)], .26,.72),
        ([(-6,30.3),(-4,26.6),(-2,23.7),(-4,20.2)], .25,.80),
        ([(-9,23.6),(-4,22.4),(2.9,21.2),(8,23.8)], .45,.55),
        ([(9,20.4),(3,18.8),(-2.9,19.5),(-9,20.1)], .48,.58),
        ([(-8,17.8),(-2,16.2),(3,16.4),(7,18)], .37,.48),
    ]
    for sign in (1,-1):
        ids=np.flatnonzero(s==sign); zz=z[ids]; tt=t[ids]
        local=np.zeros(len(ids))
        for back, curves in ((False,front_curves),(True,rear_curves)):
            aa=np.arctan2(np.sin(tt-(math.pi if back else 0)),np.cos(tt-(math.pi if back else 0)))
            q=np.c_[aa*8,zz]
            for k,(control,amp,width) in enumerate(curves):
                c=np.array(control,float); c[:,1]+=(.20 if sign<0 else -.14)*np.sin(np.arange(4)*.8+k*1.77)
                c[:,0]+=(.35 if sign<0 else -.2)*math.sin(k*1.3)
                local+=curve_field(q,c,amp*(.95 if sign<0 else 1.05),width)
        displacement[ids]=local
    # A stitched seam compresses the shell itself instead of floating above it.
    cloth,panel=pattern_fields(ps)
    displacement-=.048*np.exp(-(cloth/.17)**2)+.032*np.exp(-(panel/.20)**2)
    displacement*=smooth((z-13.7)/1.9)*(1-smooth((z-94.2)/1.5))
    # Small positive ease keeps valley bottoms out of the original body envelope.
    displacement+=.17*smooth((z-14)/4)*(1-smooth((z-93)/3))
    ps+=ns*displacement[:,None]
    return ps


def base():
    src=read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json')
    names={b['index']:b['name'] for b in src['bones']}; ps=[]; ws=[]; fs=[]; lookup={}; first=0
    for part in src['parts']:
        if part['name'] in ('Leather_WaistAndSeat','Leather_Leg_L','Leather_Leg_R'):
            for tri in src['triangles'][first:first+part['triangles']]:
                row=[]
                for i in tri:
                    p=src['positions'][i]; key=tuple(np.round(p,5))
                    if key not in lookup:lookup[key]=len(ps);ps.append(p);ws.append({names[b]:w for b,w in src['weights'][i]})
                    row.append(lookup[key])
                fs.append(row)
        first+=part['triangles']
    for level in range(2):
        edge={}; out=[]
        for a,b,c in fs:
            mids=[]
            for i,j in ((a,b),(b,c),(c,a)):
                key=tuple(sorted((i,j)))
                if key not in edge:edge[key]=len(ps);ps.append(((np.array(ps[i])+ps[j])*.5).tolist());ws.append(blend_weights(ws[i],ws[j],.5))
                mids.append(edge[key])
            ab,bc,ca=mids;out.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
        fs=out
    ps=np.array(ps); fs=np.array(fs)
    edges=np.unique(np.sort(np.concatenate((fs[:,[0,1]],fs[:,[1,2]],fs[:,[2,0]])),axis=1),axis=0)
    rows=np.r_[edges[:,0],edges[:,1]]; cols=np.r_[edges[:,1],edges[:,0]]; count=np.bincount(rows,minlength=len(ps))
    fixed=np.zeros(len(ps),bool)
    for a,b in boundary(fs):fixed[a]=fixed[b]=True
    weight=.42*(1-smooth((ps[:,2]-94)/5)); weight[fixed]=0
    def mean(v):
        result=np.zeros_like(v);np.add.at(result,rows,v[cols]);return result/np.maximum(count,1)[:,None]
    for _ in range(12):ps+=weight[:,None]*(mean(ps)-ps);ps-=.98*weight[:,None]*(mean(ps)-ps)
    ps=sculpt(ps,fs)
    print('REALISTIC_DRAPE_SCULPTED',len(ps),len(fs),flush=True)
    me=bpy.data.meshes.new('RealisticTailoringShell');me.from_pydata([(x,-y,z) for x,y,z in ps],[],fs.tolist());me.update()
    ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
    centroids=ps[fs].mean(1);sg,cx,cy,ta,zz=coordinates(centroids)
    groups=list(zip(np.where(zz>80,0,np.where(sg>0,1,2)),centroids[:,1]>np.where(zz>80,.8,cy)))
    eg={}
    for tri,group in zip(fs,groups):
        for a,b in zip(tri,np.roll(tri,-1)):eg.setdefault(tuple(sorted((int(a),int(b)))),set()).add(group)
    for e in me.edges:e.use_seam=len(eg[tuple(sorted(e.vertices))])>1
    me.uv_layers.new(name='Physical8cm');bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.unwrap(method='ANGLE_BASED',margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
    layer=me.uv_layers.active;uv=np.array([[[layer.data[i].uv.x,1-layer.data[i].uv.y] for i in f.loop_indices] for f in me.polygons])
    sys.path.insert(0,str(P/'Tools/ModularOutfit'));from author_chainmail_shirt import mail_uv
    uv,_=mail_uv(ps,fs,uv);uv=np.array(uv)*25/8
    bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(me)
    return src,ps,fs,ws,uv


class RealisticTailor(RefinedTailor):
    def stitches(self,name,samples,closed=False,pitch=.34):
        # 0.28 mm thread diameter, 2.1 mm visible stitch, 3.4 mm pitch.
        p=np.array([s[0] for s in samples]);n=np.array([s[1] for s in samples]);w=[s[2] for s in samples]
        if closed:p=np.r_[p,p[:1]];n=np.r_[n,n[:1]];w=w+w[:1]
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        for k,distance in enumerate(np.arange(pitch*.5,arc[-1]-.10,pitch)):
            pp=[];ww=[];length=min(.21,pitch*.68)
            for a in (0.,.32,.68,1.):
                at=distance+(a-.5)*length;i=min(len(p)-2,max(0,np.searchsorted(arc,at)-1));f=(at-arc[i])/max(arc[i+1]-arc[i],1e-8)
                normal=unit(n[i]*(1-f)+n[i+1]*f);pp.append(p[i]*(1-f)+p[i+1]*f+normal*(-.012+.029*math.sin(math.pi*a)));ww.append(blend_weights(w[i],w[i+1],f))
            self.tube(name+'_'+str(k),pp,ww,.014,4,sides=4)

    def shell(self):
        fields=np.array(pattern_fields(self.ps)); holes=np.maximum(pocket_field(self.ps),pocket_field(self.ps,True))
        ps=[];ns=[];ws=[];fs=[];uv=[];slots=[];lookup={}
        def clip(poly,vals,positive):
            result=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                va=a@vals;vb=b@vals;ia=va>=0 if positive else va<=0;ib=vb>=0 if positive else vb<=0
                if ia:result.append(a)
                if ia!=ib:result.append(a+va/(va-vb)*(b-a))
            return result
        def put(bc,tri):
            p=bc@self.ps[tri];key=tuple(np.round(p,7))
            if key not in lookup:
                lookup[key]=len(ps);ps.append(p);ns.append(unit(bc@self.ns[tri]))
                ws.append(norm_weights({k:sum(self.ws[v].get(k,0)*a for v,a in zip(tri,bc)) for k in set().union(*(self.ws[v] for v in tri))}))
            return lookup[key]
        for fi,tri in enumerate(self.fs):
            poly=clip(list(np.eye(3)),holes[tri],False)
            if len(poly)<3:continue
            cloth=clip(poly,fields[0,tri],True);leather=clip(poly,fields[0,tri],False)
            polygons=[(cloth,2),(clip(leather,fields[1,tri],True),1),(clip(leather,fields[1,tri],False),0)]
            for poly,slot in polygons:
                for j in range(1,len(poly)-1):
                    bc=[poly[0],poly[j],poly[j+1]];ids=[put(b,tri) for b in bc]
                    if len(set(ids))==3:fs.append(ids);uv.append([b@self.uv[fi] for b in bc]);slots.append(slot)
        ps=np.array(ps);ns=np.array(ns);fs=np.array(fs);uv=np.array(uv);N=len(ps)
        paired=np.vstack((ps,ps-ns*.115)); faces=np.vstack((fs,fs[:,::-1]+N))
        self.append('ContinuousCutPanelsAndLining',paired,faces,ws+copy.deepcopy(ws),np.concatenate((uv,uv[:,::-1])),slots+[3]*len(fs),np.concatenate((ns[fs],-ns[fs[:,::-1]])))
        self.outer_count=len(fs); self.outer_vertices=N
        for a,b in boundary(fs):
            pp=paired[[b,a,a+N,b+N]];ff=[[0,1,2],[0,2,3]];l=np.linalg.norm(ps[a]-ps[b])/8;tt=np.array([[0,0],[l,0],[l,.115/8],[0,.115/8]])
            self.append('TurnedCutEdge',pp,ff,[ws[b],ws[a],ws[a],ws[b]],tt[ff],1)
        # Pocket cavities are made from their actual clipped boundary, including
        # an interior back and wall. No black decals standing in for openings.
        for rear in (False,True):
            for sign in (1,-1):
                ring_edges=[(a,b) for a,b in boundary(fs) if ps[[a,b],0].mean()*sign>0 and 83<ps[[a,b],2].mean()<96 and ((ps[[a,b],1].mean()<-4) if rear else (ps[[a,b],1].mean()>5))]
                adj={}
                for a,b in ring_edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
                if not adj:continue
                start=next(iter(adj));ring=[start];prev=None;cur=start
                while True:
                    nxt=next((v for v in adj[cur] if v!=prev),None)
                    if nxt is None or nxt==start or nxt in ring:break
                    ring.append(nxt);prev,cur=cur,nxt
                if len(ring)<3:continue
                idx=np.array(ring);edge=ps[idx];norm=ns[idx];mid=edge.mean(0);nn=unit(norm.mean(0));depth=.56 if rear else .82
                # The bag widens behind the mouth and terminates in a closed back.
                back=edge-norm*depth+(edge-mid)*.12
                vertices=np.vstack((edge-norm*.10,back,[back.mean(0)]));ww=[ws[i] for i in idx]*2+[norm_weights({k:sum(ws[i].get(k,0) for i in idx)/len(idx) for k in set().union(*(ws[i] for i in idx))})]
                faces=[];tex=[];mats=[];N=len(idx)
                for j in range(N):
                    nxt=(j+1)%N
                    for f,slot in (([j,nxt,nxt+N],3),([j,nxt+N,j+N],3),([2*N,j+N,nxt+N],2 if not rear else 3)):
                        q=vertices[f]
                        expected=nn if f[0]==2*N else unit((mid-q.mean(0))-nn*((mid-q.mean(0))@nn))
                        if np.cross(q[1]-q[0],q[2]-q[0])@expected>0:f=f[::-1]
                        faces.append(f);tex.append((vertices[f][:,[0,2]]/8).tolist());mats.append(slot)
                self.append(('Rear' if rear else 'Front')+'PocketCavity_'+str(sign),vertices,faces,ww,tex,mats)
        print('REALISTIC_CUT_SHELL_SAVED_IN_MEMORY',self.outer_count,flush=True)

    def construction_seams(self):
        d=self.d;faces=np.array(d['triangles'][:self.outer_count]);slots=np.array(d['triangle_materials'][:self.outer_count]);ps=np.array(d['positions']);ns=normals(ps,faces);edges={}
        for f,slot in zip(faces,slots):
            for a,b in zip(f,np.roll(f,-1)):edges.setdefault(tuple(sorted((int(a),int(b)))),set()).add(int(slot))
        selected={e for e,v in edges.items() if len(v)>1};adj={}
        for a,b in selected:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
        while selected:
            a,b=next(iter(selected));path=[a,b];selected.remove(tuple(sorted((a,b))))
            for reverse in (False,True):
                if reverse:path.reverse()
                while True:
                    cur=path[-1];nxt=next((v for v in adj[cur] if tuple(sorted((cur,v))) in selected),None)
                    if nxt is None:break
                    selected.remove(tuple(sorted((cur,nxt))));path.append(nxt)
                    if nxt==path[0]:break
            closed=path[0]==path[-1]
            if closed:path.pop()
            if len(path)<3:continue
            for offset in (-.16,.16):
                samples=[]
                for j,i in enumerate(path):
                    tangent=unit(ps[path[min(j+1,len(path)-1)]]-ps[path[max(j-1,0)]])
                    target=ps[i]+unit(np.cross(ns[i],tangent))*offset
                    hit,_,fi,_=self.tree.find_nearest(tuple(target));tri=self.fs[fi];bc=lib.bary(np.array(hit),self.ps[tri]);normal=unit(bc@self.ns[tri]);weight=norm_weights({k:sum(self.ws[v].get(k,0)*q for v,q in zip(tri,bc)) for k in set().union(*(self.ws[v] for v in tri))})
                    samples.append((np.array(hit)+normal*.016,normal,weight))
                self.stitches('IntegratedPanelTopstitch',samples,closed)


def details(t):
    t.band('CurvedWaistband',lambda u,v:t.waist(u*math.tau,96.12+3.82*v),152,8,.105,0,closed=True)
    t.band('SuppleLeatherBelt',lambda u,v:t.waist(.045+u*(math.tau-.09),97.13+2.20*v),160,6,.24)
    for k,theta in enumerate((.32,1.22,2.12,math.pi,4.16,5.06,5.96)):
        t.band('SewnBeltLoop_'+str(k),lambda u,v,theta=theta:t.waist(theta+(u-.5)*.077,96.17+3.65*v),6,14,.40,0,stitch=False)
        for v in (.07,.93):
            samples=[]
            for u in np.linspace(0,1,12):
                p,n,w=t.waist(theta+(u-.5)*.077,96.17+3.65*v);samples.append((p+n*(.135+.245*math.sin(math.pi*v)**.8+.02),n,w))
            t.stitches('BeltLoopEndTack',samples,pitch=.15)
    p,n,w=t.front(.4,98.2);p+=n*.49;h=np.array([1,0,0]);v=unit(np.cross(h,n));contour=[]
    for cx,cy,start in ((1.65,1.08,0),(-1.65,1.08,90),(-1.65,-1.08,180),(1.65,-1.08,270)):
        for angle in np.linspace(start,start+90,10,endpoint=False):
            a=math.radians(angle);contour.append(p+h*(cx+.30*math.cos(a))+v*(cy+.30*math.sin(a)))
    t.tube('DarkenedSteelBuckle',contour,[w]*len(contour),.12,5,True,8)
    t.tube('BucklePivot',[p-v*1.13,p+v*1.13],[w,w],.085,5,sides=8)
    t.tube('BuckleTongue',[p+n*.08-h*.12,p+n*.08+h*1.87],[w,w],.075,5,sides=8)
    t.band('BeltKeeper',lambda u,v:t.waist(-.23+(u-.5)*.060,97.03+2.4*v),5,9,.36,stitch=False)
    # Supple fly overlap: shallow sewn edge, rounded J closure, no projecting flap.
    t.patch('ShallowFlyFacing',[[-.45,95.85],[1.35,95.85],[1.4,86.8],[.85,84.35],[-.45,84.1]],t.front,slot=0,rise=.075,stitch=False)
    for shift in (0,.23):
        xs=[1.5+shift]*45+list(np.linspace(1.5+shift,-.2,22));zs=list(np.linspace(95.5,86,45))+list(86-1.4*np.sin(np.linspace(0,math.pi/2,22)))
        t.stitches('FlyJTopstitch',[(p+n*.10,n,w) for p,n,w in [t.front(x,z) for x,z in zip(xs,zs)]])
    for sign in (1,-1):
        leg=lambda a,z,sign=sign:t.leg(a,z,sign)
        # Hand pocket rolling lips follow the true cut with taper at its ends.
        for rear in (False,True):
            a=np.array([4.6,91.0]) if rear else np.array([7.,95.35]);b=np.array([12.4,90.6]) if rear else np.array([14.8,85.6]);dr=unit(b-a);ac=np.array([-dr[1],dr[0]])
            for flank in (-1,1):
                def welt(u,v,flank=flank,a=a,b=b,ac=ac,rear=rear,sign=sign):
                    half=(.25 if rear else .12)+(.03 if rear else .68)*math.sin(math.pi*u)
                    q=a+(b-a)*u+ac*flank*(half+.17+(v-.5)*.32)
                    return t.rear(sign*q[0],q[1]) if rear else t.front(sign*q[0],q[1])
                t.band(('Rear' if rear else 'Front')+'RolledPocketLip_'+str(sign)+'_'+str(flank),welt,50,4,.115,0,stitch=False)
                samples=[welt(u,.75) for u in np.linspace(.03,.97,110)]
                t.stitches('PocketLipStitch',[(p+n*.12,n,w) for p,n,w in samples])
            if rear:t.stud('RearWeltButton',t.rear(sign*8.5,90.8),.19,.06)
        for theta in (math.pi/2,-math.pi/2):
            for offset in (-.013,.013):
                # Medial tubular leg ends below the joined crotch; its upper
                # continuation is already sewn along the clipped gusset edge.
                end=64.0 if theta<0 else 79.0
                samples=[leg(theta+offset,z) for z in np.linspace(14.7,end,220)]
                t.stitches('FlatFelledLegSeam',[(p+n*.018,n,w) for p,n,w in samples])
        for offset in (-.014,.014):
            samples=[leg(.84+.45*(z-56)/26+offset,z) for z in np.linspace(56.5,81.0,125)]
            t.stitches('ThighBiasDart',[(p+n*.018,n,w) for p,n,w in samples])
        t.band('TurnedAnkleHem_'+str(sign),lambda u,v:leg(u*math.tau,11.97+1.72*v),112,5,.105,0,closed=True)
        t.patch('CuffAdjustmentTab_'+str(sign),[[1.18,12.3],[1.94,12.3],[1.96,13.45],[1.20,13.45]],leg,rise=.14)
        t.stud('CuffAdjustmentSnap_'+str(sign),leg(1.78,12.9),.20,.20)
    # One restrained tool sleeve, with a free upper rim and an actual dark inside.
    external_pocket(t)
    t.construction_seams()


def external_pocket(t):
    sign=-1; nu=24; nv=46;ps=[];ns=[];ws=[];uv=[]
    for j in range(nv+1):
        v=j/nv
        for i in range(nu+1):
            u=i/nu;y=-2.5+4.8*u;z=65.5+13.3*v+.45*abs(2*u-1)*(1-v)
            p,n,w=t.side(y,z,sign);ease=.06+.33*math.sin(math.pi*u)**.8*smooth(v/.2)
            ps.append(p+n*ease);ns.append(n);ws.append(w);uv.append([y/8,z/8])
    ps=np.array(ps);ns=np.array(ns);uv=np.array(uv);fs=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i
            for tri in ([a,a+1,a+nu+2],[a,a+nu+2,a+nu+1]):
                q=ps[tri]
                if np.cross(q[1]-q[0],q[2]-q[0])@ns[tri].mean(0)>0:tri=tri[::-1]
                fs.append(tri)
    fs=np.array(fs);N=len(ps);coords=np.vstack((ps,ps-ns*.075))
    t.append('OpenToolPocketLeather',coords,np.vstack((fs,fs[:,::-1]+N)),ws+copy.deepcopy(ws),np.concatenate((uv[fs],uv[fs[:,::-1]])),[0]*len(fs)+[3]*len(fs))
    for a,b in boundary(fs):
        pp=coords[[b,a,a+N,b+N]];ff=[[0,1,2],[0,2,3]];tt=np.array([[0,0],[np.linalg.norm(ps[a]-ps[b])/8,0],[np.linalg.norm(ps[a]-ps[b])/8,.075/8],[0,.075/8]])
        t.append('ToolPocketTurnedLip',pp,ff,[ws[b],ws[a],ws[a],ws[b]],tt[ff],1)
    for col in (1,nu-1):
        ids=[j*(nu+1)+col for j in range(2,nv-1)];t.stitches('ToolPocketSideStitch',[(ps[i]+ns[i]*.018,ns[i],ws[i]) for i in ids])
    ids=[(nv-1)*(nu+1)+i for i in range(1,nu)];t.stitches('ToolPocketMouthStitch',[(ps[i]+ns[i]*.018,ns[i],ws[i]) for i in ids])
    ids=[2*(nu+1)+i for i in range(1,nu)];t.stitches('ToolPocketBaseStitch',[(ps[i]+ns[i]*.018,ns[i],ws[i]) for i in ids])


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True);R.mkdir(parents=True,exist_ok=True)
    src,ps,fs,ws,uv=base();t=RealisticTailor(src,ps,fs,ws,uv);t.shell();details(t);d=t.d
    d['outer_shell_triangles']=t.outer_count;d['outer_shell_vertices']=t.outer_vertices
    for i,slot in enumerate(d['triangle_materials']):
        if slot in (0,1):d['uv'][i]=(np.asarray(d['uv'][i])*8/25).tolist()
    # Very subtle rest-space pressure polish, exported as vertex color with skin.
    n=t.outer_vertices;p=np.array(d['positions'][:n]);s,cx,cy,a,z=coordinates(p)
    polish=.07*np.exp(-((z-48)/6)**2)*np.maximum(0,np.cos(a))+.045*np.exp(-((z-85)/7)**2)*np.maximum(0,-np.cos(a))
    for i,k in enumerate(polish):d['colors'][i]=[1-k*.08,1-k*.08,1-k*.09,1-k]
    d['contract']='Concept03 RealisticCutV3: continuous native Jason skinned shell; integrated knee and rear yoke cut panels; angular olive mobility panels; non-mirrored sculpted tension/compression folds; real cut hand/rear pocket mouths with recessed bags; same weights on shell, lining and seams; no cloth simulation; centimetres'
    d['concept']=str(BASE/'Design/LeatherPants_Concept03_Realistic.png')
    write(R/'Authored/ue_leather_pants/Jason.json',d)
    write(R/'authored.json',dict(completed=True,revision='RealisticCutV3',concept=d['concept'],approved_by='User continue after Concept03',vertices=len(d['positions']),triangles=len(d['triangles']),parts=len(d['parts']),native_bones=len(d['bones']),fold_method='Authored cubic crease surface fields, not simulation',pockets='True cut mouths, lined wall and recessed back; one external tool sleeve',material_slots=lib.SLOTS,preview_rendered=False,ue_imported=False,runtime_tested=False))
    print('REALISTIC_CUT_AUTHORED',len(d['positions']),len(d['triangles']),flush=True)


if __name__=='__main__':main()
