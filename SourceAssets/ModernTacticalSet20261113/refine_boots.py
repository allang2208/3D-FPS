"""R3: smooth native last, open quarters, fitted tongue and surface-routed laces."""
import math
import numpy as np

def monotone(x,xs,ys):
    h=np.diff(xs);d=np.diff(ys)/h;m=np.zeros(len(xs));m[0]=d[0];m[-1]=d[-1]
    for i in range(1,len(xs)-1):
        if d[i-1]*d[i]>0:
            w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1];m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    i=int(np.clip(np.searchsorted(xs,x)-1,0,len(xs)-2));t=float(np.clip((x-xs[i])/h[i],0,1))
    return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h[i]*m[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h[i]*m[i+1]

def build(api):
    globals().update({k:api[k] for k in ['read','PROJECT','WeightSurface','mesh','grid','tube','stitch','box','smooth','unit']})
    donor=read(PROJECT/'SourceAssets/ST6LowerSet20261018/Jason_ST6Boots_Garment.json');weights=WeightSurface(donor)
    levels=np.array([1.8,2.6,3.8,5.2,7,9.5,12,16,21,26,28.5])
    rx=np.array([5.4,5.65,5.85,5.7,5.3,4.8,4.75,5,5.7,6.1,6.15])
    ry=np.array([15.4,15.5,14.7,12.8,10.2,7.4,5.65,5.5,5.9,6.25,6.3])
    cy=np.array([7.4,7.4,7,5.3,3.3,.5,-2,-2.65,-2.8,-2.8,-2.8])
    # Sample the smooth curves once; every attached component shares the last.
    zs=np.linspace(1.8,29,545)
    values=[np.array([monotone(z,levels,y) for z in zs]) for y in [rx,ry,cy]]
    tilt=math.atan2(2.00392146,12.92064786);ct=math.cos(tilt);st=math.sin(tilt)
    def world(x,y,z,sg):return np.array([sg*(14.798+ct*x+st*y),-2.45465-st*x+ct*y,z])
    def local(t,z):
        xr,yr,yc=[np.interp(z,zs,y) for y in values];s=math.sin(t);c=math.cos(t)
        power=.83+.17*float(smooth(7,13,z))
        fold=.065*math.sin(z*1.7+1.1*s)*math.exp(-((z-13)/3.8)**2)
        return np.array([xr*math.copysign(abs(s)**power,s)*(1-.12*max(0,-c))+fold*s,yc+yr*math.copysign(abs(c)**power,c)+fold*c,z])
    def surface(t,z,sg,offset=0):
        q=local(t,z)
        if offset:
            dt=local(t+.003,z)-local(t-.003,z);dz=local(t,z+.015)-local(t,z-.015)
            n=unit(np.cross(dz,dt))
            if np.dot(n,[math.sin(t),math.cos(t),0])<0:n=-n
            q+=n*offset
        return world(*q,sg)
    def opening(z):return .44*float(smooth(5.8,10,z))
    for side,sg in [('l',1),('r',-1)]:
        # A genuine front opening; the tongue sits beneath the reinforced edges.
        def upper(u,v):
            z=2.1+26.4*v;a=opening(z);return surface(a+(math.tau-2*a)*u,z,sg)
        grid('Boot_ContinuousQuarters_'+side,upper,100,85,'RangerNylon',thickness=.22,source=weights,radial_center=(sg*14.8,-2.45,14))
        def tongue(u,v):return surface((u-.5)*1.23,6.15+21.95*v,sg,.055)
        grid('Boot_PaddedBellowsTongue_'+side,tongue,24,64,'CharcoalStretch',thickness=.28,source=weights,outward=(0,1,0))
        for e in [.035,.965]:stitch('TongueEdge_'+side+str(e),[tongue(e,v)+[0,.045,0] for v in np.linspace(.02,.98,100)],source=weights,pitch=.30)
        grid('Boot_TongueTopBinding_'+side,lambda u,v:surface((u-.5)*1.23,27.45+v*.68,sg,.12),24,4,'OliveWebbing',thickness=.12,source=weights,outward=(0,1,0))
        for flank in [-1,1]:
            def facing(u,v,flank=flank):
                z=7.1+20.9*v;return surface(flank*(opening(z)+.015+u*.35),z,sg,.19)
            grid('Boot_LeatherEyeletStay_'+side+str(flank),facing,10,60,'CharcoalLeather',thickness=.15,source=weights,outward=(0,1,0))
            for edge in [.07,.93]:stitch('FacingDoubleNeedle_'+side+str((flank,edge)),[facing(edge,v)+[0,.04,0] for v in np.linspace(.015,.985,100)],source=weights,pitch=.28)
            # Sewn ankle reinforcement follows the continuous upper surface.
            grid('Boot_AnkleSupport_'+side+str(flank),lambda u,v,flank=flank:surface(flank*(.92+1.25*u),5.2+(11.5-3*math.sin(math.pi*u))*v,sg,.10),22,28,'CharcoalLeather',thickness=.12,source=weights,radial_center=(sg*14.8,-2.45,10))
            stitch('AnkleSupportStitch_'+side+str(flank),[surface(flank*(.92+1.25*u),16.35-3*math.sin(math.pi*u),sg,.15) for u in np.linspace(0,1,65)],source=weights)
        # Real toe cap and seam share the same curved boundary.
        def cap(u,v):
            t=(u-.5)*3.45;top=5.1+1.7*max(0,math.cos(t));return surface(t,2.3+(top-2.3)*v,sg,.12)
        grid('Boot_ShapedToeCap_'+side,cap,42,24,'CharcoalLeather',thickness=.12,source=weights,outward=(0,1,0))
        for edge in [.92,.99]:stitch('ToeCapDoubleNeedle_'+side+str(edge),[cap(u,edge)+[0,.025,.025] for u in np.linspace(.01,.99,120)],source=weights,pitch=.28)
        grid('Boot_HeelCounter_'+side,lambda u,v:surface(math.pi+(u-.5)*1.85,2.5+10.6*v,sg,.14),30,30,'CharcoalLeather',thickness=.15,source=weights,outward=(0,-1,0))
        for a in [-.86,.86]:stitch('HeelCounterStitch_'+side+str(a),[surface(math.pi+a,z,sg,.19) for z in np.linspace(3.0,12.8,70)],source=weights)
        # Padded collar and separate internal lining, open across the tongue.
        grid('Boot_CollarPad_'+side,lambda u,v:surface(.44+(math.tau-.88)*u,26.35+v*2.15,sg,.18*math.sin(math.pi*v)),90,10,'CharcoalStretch',thickness=.32,source=weights,radial_center=(sg*14.8,-2.45,27))
        grid('Boot_CollarLining_'+side,lambda u,v:surface(.44+(math.tau-.88)*u,24.6+v*3.7,sg,-.26),90,8,'CharcoalStretch',source=weights,radial_center=(sg*14.8,-2.45,27))
        tube('Boot_CuffBinding_'+side,[surface(t,28.48,sg,-.03) for t in np.linspace(.44,math.tau-.44,100)],.16,'OliveWebbing',8,source=weights)
        rows=np.linspace(8.0,26.7,9)
        for i,z in enumerate(rows):
            for flank in [-1,1]:
                t=flank*(opening(z)+.14);c=surface(t,z,sg,.30)
                tangent=unit(surface(t+.02,z,sg)-surface(t-.02,z,sg));up=unit(surface(t,z+.05,sg)-surface(t,z-.05,sg));up=unit(up-tangent*np.dot(up,tangent))
                ring=[c+.235*(tangent*math.cos(a)+up*math.sin(a)) for a in np.linspace(0,math.tau,24,endpoint=False)]
                tube('Boot_RolledEyelet_'+side+str((i,flank)),ring,.073,'Gunmetal',8,True,source=weights)
        for i in range(len(rows)-1):
            for flank in [-1,1]:
                path=[]
                for u in np.linspace(0,1,26):
                    z=rows[i]*(1-u)+rows[i+1]*u
                    theta=flank*((opening(rows[i])+.14)*(1-u)-(opening(rows[i+1])+.14)*u)
                    path.append(surface(theta,z,sg,.43+(.085 if flank==1 else 0)*math.sin(math.pi*u)))
                tube('Boot_SurfaceRoutedLace_'+side+str((i,flank)),path,.105,'OliveWebbing',8,source=weights)
        # Compact knot, two loops and resting loose ends follow the tongue.
        knot=surface(0,27.05,sg,.58)
        tube('Boot_LaceKnot_'+side,[knot+np.array([.19*math.cos(a),.08*math.sin(a),.19*math.sin(a)]) for a in np.linspace(0,math.tau,30)],.105,'OliveWebbing',8,True,source=weights)
        for flank in [-1,1]:
            path=[surface(flank*.23*math.sin(a),27.05+.95*(1-math.cos(a)),sg,.55+.12*math.sin(a)**2) for a in np.linspace(0,math.tau,52)]
            tube('Boot_LaceLoop_'+side+str(flank),path,.105,'OliveWebbing',8,source=weights)
            tail=[surface(flank*(.05+.30*u),27.05-2.6*u,sg,.56-.10*u) for u in np.linspace(0,1,30)]
            tube('Boot_LaceTail_'+side+str(flank),tail,.105,'OliveWebbing',8,source=weights)
            tube('Boot_LaceAglet_'+side+str(flank),tail[-5:],.118,'MattePolymer',8,source=weights)
        grid('Boot_RearPullLoop_'+side,lambda u,v:surface(math.pi+(u-.5)*.26,25.6+3.1*v,sg,.18+.65*math.sin(math.pi*v)),6,28,'OliveWebbing',thickness=.15,source=weights,outward=(0,-1,0))
        # Sole and welt use the rotated native last, with a continuous tread bed.
        outline=[local(t,2.2) for t in np.linspace(0,math.tau,112,endpoint=False)]
        def solepoint(t,z,scale):
            q=local(t,2.2);q[:2]=np.array([0,7.4])+(q[:2]-[0,7.4])*scale;q[2]=z+.18*max(0,math.cos(t))**4
            return world(*q,sg)
        pts=[];faces=[];rings=[(.5,.99),(.70,1.025),(1.25,1.035),(1.8,1.025),(2.35,1.005)]
        for z,scale in rings:pts.extend(solepoint(t,z,scale) for t in np.linspace(0,math.tau,112,endpoint=False))
        for j in range(4):
            for i in range(112):faces.append([j*112+i,j*112+(i+1)%112,(j+1)*112+(i+1)%112,(j+1)*112+i])
        faces.extend([list(reversed(range(112))),list(range(448,560))]);mesh('Boot_MoldedOutsole_'+side,pts,faces,'BlackRubber',source=weights)
        for z in [1.0,1.83]:tube('Boot_SoleMolding_'+side+str(z),[solepoint(t,z,1.035) for t in np.linspace(0,math.tau,112,endpoint=False)],.085,'BlackRubber',6,True,source=weights)
        stitch('Boot_StitchedWelt_'+side,[solepoint(t,2.43,1.006) for t in np.linspace(0,math.tau,190)],source=weights,pitch=.30)
        basis=np.array([[sg*ct,sg*st,0],[-st,ct,0],[0,0,1]])
        def inside(x,y):return (abs(x)/5.5)**2.4+(abs(y-7.4)/15.4)**2.4<.79
        for j,y in enumerate(np.arange(-4.2,21,2.85)):
            for k,x in enumerate([-3.2,0,3.2]):
                if not all(inside(x+dx,y+dy) for dx in [-1.1,1.1] for dy in [-1.05,1.05]):continue
                if 2<y<7 and k==1:continue
                box('Boot_ContainedTread_'+side+str((j,k)),world(x,y,.35,sg),[2.2,2.1,.7],'BlackRubber',.14,basis,source=weights)
        print('TS01_REFINED_BOOT',side,flush=True)
