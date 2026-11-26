"""Seated leather edges and fine sunk stitches on the already repaired body.

The continuous shell, skin weights, neckline/cuff cuts and native rig are read
from the inspected source. Only its added tailoring pieces are re-authored.
"""
import copy,gc,json,math,sys
from pathlib import Path
import bpy,numpy as np
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/RangerLeatherPants20261021';R=BASE/'AtelierFinishV2'
sys.path.insert(0,str(P/'Tools/RangerLeatherPants'));import author as lib
from author import unit,smooth,normals,norm_weights,blend_weights,read,write

class RefinedTailor(lib.Tailor):
    def stitches(self,name,samples,closed=False,pitch=.32):
        # Existing construction calls supply a small clearance above the
        # surface. Seat both ends and lift only the middle of each stitch.
        p=np.array([s[0] for s in samples]);n=np.array([s[1] for s in samples]);w=[s[2] for s in samples]
        p-=n*.018
        if closed:p=np.r_[p,p[:1]];n=np.r_[n,n[:1]];w=w+w[:1]
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];pitch=min(pitch,.32)
        for k,distance in enumerate(np.arange(pitch*.5,arc[-1]-.10,pitch)):
            pp=[];ww=[];length=min(.19,pitch*.66)*(1+.035*math.sin(k*1.71));phase=.009*math.sin(k*2.31)
            for t in (0.,.25,.50,.75,1.):
                a=distance+(t-.5)*length;i=min(len(p)-2,max(0,np.searchsorted(arc,a)-1));f=(a-arc[i])/max(arc[i+1]-arc[i],1e-8);normal=unit(n[i]*(1-f)+n[i+1]*f)
                pp.append(p[i]*(1-f)+p[i+1]*f+normal*(-.010+.027*math.sin(math.pi*t)));ww.append(blend_weights(w[i],w[i+1],f))
            before=len(self.d['positions']);self.tube(name+'_'+str(k),pp,ww,.0105*(1+.04*math.sin(k*2.13)),4,sides=5)
            shade=.84+.08*math.sin(k*1.91)**2
            for i in range(before,len(self.d['positions'])):self.d['colors'][i]=[shade,shade*.97,shade*.92,1.]
    def band(self,name,fn,nu,nv,rise=.16,slot=1,closed=False,stitch=True):
        old=fn
        def fit(u,v):
            p,n,w=old(u,v);edge=min(v,1-v);target=rise
            if name.startswith('SewnBeltLoop'):target=.135+.245*math.sin(math.pi*v)**.8
            elif name=='SuppleLeatherBelt':target=.24
            elif name=='BeltKeeper':target=.36
            elif slot in (0,1):target=max(.100,rise-.035*(1-float(smooth(edge/.20))))
            if stitch and slot in (0,1):target-=.009*(math.exp(-((v-.12)/.055)**2)+math.exp(-((v-.88)/.055)**2))
            return p+n*(target-rise),n,w
        super().band(name,fit,nu,max(nv,8),rise,slot,closed,stitch)
    def patch(self,name,outline,project,slot=1,rise=.19,stitch=True):
        outline=np.array(outline);curve=[]
        for i,b in enumerate(outline):
            a=outline[(i-1)%len(outline)];c=outline[(i+1)%len(outline)];d=outline[(i+2)%len(outline)]
            for t in np.linspace(0,1,10,endpoint=False):curve.append((2*t**3-3*t*t+1)*b+(t**3-2*t*t+t)*(c-a)*.30+(-2*t**3+3*t*t)*c+(t**3-t*t)*(d-b)*.30)
        curve=np.array(curve);middle=curve.mean(0);N=len(curve);center=project(*middle)[0];perimeter=np.array([project(*q)[0] for q in curve]);radial=np.linalg.norm(perimeter-center,axis=1)
        levels=np.array([0,.17,.34,.51,.66,.78,.85,.90,.94,.965,.980,.990,1.]);ps=[];ns=[];ws=[];tex=[];colors=[]
        gauge=float(np.clip(rise*(.78 if 'Pocket' in name else .55),.075,.34))
        def offset(r,radius):
            inset=(1-r)*radius;thick=.050+(gauge-.050)*float(smooth(inset/.48));crease=0.
            if stitch:crease=.010*math.exp(-((inset-.20)/.065)**2)+.009*math.exp(-((inset-.41)/.070)**2)
            return .018+thick-crease
        for row,r in enumerate(levels):
            for j,q in enumerate([middle] if row==0 else [middle+(q-middle)*r for q in curve]):
                j=0 if row==0 else j;p,n,w=project(*q);inset=(1-r)*radial[j];pressure=math.exp(-inset/.19);wear=math.exp(-((inset-.12)/.11)**2)
                # Edge pressing and restrained burnishing affect color and roughness together.
                shade=1-.065*pressure+.015*wear;ps.append(p+n*offset(r,radial[j]));ns.append(n);ws.append(w);tex.append(q);colors.append([shade,shade*.998,shade*.993,1-.10*wear])
        ps=np.array(ps);ns=np.array(ns);tex=np.array(tex);fs=[]
        for j in range(N):fs.append([0,1+j,1+(j+1)%N])
        for row in range(len(levels)-2):
            for j in range(N):
                a=1+row*N+j;b=1+row*N+(j+1)%N;fs.extend([[a,b,b+N],[a,b+N,a+N]])
        fs=np.array(fs)
        for i,tri in enumerate(fs):
            if np.cross(ps[tri[1]]-ps[tri[0]],ps[tri[2]]-ps[tri[0]])@ns[tri].mean(0)>0:fs[i]=tri[::-1]
        scale=[]
        for axis in range(2):
            lo=int(np.argmin(tex[:,axis]));hi=int(np.argmax(tex[:,axis]));scale.append(np.linalg.norm(ps[hi]-ps[lo])/max(tex[hi,axis]-tex[lo,axis],1e-8))
        tex=tex*np.array(scale)/8;bottom=[]
        for row,r in enumerate(levels):
            for j,q in enumerate([middle] if row==0 else [middle+(q-middle)*r for q in curve]):
                p,n,w=project(*q);bottom.append(p+n*.018)
        count=len(ps);coords=np.vstack((ps,bottom));ff=np.vstack((fs,fs[:,::-1]+count));uv=np.concatenate((tex[fs],tex[fs[:,::-1]]))
        self.append(name,coords,ff,ws+copy.deepcopy(ws),uv,slot,colors=colors+[[.82,.80,.77,1] for _ in ws])
        ring=np.arange(1+(len(levels)-2)*N,len(ps))
        for a,b in zip(ring,np.roll(ring,-1)):
            pp=coords[[a,b,b+count,a+count]];tri=[[0,1,2],[0,2,3]];l=np.linalg.norm(ps[a]-ps[b])/8;tt=np.array([[0,0],[l,0],[l,.05/8],[0,.05/8]]);out=unit((pp[:2].mean(0)-ps[0])-ns[a]*((pp[:2].mean(0)-ps[0])@ns[a]))
            if np.cross(pp[1]-pp[0],pp[2]-pp[0])@out>0:tri=[[0,2,1],[0,3,2]]
            self.append(name+'_TurnedEdge',pp,tri,[ws[a],ws[b],ws[b],ws[a]],tt[tri],slot,colors=[[.91,.90,.88,.93]]*4)
        if stitch:
            for inset in (.20,.41):
                samples=[]
                for j,q in enumerate(curve):
                    r=max(.65,1-inset/max(radial[j],.1));p,n,w=project(*(middle+(q-middle)*r));samples.append((p+n*(offset(r,radial[j])+.018),n,w))
                self.stitches(name+'_SaddleStitch',samples,True)

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True);old=read(BASE/'Authored/ue_leather_pants/Jason.json');n=old['parts'][0]['vertices']//2;count=old['outer_shell_triangles']
    ps=np.array(old['positions'][:n]);fs=np.array(old['triangles'][:count]);ws=old['weights'][:n];uv=np.array(old['uv'][:count]);src=dict(source=old['binding_source'],skeleton=old['skeleton'],bones=[dict(name=k,**v) for k,v in old['bones'].items()])
    t=RefinedTailor(src,ps,fs,ws,uv)
    # Copy the entire inspected base (including its matching lining and turned
    # openings) exactly. New tailoring never reprojects or rebinds the body.
    for part in old['parts']:
        if part['name'] not in ('ContinuousLeatherAndMobilityPanels','TurnedShellEdge'):continue
        a=part['first_vertex'];b=a+part['vertices'];fi=part['first_triangle'];fj=fi+part['triangles']
        t.append(part['name'],old['positions'][a:b],np.array(old['triangles'][fi:fj])-a,old['weights'][a:b],old['uv'][fi:fj],old['triangle_materials'][fi:fj],old['normals'][fi:fj],old['colors'][a:b])
    t.outer_count=count;lib.details(t);d=t.d;d['outer_shell_triangles']=count
    # Native metric charts are 8 cm. Preserve their orientation and scale only
    # leather faces to the scan's recorded 25 cm tile, with no shader guesswork.
    for fi,slot in enumerate(d['triangle_materials']):
        if slot in (0,1):d['uv'][fi]=(np.array(d['uv'][fi])*8/25).tolist()
    # Broad pressure polish is tied to anatomical/rest coordinates, never to
    # screen/world position, and stays with the native skinned garment.
    positions=np.array(d['positions']);first=d['parts'][0]
    for i in range(n):
        x,y,z=positions[i];sign=1 if x>=0 else -1;c=lib.center(z,sign);front=max(0,(y-c[1])/10)
        polish=.15*math.exp(-((z-48)/6)**2)*min(1,front)+.09*math.exp(-((z-86)/7)**2)*max(0,-(y-.8)/12)
        d['colors'][i]=[1-polish*.14,1-polish*.15,1-polish*.16,1-polish]
    d['contract']+='; AtelierFinishV2: inspected continuous shell preserved; measured 25cm scanned leather; skived seated panel edges; 3.2mm pitch sunk stitches; rest-space pressure polish'
    d['tailored_finish']=dict(edge_gauge_cm=.05,contact_clearance_cm=.018,stitch_pitch_cm=.32,stitch_length_cm=.19,thread_diameter_cm=.021,stitch_ends_depth_cm=.01,stitch_arch_height_cm=.017,leather_tile_cm=25,cloth_tile_cm=8)
    write(R/'Authored/ue_leather_pants/Jason.json',d);write(R/'authored.json',dict(completed=True,revision='AtelierFinishV2',concept=str(BASE/'Design/LeatherPants_Concept02.png'),source=str(BASE/'Authored/ue_leather_pants/Jason.json'),vertices=len(d['positions']),triangles=len(d['triangles']),preserved_native_body=True,finish=d['tailored_finish'],runtime_tested=False))
    print('ATELIER_TAILORING_SAVED',len(d['positions']),len(d['triangles']),flush=True)
if __name__=='__main__':main()
