"""Scoped diagnosis requested for cylinder residue and chamber seating."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003';O.mkdir(exist_ok=True)
parts=json.loads((B/'canonical_parts.json').read_text(encoding='utf8'))
report={'source_parts':{},'donor_meshes':{},'assembly':{}}
for part in parts:
    if part['name'] not in ('4_l','5_l','6_l','12_l','13_l'):continue
    verts=[Vector(v) for v in part['verts']];edges={}
    for face in part['faces']:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
    # Weld split UV/normal vertices for meaningful surface boundary topology.
    ids={};remap={};points=[]
    for i,v in enumerate(verts):
        key=tuple(round(x,6) for x in v)
        if key not in ids:ids[key]=len(points);points.append(v)
        remap[i]=ids[key]
    edge2={}
    for face in part['faces']:
        for a,b in zip(face,face[1:]+face[:1]):
            a,b=remap[a],remap[b]
            if a==b:continue
            key=tuple(sorted((a,b)));edge2[key]=edge2.get(key,0)+1
    adj={}
    for (a,b),count in edge2.items():
        if count==1:adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
    seen=set();loops=[]
    for i in adj:
        if i in seen:continue
        stack=[i];seen.add(i);shell=[]
        while stack:
            a=stack.pop();shell.append(a)
            for j in adj[a]:
                if j not in seen:seen.add(j);stack.append(j)
        vv=[points[j] for j in shell];center=sum(vv,Vector())/len(vv)
        loops.append(dict(vertices=len(vv),center=list(center),min=[min(v[k] for v in vv) for k in range(3)],max=[max(v[k] for v in vv) for k in range(3)]))
    report['source_parts'][part['name']]=dict(boundaries=loops,rear_points=[list(v) for v in points if v.y>.090])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(B/'Donor/single/SK_DW715_Donor.fbx'))
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    pergroup={};remaining=[]
    for v in ob.data.vertices:
        groups={ob.vertex_groups[g.group].name:g.weight for g in v.groups}
        for name,w in groups.items():pergroup[name]=pergroup.get(name,0)+w
        if sum(w for n,w in groups.items() if n.startswith('WPN_'))<=.5:remaining.append(v.index)
    report['donor_meshes'][ob.name]=dict(vertices=len(ob.data.vertices),remaining_after_old_filter=len(remaining),
        materials=[m.name for m in ob.data.materials if m],groups=pergroup,
        remaining_materials={str(i):sum(len(p.vertices) for p in ob.data.polygons if p.material_index==i and all(v in set(remaining) for v in p.vertices)) for i in range(len(ob.data.materials))})
bpy.ops.wm.open_mainfile(filepath=str(B/'Single/RSH12_single_Editable.blend'))
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    bymat={}
    for poly in ob.data.polygons:
        mat=ob.data.materials[poly.material_index];key=mat.name
        row=bymat.setdefault(key,dict(polygons=0,vertices=set(),weights={}))
        row['polygons']+=1
        for i in poly.vertices:
            row['vertices'].add(i)
    for row in bymat.values():
        for i in row['vertices']:
            for g in ob.data.vertices[i].groups:
                name=ob.vertex_groups[g.group].name;row['weights'][name]=row['weights'].get(name,0)+g.weight
        row['vertices']=len(row['vertices'])
    report['assembly'][ob.name]=bymat
(O/'geometry_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for n,d in report['source_parts'].items():print('PART_BOUNDARIES',n,[(x['vertices'],[round(v*1000,2) for v in x['center']]) for x in d['boundaries']],flush=True)
for n,d in report['donor_meshes'].items():print('DONOR_REMAINDER',n,d['remaining_after_old_filter'],d['materials'],flush=True)
print('RSH12_FIT_DIAGNOSIS_SAVED',flush=True)
