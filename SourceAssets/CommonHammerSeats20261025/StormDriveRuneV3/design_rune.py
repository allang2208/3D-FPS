"""Unified tapered lightning footprint; no overlapping strips at branch junctions."""
import sys,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P/'python_deps'))
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
w=.0385*.29;h=.054*.72
paths=[([( .20,.85),(-.08,.39),(.26,.43),(-.38,-.17),(.05,-.11),(-.28,-.88)],[.04,.52,.64,.54,.48,.025]),
       ([(-.07,.12),(.50,.31),(.42,.52)],[.32,.27,.02]),
       ([(-.032,-.30),(-.55,-.41),(-.48,-.57)],[.28,.20,.02]),
       ([(-.08,.39),(-.52,.48),(-.41,.62)],[.24,.16,.02])]
def arch(w,h):
    pts=[(-w,-h),(w,-h),(w,h*.30)]
    for i in range(1,19):
        t=i/18;pts.append(((1-t)**2*w+2*(1-t)*t*w*.83,(1-t)**2*h*.30+2*(1-t)*t*h*.75+t*t*h))
    pts += [(-x,z) for x,z in reversed(pts[2:-1])]
    return pts
usable=Polygon(arch(.0385*.262,.054*.687))
out={}
for name,scale in [('channel',1.35),('metal',1.0),('light',.32)]:
    pieces=[]
    for points,widths in paths:
        points=[(x*w,z*h) for x,z in points];widths=[r*.001*scale for r in widths]
        for (a,b),(ra,rb) in zip(zip(points,points[1:]),zip(widths,widths[1:])):
            dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);nx=-dy/length;ny=dx/length
            pieces.append(Polygon([(a[0]+nx*ra,a[1]+ny*ra),(b[0]+nx*rb,b[1]+ny*rb),(b[0]-nx*rb,b[1]-ny*rb),(a[0]-nx*ra,a[1]-ny*ra)]))
        pieces.extend(Point(p).buffer(r,quad_segs=6) for p,r in zip(points,widths))
    shape=unary_union(pieces).simplify(.000005,preserve_topology=True)
    assert shape.geom_type=='Polygon' and shape.is_valid and not shape.interiors,(name,shape.geom_type)
    assert usable.contains(shape),(name,'Rune must stay inside the actual plate border')
    out[name]=list(shape.exterior.coords)[:-1]
(P/'rune_footprints.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('TAPERED_LIGHTNING_UNION_READY')
