from pathlib import Path
import json, gzip, hashlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial.transform import Rotation
batch=Path(__file__).resolve().parent
inputs=json.loads((batch/'inputs.json').read_text())
project=Path(inputs['project'])
source=project/'SourceAssets/SkeletonSniperStock20261031'
def read(path):return json.loads(path.read_bytes())
data=json.load(gzip.open(source/'Review20261031/saved_geometry.json.gz','rt'))
auth=read(source/'authoring.json')['models']
receipt=read(source/'Review20261031/read_receipt.json')
mounts=read(source/'Review20261031/fit_metrics.json')
donor=read(project/'SourceAssets/SVDStockAdapter20260923/authoring.json')['meshes']['skeleton']
def unit(v):return v/np.linalg.norm(v)
def unreal(matrix):
    return {'quaternion':Rotation.from_matrix(matrix[:3,:3]).as_quat().tolist(),'translation':matrix[:3,3].tolist()}
config={}
for family in ('SVD','SVCH'):
    host=data[family]['host']; native=receipt[family]['host']
    current=project/'Content'/(native['path'][6:]+'.uasset')
    if hashlib.sha256(current.read_bytes()).hexdigest()!=native['sha256']:raise RuntimeError('Reference body changed: '+family)
    row=auth[family];forward=unit(np.array(row['source_to_host'])[:3,0])
    target=np.array([0.,np.sign(forward[1]),0.])
    frame=np.diag([100.,-100.,100.,1.])@np.array(row['export_conversion'])
    src_axis=unit(frame[:3,:3]@forward);axis=unit(frame[:3,:3]@target)
    cross=np.cross(src_axis,axis);angle=np.arctan2(np.linalg.norm(cross),src_axis@axis)
    rot=Rotation.from_rotvec(unit(cross)*angle).as_matrix()
    old_pivot=(frame@np.r_[row['front_anchor'],1.])[:3]
    item=dict(host=native['path'],reference_host_sha256=native['sha256'],axis=axis.tolist(),old_axis=src_axis.tolist(),before_degrees=float(np.rad2deg(angle)))
    if family=='SVD':
        pivot=(frame@np.r_[donor['stock_front_m'],1.])[:3]
        item['peer']='/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/Meshes/SM_SVD_skeleton'
    else:
        # Retain the native game's front trim islands from the factory character mesh.
        vertices=np.array(host['positions']);faces=np.array(host['triangles'])
        factory=next(i for i,v in enumerate(host['materials']) if v['slot']=='KVInhibitor_stock')
        ids=np.flatnonzero(np.array(host['material_ids'])==factory)
        coords,inv=np.unique(vertices[faces[ids]].reshape(-1,3).round(4),axis=0,return_inverse=True)
        fac=inv.reshape(-1,3)
        graph=coo_matrix((np.ones(fac.size),(fac.ravel(),fac[:,[1,2,0]].ravel())),shape=(len(coords),len(coords)))
        count,labels=connected_components(graph.tocsr(),directed=False)
        boundary=coords[:,1].min()+.11*np.ptp(coords[:,1])
        front=[i for i in range(count) if coords[labels==i,1].max()<=boundary]
        if not front:raise RuntimeError('Native visual collar not found')
        wide=coords[labels==max(front,key=lambda i:np.ptp(coords[labels==i,0]))]
        center=(wide.min(0)+wide.max(0))*.5
        # Overlap the visible skins along the host's longitudinal axis without changing the factory rim.
        center[1]-=.12*np.ptp(coords[np.isin(labels,front),1])
        attach=np.array(mounts[family]['stock_component_matrix'])
        inv_attach=np.linalg.inv(attach)
        pivot=(inv_attach@np.r_[center,1.])[:3]
        item.update(trim_ids=ids[np.isin(labels[fac[:,0]],front)].tolist(),factory_material=host['materials'][factory]['asset'],factory_id=factory,native_to_stock=unreal(inv_attach),host_faces=int(len(faces)))
    transform=np.eye(4);transform[:3,:3]=rot;transform[:3,3]=pivot-rot@old_pivot
    item['body_transform']=unreal(transform)
    config[family]=item
(batch/'frames.json').write_text(json.dumps(config,indent=2))
print([(k,round(v['before_degrees'],2),len(v.get('trim_ids',[]))) for k,v in config.items()])
