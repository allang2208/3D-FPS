"""Smooth coincident UV seam vertices together; never open the original lip surface."""
from mathutils import Vector
def refine(mesh,original):
    groups={};ids=[];points=[];members=[]
    for i,p in enumerate(original['positions']):
        key=tuple(round(v,4) for v in p)
        if key not in groups:
            groups[key]=len(points);points.append(Vector(p));members.append([])
        gi=groups[key];ids.append(gi);members[gi].append(i)
    neighbours=[set() for _ in points]
    for a,b,c in original['triangles']:
        a,b,c=ids[a],ids[b],ids[c]
        neighbours[a].update((b,c));neighbours[b].update((a,c));neighbours[c].update((a,b))
    starts=[p.copy() for p in points];selected=[]
    for i,p in enumerate(points):
        fade=max(0.,1-abs(p.x)/2.45)*max(0.,1-abs(p.z-150.2)/.85)
        if fade and p.y>6.5:selected.append((i,fade))
    for _ in range(5):
        updates={}
        for i,fade in selected:
            ns=neighbours[i]-{i}
            if ns:updates[i]=points[i].lerp(sum((points[j] for j in ns),Vector())/len(ns),.16*fade)
        for i,p in updates.items():points[i]=p
    for i,indices in enumerate(members):
        delta=points[i]-starts[i]
        if delta.length>.04:points[i]=starts[i]+delta.normalized()*.04
        for vi in indices:mesh.vertices[vi].co=points[i]
    mesh.update()
    return len(selected)
