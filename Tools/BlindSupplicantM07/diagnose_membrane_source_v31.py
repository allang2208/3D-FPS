"""Requested source diagnosis: proxy islands, pins, thin triangles and seams."""
import json
from pathlib import Path
import numpy as np
import bpy

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT=ROOT/'MembraneStabilityV31'
OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'BodyMotionV18/Proxy/cloth_ue_manifest_v18.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BodyMotionV18/Proxy/M07_Original_GillContacts_V18.blend'))
rows=[]
for label in range(1,7):
    obj=bpy.data.objects[f'M07_OriginalGill_{label:02d}_SimulationV18']
    panel=manifest['panels'][label-1]
    p=np.asarray([v.co[:] for v in obj.data.vertices],float)
    faces=np.asarray([list(f.vertices) for f in obj.data.polygons],int)
    adjacency=[set() for _ in p]
    for tri in faces:
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            adjacency[a].add(b);adjacency[b].add(a)
    remaining=set(range(len(p)))
    components=[]
    while remaining:
        stack=[remaining.pop()];component=[]
        while stack:
            node=stack.pop();component.append(node)
            for n in adjacency[node]:
                if n in remaining:remaining.remove(n);stack.append(n)
        components.append(component)
    maxdist=np.asarray(panel['max_distance_cm'])
    edge=np.stack((p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,1]],p[faces[:,0]]-p[faces[:,2]]),axis=1)
    length=np.linalg.norm(edge,axis=2)
    twice=np.linalg.norm(np.cross(edge[:,0],-edge[:,2]),axis=1)
    quality=2*np.sqrt(3)*twice/np.maximum((length*length).sum(axis=1),1.e-12)
    islands=[dict(vertices=len(c),pins=int((maxdist[c]<1.e-5).sum()),max_distance_cm=float(maxdist[c].max()),
                  diameter_cm=float(np.linalg.norm(p[c].max(axis=0)-p[c].min(axis=0)))) for c in components]
    display=bpy.data.objects[f'M07_OriginalGill_{label:02d}_Display']
    groups={g.index:g.name for g in display.vertex_groups}
    bins={};seam_conflicts=0;max_seam=0.
    for v in display.data.vertices:
        key=tuple(round(float(x),3) for x in v.co)
        weights={groups[g.group]:g.weight for g in v.groups if g.weight>1.e-6}
        if key in bins:
            previous=bins[key];error=sum(abs(weights.get(n,0)-previous.get(n,0)) for n in set(weights)|set(previous))
            max_seam=max(max_seam,error);seam_conflicts+=error>.05
        else:bins[key]=weights
    row=dict(panel=label,vertices=len(p),triangles=len(faces),components=len(components),
        unpinned_components=sum(r['pins']==0 for r in islands),unpinned_vertices=sum(r['vertices'] for r in islands if r['pins']==0),
        triangle_quality_min=float(quality.min()),triangles_quality_below_005=int((quality<.05).sum()),
        longest_edge_cm=float(length.max()),islands=sorted(islands,key=lambda r:-r['vertices']),
        coincident_weight_conflicts=seam_conflicts,max_coincident_weight_l1=max_seam)
    rows.append(row)
    print('M07_V31_SOURCE_PANEL '+json.dumps({k:v for k,v in row.items() if k!='islands'}),flush=True)
(OUT/'source_membrane_diagnosis_v31.json').write_text(json.dumps(dict(scope='Requested source-only membrane inspection; no simulation or game run',panels=rows),indent=2)+'\n',encoding='utf-8')
