"""Stone-wall LOD0 geometry in UE centimetres, including pitch/roll support."""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
GEOMETRY = ROOT/'SourceAssets/TemperateHillsVillage/WallSupport20261114/Geometry'

def load_mesh(name):
    vertices, triangles = [], []
    for line in (GEOMETRY/(name+'.obj')).read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == 'v':
            # UnrealEd's OBJ exporter writes X,Z,Y (EditorExporters.cpp).
            x,z,y = map(float,fields[1:4]); vertices.append((x,y,z))
        elif fields and fields[0] == 'f':
            triangles.append([int(f.split('/')[0])-1 for f in fields[1:4]])
    return np.asarray(vertices),np.asarray(triangles)

def rotate_vertices(vertices, rotation):
    # FRotationMatrix: row vectors, pitch/yaw/roll in Unreal's left-handed frame.
    pitch,yaw,roll = np.radians(rotation)
    sp,sy,sr = np.sin([pitch,yaw,roll]); cp,cy,cr = np.cos([pitch,yaw,roll])
    matrix = np.array([[cp*cy,cp*sy,sp],
        [sr*sp*cy-cr*sy,sr*sp*sy+cr*cy,-sr*cp],
        [-(cr*sp*cy+sr*sy),cy*sr-cr*sp*sy,cr*cp]])
    return vertices @ matrix

def bottom_profile(vertices, triangles, step=2.):
    """Actual triangle lower envelope across the wall's long axis, not its box."""
    tri=vertices[triangles][:,:,[0,2]]
    xs=np.arange(vertices[:,0].min()+step*.5,vertices[:,0].max(),step)
    lows=np.full(len(xs),np.inf)
    for a,b in ((0,1),(1,2),(2,0)):
        x0,z0=tri[:,a,0],tri[:,a,1]; x1,z1=tri[:,b,0],tri[:,b,1]
        for i,x in enumerate(xs):
            valid=(x>=np.minimum(x0,x1))&(x<=np.maximum(x0,x1))&(abs(x1-x0)>1.e-6)
            if valid.any():
                z=z0[valid]+(z1[valid]-z0[valid])*(x-x0[valid])/(x1[valid]-x0[valid])
                lows[i]=min(lows[i],float(z.min()))
    return xs,lows

if __name__=='__main__':
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    names=sorted(p.stem for p in GEOMETRY.glob('*Piece*.obj') if '_Internal' not in p.stem)
    fig,axes=plt.subplots(4,4,figsize=(20,13),layout='constrained')
    for i,name in enumerate(names):
        v,f=load_mesh(name)
        for j,roll in enumerate((0,180)):
            q=rotate_vertices(v,[0,0,roll]); x,b=bottom_profile(q,f)
            ground=float(np.quantile(b[np.isfinite(b)],.9)+8)
            ax=axes[i//2,(i%2)*2+j]
            ax.add_collection(PolyCollection(q[f][:,:,[0,2]],facecolor='#626751',edgecolor='none'))
            ax.plot(x,b,color='#ee9944',linewidth=.9)
            ax.axhline(ground,color='red');ax.fill_between([q[:,0].min()-10,q[:,0].max()+10],-140,ground,color='#99805d',alpha=.25)
            ax.set_title(name.replace('SM_H_StoneWall_00A_','')+' roll '+str(roll))
            ax.set_xlim(q[:,0].min()-10,q[:,0].max()+10);ax.set_ylim(-140,140);ax.set_aspect('equal')
            print(name,roll,'height',round(q[:,2].max()-ground,1),'burial',round(ground-q[:,2].min(),1))
    fig.savefig(GEOMETRY.parent/'source-profiles.png',dpi=120)
