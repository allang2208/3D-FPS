"""Keep the R7 stock strike and grips; fit the right support around the stock."""
import copy
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.interpolate import PchipInterpolator
from pose_io import *

WRITE[:]=[n+'_r' for n in ('clavicle','upperarm','lowerarm','lowerarm_aux','lowerarm_twist_02','lowerarm_twist_01','hand')]
cam=json.loads((OLD/'camera_basis.json').read_text());CL=np.array(cam['linear']);CO=np.array(cam['origin_m'])
G=json.loads((O.parents[1]/'Super90LoaderR23_20261010/geometry.json').read_text())
ri={n:np.linalg.inv(m) for n,m in rest.items()}
skin=G['meshes']['Super90_V7_M4_BareArmsV6'];vertices=np.array(skin['positions'])
rf=rest['hand_r'][:3,3]-rest['lowerarm_r'][:3,3]
ru=rest['lowerarm_r'][:3,3]-rest['upperarm_r'][:3,3]
width=rest['index_01_r'][:3,3]-rest['pinky_01_r'][:3,3]
vrest={n:np.array(m) for n,m in json.loads((OLD/'v7_skin_basis.json').read_text())['rest'].items()}
warp={n:np.array(m) for n,m in json.loads((O.parents[1]/'BenelliM4Super9020261006/authoring.json').read_text())['v7_to_native_warp'].items()}
vh=unit(np.cross(vrest['lowerarm_r'][:3,3]-vrest['upperarm_r'][:3,3],vrest['hand_r'][:3,3]-vrest['lowerarm_r'][:3,3]))
def basis(axis,normal):
    x=unit(axis);z=unit(normal-x*(normal@x));return np.column_stack((x,np.cross(z,x),z))
FU=basis(ru,warp['upperarm_r'][:3,:3]@vh)
FF=basis(rf,warp['lowerarm_r'][:3,:3]@vh)
def turn(axis,angle):return R.from_rotvec(unit(axis)*angle).as_matrix()
def mix(a,b,w):return Slerp([0,1],R.from_matrix([a,b]))([float(w)]).as_matrix()[0]
def ease(x):
    x=np.clip(x,0.,1.);return x*x*x*(10+x*(-15+6*x))
blend=ease(times/.095)*(1-ease((times-.64)/.26))

# Split convex sections fit the actual buttstock without filling the open space
# below the pistol grip. These are authoring obstacles, not runtime colliders.
body=np.array(G['meshes']['Super90_body']['positions']);hulls=[]
for lo,hi in [(-.501,-.430),(-.445,-.350),(-.365,-.265)]:
    selected=body[(body[:,1]>=lo)&(body[:,1]<=hi)]
    equations=ConvexHull(selected).equations
    hulls.append(np.unique(np.round(equations,7),axis=0))
station=(vertices-rest['lowerarm_r'][:3,3])@rf/(rf@rf)
armids=[i for i,w in enumerate(skin['weights']) if sum(x for n,x in w.items() if n.endswith('_r'))>.99
        and sum(x for n,x in w.items() if n.startswith(('upperarm','lowerarm')))>.75 and station[i]<.93]
ids=np.array(armids[::7]);V=np.c_[vertices[ids],np.ones(len(ids))];groups={}
for n in names:
    weight=np.array([skin['weights'][i].get(n,0.) for i in ids]);active=np.flatnonzero(weight>0)
    if len(active):groups[n]=(active,weight[active,None],V[active]@ri[n].T)
def skinned(p):
    out=np.zeros((len(ids),3))
    for n,(active,weight,points) in groups.items():out[active]+=((points@p[n].T)[:,:3])*weight
    return out
def clearance(points,gi):
    q=(np.c_[points,np.ones(len(points))]@gi.T)[:,:3]
    return np.min(np.column_stack([np.max(q@h[:,:3].T+h[:,3],axis=1) for h in hulls]),axis=1)
