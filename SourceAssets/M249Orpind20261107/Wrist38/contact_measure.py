"""Quantify the visually suspected box crossing; native vertex IDs only."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial import ConvexHull,cKDTree

HERE=Path(__file__).resolve().parent
root=HERE.parent/'Wrist34/geometry_wrist_thirty_eight_clearance'
if len(sys.argv)>1:root=Path(sys.argv[1])
result={}
for folder in sorted(root.glob('box_*')):
    meta=json.loads((folder/'geometry.json').read_text());rows=json.loads((folder/'review.json').read_text())['frames']
    dominant=np.fromfile(folder/'dominant.bin',np.uint32);names=meta['bones'];slots=meta['slots']
    offset=.9 if 'empty' in folder.name else 0
    allrows=[]
    for row in rows:
        if row['source']<4.19-offset:continue
        stem=folder/Path(row['file']).stem
        p=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)
        tri=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3)
        mats=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        handids=np.unique(tri[mats==slots.index('Skin_Hand')]);handids=handids[np.array([names[dominant[i]].endswith('_r') for i in handids])]
        boxids=np.unique(tri[mats==slots.index('M249_Surface__NewBox')])
        planes=ConvexHull(p[boxids]).equations
        margins=np.max(p[handids]@planes[:,:3].T+planes[:,3],axis=1)
        beltfaces=tri[(mats==slots.index('FeedCase__NewBelt'))&(dominant[tri]==names.index('New_PKM_Belt_00')).all(axis=1)]
        tree=cKDTree(p[np.unique(beltfaces)])
        gaps={digit:float(tree.query(p[dominant==names.index(digit)])[0].min()) for digit in ['index_03_r','thumb_03_r']}
        allrows.append(dict(source=row['source'],hand_box_hull_min_cm=float(margins.min()),
                            native_hand_vertices_inside_box_hull=int((margins<-.05).sum()),tip_vertex_gaps_cm=gaps))
    result[folder.name]=allrows
output=Path(sys.argv[2]) if len(sys.argv)>2 else HERE/'contact_measurements_clearance.json'
output.write_text(json.dumps(result,indent=2))
for name,rows in result.items():
    worst=min(rows,key=lambda r:r['hand_box_hull_min_cm'])
    print(name,worst)
