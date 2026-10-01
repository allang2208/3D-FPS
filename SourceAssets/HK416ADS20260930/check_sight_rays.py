"""Scoped geometric inspection requested for the HK416 iron sight picture."""
import json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
d=json.loads((O/'sight_geometry.json').read_text());v=[Vector(p) for p in d['vertices']]
bvh=BVHTree.FromPolygons(v,d['triangles'])
landmarks=json.loads((O/'landmarks.json').read_text())
report={'space':'source mesh metres; 900 px vertical, 55 degree vertical FOV','scope':'offline sight geometry only'}
for key,rear,front,eye in [('before',(0,-.0246,.03455),(0,.0669,.03455),.18/4),('after',landmarks['rear_source_m'],landmarks['front_source_m'],.12/4)]:
    rear=Vector(rear);front=Vector(front);axis=(front-rear).normalized();cam=rear-axis*eye
    right=axis.cross(Vector((0,0,1))).normalized();up=right.cross(axis).normalized();rays=[]
    for dx,dy in [(0,0),(0,-2),(0,-5),(0,-8),(0,2),(0,5),(0,8),(-7,0),(7,0)]:
        direction=(axis+(right*dx-up*dy)*(2*math.tan(math.radians(55)/2)/900)).normalized()
        p,n,i,distance=bvh.ray_cast(cam,direction)
        hit='sky' if p is None else 'rear_sight_body' if p.y<0 else 'front_sight'
        rays.append({'pixel_offset':[dx,dy],'hit':hit,'point':list(p) if p else None})
    report[key]={'rear':list(rear),'front':list(front),'eye_distance_game_cm':eye*400,'rays':rays}
(O/'sight_rays.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
