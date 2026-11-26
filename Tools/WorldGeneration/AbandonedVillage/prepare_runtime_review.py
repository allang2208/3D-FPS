"""Inputs for an opt-in real hills runtime review; production assets are read only."""
import json, sys
from pathlib import Path
import numpy as np
from wall_support_geometry import ROOT, load_mesh, rotate_vertices
from layout_geometry import house_geometry, house_paths

source = ROOT / 'SourceAssets/TemperateHillsVillage'
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
plan = json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
walls = []
for group in plan['yard_walls']:
    for inst in group['native_instances']:
        v, f = load_mesh(inst['mesh'].split('.')[-1])
        q = rotate_vertices(v * np.array(inst['scale']), inst['rot']) + inst['pos']
        t = q[f]
        contact = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            va, vb = t[:, a], t[:, b]
            mask = (va[:, 2] * vb[:, 2] <= 0) & (abs(vb[:, 2]-va[:, 2]) > 1e-7)
            va, vb = va[mask], vb[mask]
            contact.extend(va+(vb-va)*(-va[:, 2]/(vb[:, 2]-va[:, 2]))[:, None])
        # Distributed actual triangle/ground intersections, not imported bounding boxes.
        points = np.unique(np.round(contact, 2), axis=0)
        if len(points) > 64:
            points = points[np.linspace(0, len(points)-1, 64).astype(int)]
        if len(points) < 3:
            raise RuntimeError('Missing support intersections: '+inst['mesh'])
        walls.append(dict(inst, contacts=points.tolist(), index=len(walls)))
routes = [dict(name='road_'+str(i), kind='road', points=[[x*100,y*100,0] for x,y in r['points']])
          for i,r in enumerate(plan['roads'])]
for r in list(routes):
    routes.append(dict(name=r['name']+'_reverse',kind='road',points=list(reversed(r['points']))))
for i,(house,(path,_)) in enumerate(zip(plan['houses'],house_paths(plan,kit))):
    g = house_geometry(house,kit[house[2]],plan['house_scale'])
    inside = [g['entry'][j]-g['normal'][j]*1.6 for j in (0,1)]
    inward = [path[2],path[1],path[0],inside]
    routes.append(dict(name='door_'+house[0],kind='door',
                       points=[[x*100,y*100,0] for x,y in inward+list(reversed(inward[:-1]))]))
data = dict(walls=walls,routes=routes,capture_wall_indices=[0,11,24,50,66,83],
            units='cm',source_layout=str(source/'layout.json'))
(out/'input.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(walls=len(walls),routes=len(routes),support_points=sum(len(w['contacts']) for w in walls))))
