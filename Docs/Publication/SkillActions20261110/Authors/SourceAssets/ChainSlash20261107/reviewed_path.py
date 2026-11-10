"""Rebuild the path from the guard, projected blade length, and the visible arm silhouettes."""
from pathlib import Path
import json
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation as R
from fit_motion import P, KEYS, FRAMES, F, world, unit, project

# Screen space on the 480 x 270 reference. The last four columns are elbow guides.
# Invisible portions are intentionally outside the viewport. Their 3D depth is fitted.
points=np.array([
[2238,359,174,450,-140,475,345,275,333],[2241,359,174,450,-140,475,345,275,333],
[2244,385,163,494,-130,480,318,253,329],[2247,460,154,640,-100,536,323,252,310],
[2250,552,140,730,-20,580,315,251,265],[2253,491,104,710,25,548,315,181,249],
[2256,305,144,475,-24,333,325,79,264],[2259,215,216,341,-5,280,354,83,332],
[2262,156,337,175,151,236,419,54,404],[2265,100,448,112,290,197,450,33,441],
[2277,61,461,-84,372,167,459,18,450],[2280,51,383,-115,340,190,399,68,446],
[2283,87,286,-110,319,258,277,123,376],[2286,66,228,-115,248,310,216,153,350],
[2289,263,188,126,-5,446,259,322,345],[2292,341,264,304,159,480,305,377,356],
[2295,422,451,432,323,541,401,480,452],[2307,500,458,600,423,520,416,341,406],
[2310,454,383,590,408,514,397,314,354],[2313,372,285,548,337,408,365,163,223],
[2316,290,196,436,264,291,335,97,149],[2319,170,134,220,100,234,266,22,196],
[2322,35,82,146,-78,140,205,-83,180],[2325,-50,173,57,91,69,295,-149,224],
[2328,-122,401,-38,286,83,385,-119,391],[2331,-85,435,-160,415,141,379,-45,442],
[2334,69,340,-72,395,267,263,100,413],[2337,221,230,74,290,397,169,275,360],
[2340,280,139,187,122,458,124,323,304],[2343,439,129,399,35,587,126,462,291],
[2346,556,115,585,14,655,132,552,262],[2349,597,108,650,35,700,160,641,300],
[2355,678,163,746,102,754,242,734,350],[2361,667,290,743,177,731,357,656,429],
[2367,595,341,675,75,682,417,599,438],[2370,503,309,604,25,595,407,462,386],
[2373,470,268,590,13,568,389,433,359],[2376,434,224,588,-45,538,371,402,352],
[2379,419,199,562,-65,524,350,375,336],[2382,412,183,534,-85,515,342,352,329],
[2385,393,176,496,-100,489,342,325,332],[2388,372,177,463,-134,480,342,289,332],
[2394,359,174,450,-140,475,345,275,333],[2400,359,174,450,-140,475,345,275,333]])
obs=PchipInterpolator(points[:,0],points[:,1:],axis=0)(FRAMES)
N=len(FRAMES)
def rays(uv):return np.column_stack(((uv[:,0]-240)/F,np.ones(N),(135-uv[:,1])/F))
base_ray=rays(obs[:,:2]); tip_ray=unit(rays(obs[:,2:4]))
def blade(depth):
    p=base_ray*depth[:,None];along=(p*tip_ray).sum(1)
    # Ray/sphere intersection fixes foreshortening when the tip is visible.
    target=tip_ray*(along+np.sqrt(np.maximum(4.,92**2-(p*p).sum(1)+along**2)))[:,None]
    return p,unit(target-p)
def transport(z):
    vectors=[];x=np.array([-1.,0,0])
    for axis in z:
        x=unit(x-axis*np.dot(x,axis));vectors.append(x)
    return np.array(vectors)
_,initial_axis=blade(np.full(N,33.))
basis=transport(initial_axis)
def unpack(params):
    x=params.reshape(N,8);p,z=blade(x[:,0])
    normal=unit(basis-z*(basis*z).sum(1)[:,None])
    across=normal*np.cos(x[:,1,None])+np.cross(z,normal)*np.sin(x[:,1,None])
    return x,p,np.stack((across,np.cross(z,across),z),axis=-1)
