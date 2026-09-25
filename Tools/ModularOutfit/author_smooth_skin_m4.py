"""Constrained surface fairing of the original hand; native skin weights stay intact.

Local quadratic patches suppress sewn/padded glove relief without shrinking
fingers. Contact-facing surfaces, fingertip caps and the forearm join are pinned.
Normals are rebuilt across UV splits instead of retaining glove hard shading.
"""
import json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4')
ROOT=BASE/'SmoothSkinV2';ROOT.mkdir(exist_ok=True)
source=json.loads((BASE/'M4_original.json').read_text())
shape=json.loads((BASE/'M4_bare_shape.json').read_text())
P=np.asarray(source['positions'],dtype=np.float64);T=np.asarray(source['triangles'])
M=np.asarray(shape['triangle_materials']);hand=np.asarray(shape['hand_vertices'])
H=np.unique(T[M==2])
material_boundary=set(T[M!=2].ravel())
_,first,inv=np.unique(np.round(P[H],5),axis=0,return_index=True,return_inverse=True)
representatives=H[first];base=P[representatives].copy();U=len(base)
native_to_unique=np.full(len(P),-1,np.int32);native_to_unique[H]=inv
skin_faces=T[M==2];faces=native_to_unique[skin_faces]
source_face_n=np.mean(np.asarray(source['normals'])[M==2],axis=1)
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def normals(points):
    a,b,c=(points[faces[:,i]] for i in range(3));cross=np.cross(b-a,c-a)
    cross*=np.where(np.sum(cross*source_face_n,axis=1)>=0,1.,-1.)[:,None]
    out=np.zeros_like(points)
    for k in range(3):np.add.at(out,faces[:,k],cross)
    return unit(out)
n0=normals(base)
stems=('thumb','index','middle','ring','pinky')
labels=[];back=[];axes=[];wrist=[];tip=[]
for i,p in zip(representatives,base):
    side='l' if p[0]<0 else 'r';frame=shape['anatomy'][side]
    weights=source['weights'][int(i)]
    strength=[sum(w for name,w in weights.items() if name.startswith(stem+'_') and '_metacarpal_' not in name) for stem in stems]
    stem=stems[int(np.argmax(strength))] if max(strength)>.3 else ''
    bone=max(weights,key=weights.get)
    row=next((r for r in frame['digits'] if r['bone']==bone),None)
    d=np.asarray(row['dorsal'] if row else frame['dorsal'])
    axis=np.asarray(row['axis'] if row else frame['forward'])
    labels.append((side,stem));back.append(d);axes.append(axis)
    wrist.append((p-np.asarray(frame['wrist']))@frame['forward'])
    tip.append(bool(row and row['segment']==3 and (p-row['head'])@axis>.86*row['length']))
back=np.asarray(back);axes=np.asarray(axes);wrist=np.asarray(wrist)
# Smooth contact masks replace the previous arbitrary two-ring panel-edge locks.
facing=np.sum(n0*back,axis=1)
amount=smooth(-.12,.62,facing)*smooth(-.35,.70,wrist)
amount[np.asarray(tip)]=0
limits=np.array([.09 if label[1] else .14 for label in labels])*amount # centimetres
for j,vi in enumerate(representatives):
    if not hand[vi] or vi in material_boundary:limits[j]=0
for i,p in enumerate(base):
    side=labels[i][0];thumb=np.asarray(source['bones']['thumb_01_'+side]['position'])
    limits[i]*=smooth(1.9,3.1,np.linalg.norm(p-thumb))

