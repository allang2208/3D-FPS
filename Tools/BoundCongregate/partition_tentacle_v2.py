"""Anatomical surface partition; the face contact is a real welded bridge."""
from pathlib import Path
import json,numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'TentacleRepairV2'
d=np.load(OUT/'diagnostic_surface.npz');v=d['vertices'];tri=d['triangles']
# Landmarks from measured original mesh sections, in the original GLB frame.
landmarks=[
 [.377,.063,.218,.117],[.391,.065,.295,.090],[.347,.070,.387,.082],
 [.259,.079,.459,.066],[.146,.078,.490,.047],[.037,.046,.482,.038],
 [-.065,.010,.444,.029],[-.123,-.026,.402,.025],[-.104,-.046,.368,.020],
 [-.054,-.062,.375,.020],[-.012,-.078,.366,.018],[-.003,-.0966,.345,.018],
 [-.00686,-.12055,.320,.018],[-.0258,-.14671,.295,.018],[-.07095,-.16317,.270,.018],
 [-.11702,-.1755,.245,.019],[-.14615,-.19464,.220,.019],[-.16375,-.22298,.195,.019],
 [-.17232,-.24913,.170,.019],[-.17238,-.27168,.145,.019],[-.1655,-.29396,.120,.019],
 [-.14831,-.33121,.095,.019],[-.1216,-.37793,.070,.019],[-.09349,-.42234,.045,.019],
 [-.07199,-.45006,.020,.020],[-.06105,-.46205,-.005,.021],[-.05611,-.47043,-.030,.021],
 [-.05485,-.47553,-.055,.021],[-.054,-.477,-.080,.021],[-.055,-.477,-.130,.021],
 [-.057,-.476,-.180,.021],[-.049,-.473,-.225,.021],[-.03961,-.47016,-.255,.021],
 [-.02895,-.47260,-.280,.021],[-.01539,-.47222,-.305,.021],[.00582,-.47316,-.330,.021],
 [.03358,-.48038,-.355,.021],[.05827,-.48431,-.380,.021],[.0703,-.48658,-.405,.020],
 [.06961,-.48996,-.430,.018],[.030,-.497,-.453,.015],[-.027,-.516,-.465,.014],
 [-.07198,-.55043,-.480,.013],[-.076,-.590,-.490,.012],[-.06412,-.62227,-.480,.012],
 [-.029,-.626,-.488,.011],[-.020,-.578,-.500,.010],[-.02298,-.50306,-.505,.010],
 [.028,-.471,-.514,.009],[.070,-.474,-.519,.009],[.100,-.475,-.524,.006]]
p=np.array(landmarks);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:3],axis=0),axis=1))]
inter=PchipInterpolator(s,p,axis=0);curve=inter(np.linspace(0,s[-1],1400));tree=cKDTree(curve[:,:3])
centers=v[tri].mean(1);distance,near=tree.query(centers);radius=curve[near,3]
mask=(distance<radius*1.35+.006)
# The broad organ attaches above the flank. The lower stump remains body.
mask &= ~((centers[:,0]>.20)&(centers[:,2]<.220))
# The narrow front strand is welded into the lip between these levels. Keep
# its visible front half; each side receives its own closed underside patch.
contact=(centers[:,2]<-.06)&(centers[:,2]>-.247)&(centers[:,0]<0)
mask[contact] &= centers[contact,1]<-.467
# Retain only the appendage component. The spatial corridor is a selector,
# not a new substitute tube; original surface triangles remain the render mesh.
chosen=tri[mask];edges=np.sort(np.concatenate([chosen[:,:2],chosen[:,1:],chosen[:,[0,2]]]),axis=1)
g=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
_,labels=connected_components(g);selected_label=labels[v[:,2].argmax()]
mask &= np.all(labels[tri]==selected_label,axis=1)
# Recover the complete original surface on either side of the weld, including
# the tightly curled tip that a spatial tube corridor alone can clip away.
# Region growth is bounded by the two real anatomical cut lines only.
all_edges=np.unique(np.sort(np.concatenate([tri[:,:2],tri[:,1:],tri[:,[0,2]]]),axis=1),axis=0)
mid=v[all_edges].mean(1)
root_cross=((v[all_edges[:,0],2]>.220)!=(v[all_edges[:,1],2]>.220))&(mid[:,0]>.20)
lip_cross=((v[all_edges[:,0],1]<-.467)!=(v[all_edges[:,1],1]<-.467))&(mid[:,2]<-.059)&(mid[:,2]>-.248)&(mid[:,0]>-.13)&(mid[:,0]<.015)
allowed=all_edges[~(root_cross|lip_cross)]
g=coo_matrix((np.ones(len(allowed)*2),(np.r_[allowed[:,0],allowed[:,1]],np.r_[allowed[:,1],allowed[:,0]])),shape=(len(v),len(v))).tocsr()
_,labels=connected_components(g);component=labels==labels[v[:,2].argmax()]
print('Anatomical component',int(component.sum()),flush=True)
if component.sum()<20000:
    mask=np.mean(component[tri],axis=1)>.5
mesh=trimesh.Trimesh(v,tri,process=False);adj=mesh.face_adjacency
graph=coo_matrix((np.ones(len(adj)*2),(np.r_[adj[:,0],adj[:,1]],np.r_[adj[:,1],adj[:,0]])),shape=(len(tri),len(tri))).tocsr()
degree=np.asarray(graph.sum(1)).ravel()
for _ in range(3):
    votes=np.asarray(graph@mask.astype(float)).ravel()
    mask=np.where(votes>=degree-.1,True,np.where(votes<.1,False,mask))
# The only body component to keep is the connected torso. Residual narrow
# backside islands of the distal tube belong with the organ, not the mouth.
for selected in [False,True]:
    indices=np.flatnonzero(mask==selected);sub=graph[indices][:,indices]
    _,labels=connected_components(sub);sizes=np.bincount(labels);main=sizes.argmax()
    if not selected:
        small=indices[labels!=main];mask[small]=True
    else:
        small=indices[labels!=main];mask[small]=False
np.savez_compressed(OUT/'partition.npz',face_mask=mask,curve=curve,curve_s=np.linspace(0,s[-1],1400))
fig,axes=plt.subplots(1,3,figsize=(18,8))
for ax,(a,b),title in zip(axes,[(0,2),(1,2),(0,1)],['Front XZ','Side YZ','Top XY']):
    ax.scatter(centers[::2,a],centers[::2,b],s=.25,c='#77818a',alpha=.5)
    ax.scatter(centers[mask,a],centers[mask,b],s=.5,c='#ef5b45')
    ax.plot(curve[:,a],curve[:,b],lw=.6,c='black');ax.set_aspect('equal');ax.set_title(title)
fig.tight_layout();fig.savefig(OUT/'partition.png',dpi=160)
print('Selected faces',mask.sum(),'length cm',s[-1]*225,flush=True)
