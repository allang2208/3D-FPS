from pathlib import Path
import json
import pickle
import sys
import numpy as np
from scipy.spatial.transform import Rotation

from seam import grip_faces

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
sys.path.insert(0, str(SOURCE))
from source_geometry import read_primitives


def key(points):
    return tuple(map(tuple, np.round(points, 4)[np.lexsort(points.T[::-1])]))


def component(points):
    return points[:, [1, 0, 2]] + [5.45, -28.6, -5.3]


def main():
    payload = pickle.load(open(SOURCE/'Wrist33/geometry.pkl', 'rb'))
    bind = payload['bind'][payload['names'].index('WPN_root')]
    axis = Rotation.from_quat(bind[3:7]).as_matrix()
    recipe = json.loads((SOURCE/'Repair13/parts_recipe.json').read_text())
    tri = np.asarray(payload['faces'])
    guard = np.asarray(payload['vertices'])[np.unique(tri[np.array(payload['sections']) == payload['slots'].index('M249_Factory_Handguard')])]
    bottom = guard[guard[:, 2] < guard[:, 2].min()+1.15]
    middle = (bottom[:, 1].min()+bottom[:, 1].max())/2
    target = np.array(recipe['interfaces_component_cm']['foregrip'])
    shift = axis.T @ [0, middle-target[1], 0]
    mounts = json.loads((SOURCE/'Wrist33/install_receipt.json').read_text())['mounts']
    deltas = {}
    for family in ('vertical','tactical_vertical','angled','canted','prism','base'):
        extra = next((row['shift_root_cm'] for path,row in mounts.items() if path.endswith('SM_M249_'+family)), [0,0,0])
        deltas[family] = (shift-extra).tolist()

    native = {name:np.load(SOURCE/('Geometry/'+name+'.npz')) for name in ['Receiver','RearGrip','Trigger']}
    native_keys = {name:{key(t):i for i,t in enumerate(spec['positions'][spec['faces']]*100)} for name,spec in native.items()}
    mi,pos,_,_,faces,labels = next(p for p in read_primitives() if p[0]==0)
    faces = faces[labels==21]
    triangles = pos[faces]*100
    keys = [key(t) for t in triangles]
    choice = grip_faces(pos,faces,np.array([k in native_keys['Trigger'] for k in keys]))
    moved = [i for i,k in enumerate(keys) if choice[i] and k in native_keys['Receiver']]
    if not moved or any(not choice[i] for i,k in enumerate(keys) if k in native_keys['RearGrip']):
        raise ValueError('Unexpected source grip partition')
    verts, weld = np.unique(np.round(pos*100,4),axis=0,return_inverse=True)
    edges={}
    for i,face in enumerate(weld[faces]):
        for a,b in zip(face,np.roll(face,-1)):
            edges.setdefault(tuple(sorted((a,b))),set()).add(bool(choice[i]))
    # The source housing is open at its guard and backstrap. Span those
    # openings with a closed rim following the outer edges on both sides.
    from scipy.spatial import ConvexHull
    boundary=np.unique([i for edge,sides in edges.items() if len(sides)==2 for i in edge])
    corners=component(verts[boundary])
    ring=corners[ConvexHull(corners[:,:2]).vertices]
    # FBX import can weld or discard an authoring triangle. Feed the editor
    # the actual resident mesh-description centroids for this section.
    from scipy.spatial import cKDTree
    native_receiver=tri[np.array(payload['sections'])==payload['slots'].index('M249_Factory_Receiver')]
    actual=np.asarray(payload['vertices'])[native_receiver].mean(1)
    dist,_=cKDTree(component(triangles[moved].mean(1))).query(actual)
    selected=actual[dist<.001]
    if not len(selected):raise ValueError('Missing native receiver faces')
    out=dict(front_deltas_root_cm=deltas,rail_y=bottom[:,1][[bottom[:,1].argmin(),bottom[:,1].argmax()]].tolist(),
             center_y=float(middle),moved_body_faces=[native_keys['Receiver'][keys[i]] for i in moved],
             component_centers=selected.tolist(),rear_ring_cm=ring.tolist(),
             root_position=bind[:3], root_rotation=axis.tolist())
    (HERE/'fit.json').write_text(json.dumps(out,separators=(',',':')))
    print('Rail',out['rail_y'],middle,'deltas',deltas,'receiver faces',len(moved),'rings',
          len(ring),ring.min(0).round(2),ring.max(0).round(2))

if __name__=='__main__':main()
