"""Give the source's disconnected sight assemblies one semantic material slot."""
import bpy
from collections import defaultdict

def tag_factory_sights(parts):
    ob=next(o for o in parts if o.name=='Super90_body');me=ob.data
    material=bpy.data.materials.get('FactorySights')
    if not material:
        material=bpy.data.materials['TTI_Benelli_M4'].copy();material.name='FactorySights'
    slot=me.materials.find('FactorySights')
    if slot<0:me.materials.append(material);slot=len(me.materials)-1
    parent=list(range(len(me.vertices)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(a,b):parent[find(a)]=find(b)
    points={}
    for v in me.vertices:
        key=tuple(round(c,6) for c in v.co)
        if key in points:join(v.index,points[key])
        else:points[key]=v.index
    for e in me.edges:join(*e.vertices)
    groups=defaultdict(list)
    for v in me.vertices:groups[find(v.index)].append(v)
    selected=set()
    for vs in groups.values():
        lo=[min(v.co[k] for v in vs) for k in range(3)];hi=[max(v.co[k] for v in vs) for k in range(3)]
        rear=lo[1]>-.15 and hi[1]<-.09 and lo[2]>-.735
        front=lo[1]>.43 and hi[1]<.49 and hi[2]>-.73
        if rear or front:selected.update(v.index for v in vs)
    count=0
    for p in me.polygons:
        if all(v in selected for v in p.vertices):p.material_index=slot;count+=1
    return count
