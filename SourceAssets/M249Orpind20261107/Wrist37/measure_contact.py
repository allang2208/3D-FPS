"""Measure native runtime vertices by native bone IDs, never author vertex IDs.

These nearest-surface distances supplement the two-sided image review. They do
not establish a grasp by themselves and are not a penetration proof.
"""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial import cKDTree
root=Path(sys.argv[1]);out=[]
for folder in sorted(root.glob('box_*_base')):
    meta=json.loads((folder/'geometry.json').read_text());rows=json.loads((folder/'review.json').read_text())['frames']
    dominant=np.fromfile(folder/'dominant.bin',np.uint32);names=meta['bones']
    offset=.9 if 'empty' in folder.name else 0
    for time in [4.52-offset,4.8-offset,5.1-offset]:
        row=min(rows,key=lambda x:abs(x['source']-time));stem=folder/Path(row['file']).stem
        vertices=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)
        triangles=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3)
        material=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        case_material=meta['slots'].index('FeedCase__NewBelt')
        case_triangles=triangles[(material==case_material)&(dominant[triangles]==names.index('New_PKM_Belt_00')).all(axis=1)]
        case_ids=np.unique(case_triangles)
        if not len(case_ids):raise RuntimeError('Missing leading cartridge case')
        tree=cKDTree(vertices[case_ids]);digits={}
        for digit in ['index_03_r','thumb_03_r']:
            ids=np.flatnonzero(dominant==names.index(digit));distance,index=tree.query(vertices[ids]);k=int(distance.argmin())
            digits[digit]={'native_vertex':int(ids[k]),'case_vertex':int(case_ids[index[k]]),'nearest_vertex_gap_cm':float(distance[k]),'digit_vertex_count':len(ids)}
        out.append({'case':folder.name,'source':row['source'],'native_vertex_count':len(vertices),'digits':digits})
(root/'right_contact_measurements.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
