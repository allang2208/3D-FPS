"""Produce an open blend between measured mesh sections, including one-to-two transitions."""
import json
import sys
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from skimage.draw import polygon
from skimage.measure import marching_cubes

def make(a,b):
    a=[np.array(r) for r in a]; b=[np.array(r) for r in b]
    if len(a)==len(b):
        # Match each rail individually so two separate rails never pinch or trade widths.
        vertices=[];faces=[]
        def ring_samples(r,n=72):
            if np.sum(r[:,0]*np.roll(r[:,1],-1)-r[:,1]*np.roll(r[:,0],-1))<0:r=r[::-1]
            close=np.vstack((r,r[0]))
            arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(close,axis=0),axis=1))]
            s=np.arange(n)*arc[-1]/n
            return np.column_stack([np.interp(s,arc,close[:,i]) for i in range(2)])
        for p,q in zip(a,b):
            p,q=ring_samples(p),ring_samples(q)
            qa=q-q.mean(0);pa=p-p.mean(0)
            j=min(range(len(q)),key=lambda d:np.sum((pa-np.roll(qa,d,axis=0))**2))
            q=np.roll(q,j,axis=0)
            first=len(vertices);n=len(p)
            for t in np.linspace(.022,.978,15):
                v=(1-t)*p+t*q
                vertices.extend([[x,y,t] for x,y in v])
            for row in range(14):
                for i in range(n):
                    j=(i+1)%n;l=first+row*n
                    faces.extend([[l+i,l+j,l+i+n],[l+j,l+j+n,l+i+n]])
        return {'v':vertices,'f':faces}
    def bounds(rings):
        cloud=np.concatenate(rings)
        lo,hi=cloud.min(0),cloud.max(0)
        return (lo+hi)/2,hi-lo
    ca,wa=bounds(a);cb,wb=bounds(b)
    # In a common section space the two profiles share their silhouette centre and span.
    pitch=.073
    span=np.maximum(wa,wb)
    dims=(np.ceil(span/pitch).astype(int)+13)
    def field(rings,c,w):
        solid=np.zeros(dims,bool)
        for ring in rings:
            points=(ring-c)/w*span/pitch+(dims-1)/2
            rr,cc=polygon(points[:,0],points[:,1],dims)
            solid[rr,cc]^=True
        return gaussian_filter(distance_transform_edt(solid)-distance_transform_edt(~solid),.9)
    fa,fb=field(a,ca,wa),field(b,cb,wb)
    count=17
    # Leave a small slice between each measured ring and the triangulated surface for exact stitching.
    t=np.linspace(.022,.978,count)
    weight=t*t*(3-2*t)
    vol=np.stack([(1-w)*fa+w*fb for w in weight],axis=-1)
    v,f,_,_=marching_cubes(vol,level=0,allow_degenerate=False)
    u=t[0]+(t[-1]-t[0])*v[:,2:3]/(count-1)
    # A linear centre path retains the direction of the adjoining rails.
    size=(1-u)*wa+u*wb
    xy=(v[:,:2]-(dims-1)/2)*pitch/span*size+(1-u)*ca+u*cb
    vertices=np.concatenate([xy,u],axis=1)
    return {'v':vertices.round(7).tolist(),'f':f.tolist()}
if __name__=='__main__':
    print(json.dumps([make(k['start'],k['end']) for k in json.load(sys.stdin)],separators=(',',':')))
