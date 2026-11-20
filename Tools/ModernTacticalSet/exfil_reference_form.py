"""Anatomical EXFIL-style shell surface in native UE body coordinates, centimetres."""
from pathlib import Path
import numpy as np

SET=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113"
OUT=SET/"ExfilReferenceR4"


def ease(x):
    t=np.clip(x,0.,1.)
    return t*t*(3.-2.*t)


def shape_curve(x,knots,values):
    """Slope-limited Hermite prevents flats at construction samples and rim overshoot."""
    xp=np.asarray(knots,dtype=float);yp=np.asarray(values,dtype=float)
    d=np.diff(yp)/np.diff(xp)
    slopes=np.zeros(len(xp))
    for i in range(1,len(xp)-1):
        if d[i]*d[i-1]>0.:
            h0=xp[i]-xp[i-1];h1=xp[i+1]-xp[i]
            slopes[i]=3*(h0+h1)/((2*h1+h0)/d[i-1]+(h1+2*h0)/d[i])
    i=np.clip(np.searchsorted(xp,x,side='right')-1,0,len(xp)-2)
    h=xp[i+1]-xp[i];t=np.clip((x-xp[i])/h,0.,1.)
    return ((1+2*t)*(1-t)**2*yp[i]+t*(1-t)**2*h*slopes[i]
            +t**2*(3-2*t)*yp[i+1]+t**2*(t-1)*h*slopes[i+1])


class Crown:
    def __init__(self,rig):
        self.rig=rig
        base=np.load(SET/"HelmetContourR2"/f"{rig}-profile.npz")
        nape=np.load(SET/"HelmetNapeR3/Authored"/f"nape-profile-{rig}.npz")
        self.top=float(base["top"])
        self.origin=base["origin"].copy()
        self.center=self.origin.copy()
        self.rad=base["rad"].copy()
        self.polar=np.arange(len(self.rad))*float(base["step"])
        self.angles=np.linspace(0,np.pi,181)
        self.phi=np.linspace(0,2.72,176)
        self.radius=np.empty((len(self.angles),len(self.phi)))
        self.ends=np.empty(len(self.angles))
        # References show a straight brow, short temple lobe, open ear arch,
        # and a substantial rear wing curling inward behind the ear.
        rim_depth=shape_curve(np.degrees(self.angles),
            [0,28,42,56,65,78,93,105,114,121,130,142,155,170,180],
            [7.82,7.84,8.12,9.05,9.38,7.70,6.88,7.14,8.10,9.83,11.97,13.43,14.12,14.28,14.34])
        for i,a in enumerate(self.angles):
            col=a*self.rad.shape[1]/(2*np.pi);j=int(col)
            old=self.rad[:,j]*(1-col%1)+self.rad[:,(j+1)%self.rad.shape[1]]*(col%1)
            # Below the old cut, blend onto the fitted occipital envelope.
            old_d=self.top-self.origin[2]-old*np.cos(self.polar)
            dz=nape["depths"]+nape["depth_delta"][:,i]
            rr=nape["old_radius"][:,i]+nape["radial_delta"][:,i]
            d=np.linspace(old_d[0],21.8,425)
            lower=np.interp(d,dz,rr)
            high=np.interp(d,old_d,old*np.sin(self.polar))
            mix=ease((d-8.0)/3.2)
            r=high*(1-mix)+lower*mix
            z=self.top-d-self.origin[2]
            p=np.arctan2(r,z)
            sphere=np.hypot(r,z)
            values=np.interp(self.phi,p,sphere)
            # The crown crest lies slightly forward of the polar origin. A
            # height-section inversion is multi-valued there, so retain the
            # smooth angular head envelope until the upper wall turns down.
            crown=np.interp(self.phi,self.polar,old)
            lower_weight=ease((self.phi-1.0)/.48)
            values=crown*(1-lower_weight)+values*lower_weight
            # Flatten the crown's side wall slightly and ease the forward lip
            # off the forehead. Material thickness remains inside the fit.
            values+=.17*np.cos(a)**4*np.sin(self.phi)**3
            values+=.25*max(0,np.cos(a))**4*ease((self.phi-.84)/.52)
            self.radius[i]=values
            heights=self.top-self.origin[2]-values*np.cos(self.phi)
            self.ends[i]=np.interp(rim_depth[i],heights,self.phi)
        self.radius[:,0]=self.radius[0,0]

    def sample(self,theta,t):
        a,t=np.broadcast_arrays(np.asarray(theta,float),np.asarray(t,float))
        aa=np.abs(np.arctan2(np.sin(a),np.cos(a)))
        k0=np.minimum(aa/np.pi*180,180-1e-10)
        k=k0.astype(int);u=k0-k
        phi=np.clip(t,0,1.08)*((1-u)*self.ends[k]+u*self.ends[k+1])
        r0=np.clip(phi/self.phi[-1]*(len(self.phi)-1),0,len(self.phi)-1.000001)
        j=r0.astype(int);v=r0-j
        r=((1-u)*((1-v)*self.radius[k,j]+v*self.radius[k,j+1])
           +u*((1-v)*self.radius[k+1,j]+v*self.radius[k+1,j+1]))
        s=np.sin(phi)
        local=np.stack([s*np.sin(a),s*np.cos(a),np.cos(phi)],axis=-1)*r[...,None]
        # The product view has a short, rounded summit and two falling flanks.
        # The native head envelope has a broad, nearly level region here.
        # Shape the upper shell in plan coordinates so both sides meet at a
        # single crown, just forward of centre. The lower wall retains its fit.
        x=local[...,0]
        forward,fore_aft,rounding=(.45,1.02,1.0) if self.rig=="Jason" else (1.15,.85,1.35)
        y=(local[...,1]-forward)*fore_aft
        distance=np.sqrt((x*1.06)**2+y*y+rounding**2)-rounding
        roof=.80-.17*distance
        upper=ease((local[...,2]-5.1)/5.8)
        local[...,2]+=roof*upper
        return self.origin+local

    def normal(self,theta,t):
        a,t=np.broadcast_arrays(np.asarray(theta,float),np.asarray(t,float))
        dt=np.maximum(t,.002)
        cross=np.cross(self.sample(a+.001,dt)-self.sample(a-.001,dt),
                       self.sample(a,dt+.0008)-self.sample(a,dt-.0008))
        return cross/np.maximum(np.linalg.norm(cross,axis=-1,keepdims=True),1e-15)

    def surface(self,theta,t,offset=0.):
        return self.sample(theta,t)+self.normal(theta,t)*np.asarray(offset)[...,None]
