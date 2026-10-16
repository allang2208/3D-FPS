"""Read-only authored mesh and combination-clearance checks requested by user."""
import bpy,json,math
from pathlib import Path
from collections import Counter
O=Path(__file__).parent;P=O.parents[1]
source=P/'SourceAssets/Super90DuckbillClosedSides20261016/ShotgunDuckbill_ClosedSides_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));rows=[]
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
for obj in objects:
    counts=Counter()
    for poly in obj.data.polygons:
        for edge in poly.edge_keys:counts[tuple(sorted(edge))]+=1
    rows.append({'object':obj.name,'faces':len(obj.data.polygons),'edges_not_two_sided':sum(n!=2 for n in counts.values()),
        'has_uv':bool(obj.data.uv_layers),'materials':[m.name for m in obj.data.materials]})
# Use the actual cosmetic extension profile and the accepted native seating
# transform to compare surface heights at overlapping longitudinal stations.
profile=[(.4742,.01410),(.4748,.01414),(.4765,.01310),(.4898,.01310),(.494,.0122),(.501,.0107),
         (.507,.0100),(.621,.0100),(.633,.0125),(.6394,.01414),(.6400,.01414)]
seat_forward=.499307;seat_z=-.7443155;tube_z=-.77279532
def radius(y):
    for (a,r),(b,s) in zip(profile,profile[1:]):
        if a<=y<=b:return r+(s-r)*(y-a)/(b-a)
    return None
gaps=[]
for obj in objects:
    for vertex in obj.data.vertices:
        p=obj.matrix_world@vertex.co;r=radius(seat_forward+p.x)
        if r is not None and abs(p.y)<=r:
            tube_top=tube_z+math.sqrt(max(0,r*r-p.y*p.y))
            gaps.append(seat_z+p.z-tube_top)
walls=[r for r in rows if r['object'].startswith('ClosedSidePanel_')]
passed=len(walls)==2 and all(r['edges_not_two_sided']==0 and r['has_uv'] for r in rows) and min(gaps)>0
report={'passed':passed,'source':str(source),'objects':rows,'closed_side_panels':len(walls),
    'minimum_sampled_clearance_to_extended_tube_cm':min(gaps)*100,
    'clearance_scope':'authored vertices against known tube outer profile at the common native mount; not in-game collision or rendered acceptance',
    'runtime_mesh_path':'/Game/Weapons/CommonShotgun/DuckbillV2_20261016/Meshes/SM_ShotgunDuckbillV2'}
(O/'geometry_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('SHOTGUN_GEOMETRY_RESULT',passed,min(gaps)*100)
