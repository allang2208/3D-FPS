"""Check the reconstructed shaft against the seven currently routed trouser hems."""
import hashlib,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
d=read(R/'Authored/ue_leather_boots/Jason.json');p=np.asarray(d['positions']);f=np.asarray(d['triangles']);slots=np.asarray(d['triangle_materials']);ids=[]
for part in d['parts']:
    if part['name'].startswith('BootFoundation'):
        ids.extend(range(part['first_triangle'],part['first_triangle']+part['outer_surface_triangles']))
tree=BVHTree.FromPolygons([Vector(v) for v in p],f[ids].tolist(),all_triangles=True);normals=np.mean(np.asarray(d['normals'])[ids],axis=1)
old=read(PREVIOUS/'Authored/ue_leather_boots/Jason.json');op=np.asarray(old['positions']);of=np.asarray(old['triangles']);os=np.asarray(old['triangle_materials']);oi=[]
for part in old['parts']:
    if part['name'].startswith('LeatherShaftWithInnerWall'):oi.extend(i for i in range(part['first_triangle'],part['first_triangle']+part['triangles']) if os[i] in (1,4))
otree=BVHTree.FromPolygons([Vector(v) for v in op],of[oi].tolist(),all_triangles=True);on=np.mean(np.asarray(old['normals'])[oi],axis=1)
inv=read(P/'SourceAssets/PantsCompatibility20261022/inventory.json');lookup={x['asset']:x for x in inv['meshes']};routes=read(R/'inputs.json')['pants_routes'];rows=[]
for item,rigs in routes.items():
    if not rigs or not rigs.get('Jason'):continue
    asset=rigs['Jason'];row=lookup[asset];disk=P/'Content'/(asset.split('.')[0][6:]+'.uasset');assert hashlib.sha256(disk.read_bytes()).hexdigest()==row['asset_sha256'],asset
    if row.get('capture'):file=row['capture']
    else:
        assert item=='ue_leather_pants';file=P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3/Integration20261022/Authored/ue_leather_pants/Jason_HighBootsFit.json'
    pants=read(file);points=np.asarray(pants['positions']);points=points[(points[:,2]>18)&(points[:,2]<37.3)];distances=[];previous=[]
    for q in points:
        near,_,i,_=tree.find_nearest(Vector(q));distances.append(float((q-np.asarray(near))@normals[i]));near,_,i,_=otree.find_nearest(Vector(q));previous.append(float((q-np.asarray(near))@on[i]))
    maximum=max(distances) if distances else None
    rows.append(dict(item=item,asset=asset,sampled_vertices=len(points),maximum_outward_distance_cm=maximum,previous_maximum_outward_distance_cm=max(previous) if previous else None,maximum_increase_cm=max(np.maximum(distances,0)-np.maximum(previous,0)) if previous else None,worst_point=points[np.argmax(distances)].tolist() if distances else None,scope='Reference-pose calf/hem envelope comparison; existing overlaps are not treated as newly introduced clipping'))
assert all(x['maximum_outward_distance_cm'] is None or x['maximum_outward_distance_cm']<.12 for x in rows),rows
write(R/'trouser_fit_check.json',dict(completed=True,rows=rows,runtime_tested=False));print('TAILORED_BOOT_CURRENT_HEM_FITS_CHECKED',rows,flush=True)
