"""Shared geometry/texture projection for the front-to-side sculpt transition."""
import numpy as np
from surface_recipe import smooth, face_height, body_height

PROFILE_Z=np.array([-.060,-.045,-.039,-.030,-.021,-.012,-.005,0,.008,.018,.029,.039,.050])
PROFILE_Y=np.array([.022,.026,.030,.036,.038,.034,.040,.046,.047,.037,.029,.012,.002])
PROFILE_SAMPLE_Z=np.linspace(-.060,.050,2048)
_profile=np.interp(PROFILE_SAMPLE_Z,PROFILE_Z,PROFILE_Y)
_k=np.arange(-36,37);_weights=np.exp(-.5*(_k/12)**2);_weights/=_weights.sum()
PROFILE_SAMPLE_Y=np.convolve(np.pad(_profile,36,mode='edge'),_weights,mode='valid')

def anatomy_y(x,z):
    x,z=np.asarray(x),np.asarray(z)
    forward=np.interp(z,PROFILE_SAMPLE_Z,PROFILE_SAMPLE_Y)
    side_fall=.034*np.minimum(np.abs(x)/.041,1.2)**1.40
    side_corner=.0012*np.exp(-((z+.010)/.008)**2)*np.exp(-((np.abs(x)-.012)/.008)**2)
    sockets=.0028*sum(np.exp(-(((x-sign*.0176)/.0047)**2+((z-.0176)/.0037)**2)) for sign in [-1,1])
    cheek=.003*np.exp(-((np.abs(x)-.024)/.009)**2-((z+.008)/.023)**2)
    return forward-side_fall-side_corner-sockets+cheek

def side_projection(x,z):
    """Same direction field as the posterior spherical mane atlas."""
    x,z=np.asarray(x),np.asarray(z)
    y=anatomy_y(x,z)
    theta=np.arctan2(x,z+.0015)
    beta=np.arctan2(.004-y,np.sqrt(x*x+(z+.0015)**2))
    return (theta/(2*np.pi)+.5)%1,(beta+np.pi/2)/np.pi,smooth(.019,.031,np.abs(x))

def front_y(x,z):
    u,v,w=side_projection(x,z)
    face=face_height(np.asarray(x)/.082+.5,.5-np.asarray(z)/.09)
    side=body_height(u,v)
    return anatomy_y(x,z)+(1-w)*face+w*side

def front_point(x,z):
    """Lift lateral relief along the cheek normal instead of along the muzzle axis."""
    x,z=np.asarray(x),np.asarray(z)
    u,v,w=side_projection(x,z)
    side=body_height(u,v)
    face=face_height(x/.082+.5,.5-z/.09)
    eps=.00015
    slope_x=(anatomy_y(x+eps,z)-anatomy_y(x-eps,z))/(2*eps)
    slope_z=(anatomy_y(x,z+eps)-anatomy_y(x,z-eps))/(2*eps)
    length=np.sqrt(1+slope_x*slope_x+slope_z*slope_z)
    return np.stack([x-w*side*slope_x/length,
                     anatomy_y(x,z)+(1-w)*face+w*side/length,
                     z-w*side*slope_z/length],axis=-1)
