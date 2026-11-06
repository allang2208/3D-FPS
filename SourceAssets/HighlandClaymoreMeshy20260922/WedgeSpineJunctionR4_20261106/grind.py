"""Physical grind rails, in mm, traced from the front and three-quarter drawings."""
import numpy as np

PINS=np.array([0,.15,.22,.275,.36,.425,.485,.677,1.])
Z=np.array([16,29,47,69,85,115,162,221,312,480,640,775,900,975,1034,1070,1100.])
# The flute edges follow their own lines through the shoulder. Only the cheeks
# flare sideways. Keeping these paths separate is essential around the plait.
X=np.array([
[0,8,11,14,18,21,24,32,45],[0,9,12,15,19,22,27,38,56],
[0,9,12,15,20,23,30,44,64],[0,9,12,16,21,24,32,56,82.5],
[0,9,12,16,21,24,30,48,71],[0,9,12,16,21,23,28,40,58],
[0,8.6,11.6,15.2,20.2,22.4,26,34.7,49.7],[0,8,10.8,14.1,19.2,21.5,24.2,31.4,45.7],
[0,6.3,8.8,12.3,17.7,20.2,22.9,29.1,42.3],[0,3.5,5.6,8.7,14.1,16.5,19.6,25.3,37.6],
[0,2.1,3.3,5.2,9.2,11.3,15.4,21.1,33.9],[0,1.8,2.7,4.4,7.3,9.1,13.3,18.7,29.8],
[0,1.4,2.4,3.6,6.4,7.8,11.6,16.4,26.3],[0,1.3,2.0,3.1,5.6,6.8,10.2,14.6,23.4],
[0,.9,1.6,2.5,4.1,5.1,7.7,10.8,17.5],[0,.45,.7,1.3,2.2,2.8,4.1,5.8,9.4],
[0,0,0,0,0,0,0,0,0]])
Y=np.array([
[7,6.5,6.3,6.1,5.8,6,6,5,1.3],[10,9,9.6,7.7,7.2,8.65,9.1,7.7,1.15],
[13,10.8,11.3,7.1,6.1,9.9,11.5,9.1,.75],[15,11.4,12.2,7.0,5.7,10.3,11.4,9.35,.18],
[15,11.5,12.3,7.0,5.75,10,10.9,8.1,.16],[14.4,11.5,12,6.8,5.8,9.6,10.1,6.5,.15],
[13.7,11.2,11.7,6.6,5.5,9.05,9.7,5.9,.14],[13.2,10.9,11.4,6.4,5.3,8.6,9.25,5.75,.14],
[12.8,10.6,11.1,6.1,5.15,8.05,8.65,5.4,.13],[12.3,10.8,11.,6.7,5.6,7.8,7.8,4.9,.12],
[11.1,10.5,10.5,8.3,7.15,7.8,6.4,4.,.11],
*[np.zeros(9) for _ in range(6)]])
for i,h in zip(range(11,16),(10.5,9.4,8.2,5.9,3.25)):
    Y[i]=h*(1-X[i]/X[i,-1])+.11*X[i]/X[i,-1]

def ease(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

def longitudinal(values):
    delta=np.diff(values,axis=0)/np.diff(Z)[:,None]
    slopes=np.zeros_like(values,dtype=float)
    slopes[0],slopes[-1]=delta[0],delta[-1]
    for i in range(1,len(Z)-1):
        a,b=delta[i-1],delta[i]
        take=a*b>0.
        slopes[i,take]=2*a[take]*b[take]/(a[take]+b[take])
    def sample(z):
        i=min(len(Z)-2,max(0,np.searchsorted(Z,z,side='right')-1))
        length=Z[i+1]-Z[i]
        t=(z-Z[i])/length
        m0,m1=slopes[i],slopes[i+1]
        # Separate the two tangents at the scallop tip to make a deliberate cusp.
        if values is X and i in (2,3):
            if i==2:
                m1=m1.copy();m1[-1]=delta[i,-1]*1.28
            else:
                m0=m0.copy();m0[-1]=delta[i,-1]*1.30
        return ((2*t**3-3*t*t+1)*values[i]+(t**3-2*t*t+t)*length*m0+
                (3*t*t-2*t**3)*values[i+1]+(t**3-t*t)*length*m1)
    return sample
xs,ys=longitudinal(X),longitudinal(Y)

def broadside(z,p):
    xp,yp=xs(z),ys(z)
    x=np.interp(p,PINS,xp)
    y=np.interp(p,PINS,yp)
    # Form real, constant-width fillets between the blade planes. The rounded
    # crest reflects a continuous strip of light as the sword turns in hand.
    if z<775:
        for j,radius in ((2,.45),(5,.58),(6,.55),(7,.70)):
            radius=min(radius,.36*(xp[j]-xp[j-1]),.36*(xp[j+1]-xp[j]))
            d=x-xp[j]
            if abs(d)<radius:
                left=(yp[j]-yp[j-1])/(xp[j]-xp[j-1])
                right=(yp[j+1]-yp[j])/(xp[j+1]-xp[j])
                y+=(right-left)*((d+radius)**2/(4*radius)-max(0.,d))*(1-ease(620,775,z))
    if .22<p<.425 and z<775:
        i=np.searchsorted(PINS,p)-1
        f=(p-PINS[i])/(PINS[i+1]-PINS[i])
        # Radiused channel floor, separate from the crisply lipped arrises.
        y-=np.sin(np.pi*f)**2*(.34 if i in (2,4) else .22)*(1-ease(550,775,z))
    wing=ease(.43,.68,p)
    k=ease(16,69,z)*(1-ease(69,160,z))
    arc=np.interp(p,PINS,[0,-3,-8,-11,-14,-18,-14,8,0])
    zz=z+k*arc
    # A bowed grind line separates the scalloped underside and the polished
    # upper cutting face. It dies into the shoulder's cutting cusp at the edge.
    crown=2.10*(1-ease(0.,26. if z<69 else 38.,abs(z-69.)))
    y+=crown*wing*(1-ease(.74,1.,p))
    zz+=ease(775,975,z)*(1-ease(975,1100,z))*(1-p)*13.
    return np.array([x,y,zz])*.001
