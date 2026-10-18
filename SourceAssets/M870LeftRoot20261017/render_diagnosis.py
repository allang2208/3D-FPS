"""Targeted offline surface comparison, not a UE gameplay screenshot."""
from fit_guard import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

def full_skin(data,p):
    v=np.array(data['positions']);hp=np.c_[v,np.ones(len(v))];out=np.zeros_like(v)
    for n,t in data['rest'].items():
        ws=np.array([row.get(n,0.) for row in data['weights']]);ids=np.flatnonzero(ws>0)
        if len(ids):out[ids]+=(hp[ids]@(p[n]@np.linalg.inv(mat(t))).T)[:,:3]*ws[ids,None]
    return out
def draw(ax,pc,title):
    polygons=[];colours=[];depth=[]
    for data,colour,allowed in [(N,np.array([.23,.25,.27]),{0,4,5,6}),(S,np.array([.53,.56,.59]),None)]:
        v=full_skin(data,pc);f=np.array(data['triangles'])
        if allowed is not None:f=f[np.isin(data['triangle_materials'],list(allowed))]
        t=v[f];t=t[(t[:,:,0]>.5).all(1)]
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-9)
        light=np.clip(.7+.25*(normal@unit(np.array([-1,-.3,1]))),.35,.95)
        uv=np.stack((t[:,:,1]/(t[:,:,0]*th),t[:,:,2]/(t[:,:,0]*tv)),axis=-1)
        polygons.extend(uv);colours.extend(light[:,None]*colour);depth.extend(t[:,:,0].mean(1))
    order=np.argsort(depth)[::-1];ax.add_collection(PolyCollection(np.array(polygons)[order],facecolors=np.array(colours)[order],edgecolors='none'))
    rim=skin(pc,G['shirt']);good=rim[:,0]>.5;rim=rim[good]
    ax.scatter(rim[:,1]/(rim[:,0]*th),rim[:,2]/(rim[:,0]*tv),s=3,c='#d55750',zorder=5)
    ax.set_xlim(-1,1);ax.set_ylim(-1,1);ax.set_facecolor('#e7edf1');ax.set_title(title,fontsize=11);ax.set_xticks([]);ax.set_yticks([])
fig,axes=plt.subplots(2,2,figsize=(14,6.3))
for row,(role,time,label) in enumerate([('inspect',.4333333333,'Inspect'),('reload_full',6.6666666,'Reload recovery')]):
    i=int(np.argmin(abs(np.array(D['clips'][role]['times'])-time)));c=camera();pc={n:c@m for n,m in existing_clearance(support(decode(role)[i]),c).items()}
    draw(axes[row,0],pc,label+' — before')
    delta,angle=correction(pc);after={n:delta@m if n in arm else m for n,m in pc.items()}
    draw(axes[row,1],after,label+f' — after ({np.rad2deg(angle):.1f}° arm retreat)')
fig.suptitle('Offline skinned-surface diagnosis · red points: left shoulder opening',fontsize=13)
fig.tight_layout();fig.savefig(O/'shoulder_comparison.png',dpi=145);plt.close(fig)
print('M870_ROOT_PREVIEW_SAVED',flush=True)