def fit(grip):
    w=world(json.loads((P/'grip_poses.json').read_text())[grip]['idle'])
    wp=w['WPN_root'][:3,3];wr=w['WPN_root'][:3,:3];wr=wr/np.linalg.norm(wr,axis=0)
    arms=[]
    for s in 'rl':
        a,e,h=[w[b+'_'+s][:3,3] for b in ('upperarm','lowerarm','hand')]
        arms.append((a,np.linalg.norm(e-a),np.linalg.norm(h-e),wr.T@(h-wp),wr.T@unit(h-e)))
    def loss(params):
        x,p,r=unpack(params);terms=[((x[:,0]-36)*.34)[:,None]]
        for j,(a,upper,lower,grip_pos,natural) in enumerate(arms):
            h=p+r@grip_pos;e=x[:,2+3*j:5+3*j];fore=unit(h-e);u=unit(e-a)
            cos=(fore*(r@natural)).sum(1)
            target=obs[:,4+2*j:6+2*j]
            terms += [(project(e)-target)*.64,((np.linalg.norm(h-e,axis=1)-lower)*13)[:,None],
                      ((np.linalg.norm(e-a,axis=1)-upper)*1.0)[:,None],
                      (fore-r@natural)*22,np.maximum(.96-cos,0)[:,None]*180,
                      np.maximum((fore*u).sum(1)-.90,0)[:,None]*45,
                      np.maximum(24-e[:,1],0)[:,None]*7,np.maximum(22-h[:,1],0)[:,None]*6]
        scale=np.array([1,24,1,1,1,1,1,1])
        return np.r_[np.concatenate(terms,axis=1).ravel(),(np.diff(x,axis=0)*scale*.65).ravel(),(np.diff(x,n=2,axis=0)*scale*2.6).ravel()]
    x=np.zeros((N,8));x[:,0]=34
    grid=np.linspace(-np.pi,np.pi,72,endpoint=False)
    costs=[]
    for turn in grid:
        x[:,1]=turn;_,p,r=unpack(x);cost=np.zeros(N)
        for j,(a,upper,lower,g,natural) in enumerate(arms):
            h=p+r@g;e=h-r@natural*lower
            cost+=np.linalg.norm((project(e)-obs[:,4+2*j:6+2*j])*.20,axis=1)**2+((np.linalg.norm(e-a,axis=1)-upper)*1.2)**2+np.maximum(18-e[:,1],0)**2*20
        costs.append(cost)
    costs=np.array(costs).T
    diff=np.angle(np.exp(1j*(grid[:,None]-grid[None,:])))
    prior=costs[0];parents=[]
    for row in costs[1:]:
        pair=prior[:,None]+(diff*65)**2
        parents.append(pair.argmin(0));prior=row+pair.min(0)
    ids=[prior.argmin()]
    for prev in reversed(parents):ids.append(prev[ids[-1]])
    x[:,1]=np.unwrap(grid[np.array(ids[::-1])]);_,p,r=unpack(x)
    for j,(_,_,length,g,natural) in enumerate(arms):x[:,2+j*3:5+j*3]=p+r@g-(r@natural)*length
    count=len(loss(x));per=(count-8*(2*N-3))//N;mask=lil_matrix((count,8*N),dtype=np.int8)
    for i in range(N):mask[i*per:(i+1)*per,8*i:8*i+8]=1
    at=N*per
    for order in (1,2):
        for i in range(N-order):
            for k in range(8):
                for j in range(order+1):mask[at+i*8+k,(i+j)*8+k]=1
        at+=8*(N-order)
    low=np.full_like(x,-np.inf);hi=np.full_like(x,np.inf);low[:,0]=22;hi[:,0]=56
    result=least_squares(loss,x.ravel(),bounds=(low.ravel(),hi.ravel()),jac_sparsity=mask.tocsr(),max_nfev=150,ftol=2e-5,x_scale='jac')
    x,p,r=unpack(result.x)
    rows=[dict(frame=int(f),p=p[i].tolist(),q=R.from_matrix(r[i]).as_quat().tolist(),elbows=x[i,2:].reshape(2,3).tolist()) for i,f in enumerate(FRAMES)]
    (P/(grip+'-fit.json')).write_text(json.dumps(rows,separators=(',',':')))
if __name__=='__main__':
    for grip in ('Standard','LongGrip'):fit(grip)