points=base.copy();tree=cKDTree(base)
radii=np.array([.44 if label[1] else .72 for label in labels])
neighborhoods=tree.query_ball_point(base,radii)
for iteration in range(6):
    N=normals(points);updated=points.copy()
    for i,near in enumerate(neighborhoods):
        if limits[i]<1e-8:continue
        # Same finger or palm transition only; never bridge a finger gap.
        ids=np.asarray([j for j in near if labels[j][0]==labels[i][0] and
            (labels[j][1]==labels[i][1] or not labels[j][1] or not labels[i][1])],dtype=int)
        delta=points[ids]-points[i];agreement=N[ids]@N[i]
        select=(agreement>.18)&(np.abs(delta@N[i])<radii[i]*.65)
        ids=ids[select];delta=delta[select];agreement=agreement[select]
        if len(ids)<10:continue
        tangent=axes[i]-N[i]*(axes[i]@N[i])
        if np.linalg.norm(tangent)<.05:tangent=np.cross(N[i],[0,0,1])
        tangent=unit(tangent);bitangent=np.cross(N[i],tangent)
        x=delta@tangent;y=delta@bitangent;z=delta@N[i]
        w=np.exp(-np.sum(delta*delta,axis=1)/(radii[i]*.58)**2)*agreement**2
        design=np.stack((np.ones_like(x),x,y,x*x,x*y,y*y),axis=1)
        regular=np.diag([1e-8,1e-6,1e-6,2e-4,2e-4,2e-4])
        fit=np.linalg.solve((design.T*w)@design+regular,(design.T*w)@z)
        move=N[i]*fit[0]*.74
        # No axial movement along a finger: preserve its length and joint centres.
        if labels[i][1]:move-=axes[i]*(move@axes[i])
        total=points[i]+move-base[i]
        length=np.linalg.norm(total)
        if length>limits[i]:total*=limits[i]/length
        updated[i]=base[i]+total
    points=updated

# Rebuild continuous skin shading, including pinned contact regions. Proximity
# averaging smooths split glove panels but rejects opposite surfaces/digits.
geometric=normals(points);smoothed=geometric.copy();tree=cKDTree(points)
for i,ids in enumerate(tree.query_ball_point(points,.30)):
    ids=np.asarray([j for j in ids if labels[j][0]==labels[i][0] and
        (labels[j][1]==labels[i][1] or not labels[j][1] or not labels[i][1])],dtype=int)
    agreement=geometric[ids]@geometric[i]
    w=np.exp(-np.sum((points[ids]-points[i])**2,axis=1)/.0225)*smooth(.05,.75,agreement)
    smoothed[i]=unit(np.sum(geometric[ids]*w[:,None],axis=0))
newP=P.copy();newP[H]=points[inv]
normal_list=np.asarray(source['normals']).copy()
normal_list[M==2]=smoothed[faces]
# Keep the source normals at the actual forearm join to avoid an artificial ring.
join=1-smooth(-.25,.55,wrist)
for ti in np.flatnonzero(M==2):
    for corner,vi in enumerate(T[ti]):
        factor=join[native_to_unique[vi]]
        normal_list[ti,corner]=unit(normal_list[ti,corner]*(1-factor)+np.asarray(source['normals'][ti][corner])*factor)
shape['positions']=newP.tolist();shape['normals']=normal_list.tolist()
shape['geometry_policy']={'method':'six constrained quadratic surface passes; continuous skin normals',
 'dorsal_limit_mm':1.4,'finger_limit_mm':.9,'contact_vertices_frozen':True,
 'original_weights_retained':True,'original_uv_retained':True,'forearm_and_sleeve_unchanged':True,
 'glove_split_normals_retained':False}
(ROOT/'M4_bare_shape.json').write_text(json.dumps(shape,separators=(',',':')))
shutil.copyfile(BASE/'M4_original.json',ROOT/'M4_original.json')
# Production record, not an animation/visual acceptance report.
distance=np.linalg.norm(newP-P,axis=1)*10
(ROOT/'authoring.json').write_text(json.dumps({'method':shape['geometry_policy'],
 'moved_vertices':int(np.count_nonzero(distance>1e-5)),'max_displacement_mm':float(distance.max()),
 'original_weights_rebound':False,'animation_assets_changed':False,'runtime_tested':False},indent=2))
print('M4_SMOOTH_SKIN_SURFACE_AUTHORED',int(np.count_nonzero(distance>1e-5)))
