"""Compare the installed source LODs against the pre-normal-edit capture."""
import collections, gzip, json, math
from pathlib import Path

OUT=Path(__file__).resolve().parent
with gzip.open(OUT.parent/'M24SurfaceRefine20261101/inputs.json.gz','rt',encoding='utf-8') as f:
    before=json.load(f)
with gzip.open(OUT/'inputs.json.gz','rt',encoding='utf-8') as f:
    after=json.load(f)

def faces(lod):
    vertices=[tuple(round(c,5) for c in v) for v in lod['positions']]
    result=collections.Counter()
    for face,material in zip(lod['triangles'],lod['material_ids']):
        corners=tuple(vertices[i] for i in face)
        # Reindexing is harmless; preserve triangle winding and material ID.
        result[(min(corners,corners[1:]+corners[:1],corners[2:]+corners[:2]),material)]+=1
    return result

rows=[]
for key in ('skeleton_front','skeleton_seat'):
    for old,new in zip(before['meshes'][key]['lods'],after['meshes'][key]['lods']):
        a,b=faces(old),faces(new)
        normals=[v for tri in new['normals'].values() for v in tri]
        invalid=sum(not all(math.isfinite(c) for c in v) or abs(sum(c*c for c in v)-1)>0.002 for v in normals)
        basis=new['basis']
        row={'mesh':key,'lod':new['index'],'triangles':len(new['triangles']),
             'geometry_and_material_ids_equal':a==b,'missing_faces':sum((a-b).values()),'added_faces':sum((b-a).values()),
             'uv_channel_count_unchanged':old['uv_channels']==new['uv_channels'],
             'invalid_corner_normals':invalid,'basis':basis,'build_settings':new['build_settings']}
        row['passed']=a==b and row['uv_channel_count_unchanged'] and not invalid and not any(basis[k] for k in ('invalid_triangles','zero_vectors','nonfinite_vectors')) and basis['max_normal_tangent_dot']<0.002
        rows.append(row)
report={'passed':all(r['passed'] for r in rows),'rows':rows,
        'scope':'All source LOD triangles, winding, material IDs, UV channel count, normal and tangent validity. Does not compare UV coordinates or rendered appearance.'}
(OUT/'geometry_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
