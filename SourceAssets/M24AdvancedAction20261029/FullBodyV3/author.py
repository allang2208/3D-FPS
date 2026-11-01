"""Full front chassis. Native buttstock, barrel and animated parts are retained."""
from pathlib import Path
O=Path(__file__).resolve().parent
helpers=(O.parent/'DetailV2/author.py').read_text(encoding='utf-8').split('# Keep the current lower perimeter')[0]
exec(compile(helpers,'M24 shared precision modelling helpers','exec'))
native=bpy.data.objects['M24_base'];src=native.data
parent=list(range(len(src.vertices)));seen={}
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def unite(a,b):parent[root(a)]=root(b)
for v in src.vertices:
    key=tuple(round(x,6) for x in v.co)
    if key in seen:unite(v.index,seen[key])
    else:seen[key]=v.index
for e in src.edges:unite(*e.vertices)
stock=root(0)
islands={}
for v in src.vertices:islands.setdefault(root(v.index),[]).append(v.index)
barrel=max(islands,key=lambda k:max(src.vertices[i].co.y for i in islands[k]))
selected=[]
for p in src.polygons:
    vs=[src.vertices[i].co for i in p.vertices];island=root(p.vertices[0])
    if island==stock:remove=min(v.y for v in vs)>=.020
    elif island==barrel:remove=max(v.y for v in vs)<.281
    else:remove=min(v.y for v in vs)>.041
    if remove:selected.append(p.index)
centers=[]
for i in selected:
    p=src.polygons[i];c=sum((src.vertices[j].co for j in p.vertices),Vector())/len(p.vertices)
    centers.append([c.x*100,-c.y*100,c.z*100])
(O/'factory_front_faces.json').write_text(json.dumps(centers))

# Copy the actual irregular stock boundary into a closed transition, with the
# original ring intact. The front ring converges into the new receiver bedding.
edge_use={}
for pi in selected:
    p=src.polygons[pi]
    if root(p.vertices[0])!=stock:continue
    for a,b in p.edge_keys:
        key=tuple(sorted((tuple(round(x,6) for x in src.vertices[a].co),tuple(round(x,6) for x in src.vertices[b].co))))
        edge_use[key]=edge_use.get(key,0)+1
edges=[e for e,n in edge_use.items() if n==1]
loops=[]
while edges:
    a,b=edges.pop();loop=[a,b]
    while loop[-1]!=loop[0]:
        found=next((i for i,e in enumerate(edges) if loop[-1] in e),None)
        if found is None:break
        e=edges.pop(found);loop.append(e[1] if e[0]==loop[-1] else e[0])
    if loop[-1]==loop[0] and len(loop)>3:loops.append(loop[:-1])
for ring in loops:
    # Cut boundary is at the stock wrist, not around the barrel channel.
    if max(p[1] for p in ring)>.14:continue
    n=len(ring);end=[(max(-.024,min(.024,p[0])),.104,max(.056,min(.104,p[2]))) for p in ring]
    verts=ring+end
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh('Native stock interface transition',verts,faces,coat,.00015)

# Angular lower receiver walls and magazine funnel, with deep relief pockets.
profile=[(.034,.053),(.102,.048),(.136,.050),(.150,.061),(.253,.061),(.278,.074),
         (.292,.079),(.292,.107),(.106,.107),(.060,.092),(.034,.082)]
for sign in (-1,1):
    side=prism_x('Machined receiver chassis',profile,sign*.0208,sign*.0261,bevel=.00065)
    pocket=[(.112,.067),(.130,.0628),(.245,.066),(.270,.080),(.270,.098),(.112,.098)]
    cut(side,prism_x('Receiver relief tool',pocket,sign*.0250,sign*.028,bevel=.0009))
    for y,z in ((.059,.078),(.115,.087),(.260,.088)):
        fastener(side,sign,y,z,.0259,.0023)
    for j in range(8):
        y=.145+j*.012
        slot(side,(sign*.0262,y,.072),(.0018,.0017,.008),.00045)
    # Magazine lip stays outside the native magazine envelope and release path.
    prism_x('Magazine funnel flank',[(.139,.056),(.149,.049),(.231,.049),(.243,.058),(.239,.064),(.144,.064)],
            sign*.0202,sign*.0250,bevel=.00055)

# Retain the guard contact envelope while remaking its machining and surfaces.
guard_ids=[p for p in src.polygons if p.index in selected and min(src.vertices[i].co.z for i in p.vertices)<.046]
if guard_ids:
    ids=sorted({i for p in guard_ids for i in p.vertices});remap={v:i for i,v in enumerate(ids)}
    mesh('Reconstructed trigger guard and release housing',[tuple(src.vertices[i].co) for i in ids],
         [tuple(remap[i] for i in p.vertices) for p in guard_ids],coat,.00035)

# Outer receiver sleeve replaces the old static housing; the bolt itself is
# untouched. An open ejection window exposes its original travel corridor.
receiver=cylinder('Receiver sleeve',(0,.185,.1150),.0208,.191,'Y',coat,80,.00035)
cut(receiver,cylinder('Receiver bore',(0,.185,.1150),.0188,.206,'Y',coat,80,.00018))
slot(receiver,(.020,.175,.121),(.030,.119,.029),.0035)
slot(receiver,(0,.093,.119),(.052,.018,.045),.003)
# Rear top rail follows the existing optic support height exactly.
railback=[(-.0095,.1388),(.0095,.1388),(.0105,.1420),(-.0105,.1420)]
prism_y('Receiver optic rail spine',railback,.108,.281,bevel=.00025)
for j in range(13):
    y=.112+j*.01347
    prism_y('Receiver optic rail tooth',[(-.0103,.142),(.0103,.142),(.0114,.143),(.0103,.14483),(-.0103,.14483),(-.0114,.143)],y,y+.0083,bevel=.00018)

# Full-depth free-floating forend, including the previously retained underside.
# The lower chamfer retains the existing support-hand contact envelope.
wall=[(.0215,.0673),(.0268,.072),(.0280,.082),(.0280,.1345),(.0227,.1442),
      (.0190,.145),(.0190,.1412),(.0242,.1334),(.0242,.082),(.0230,.074),(.0205,.071)]
for sign in (-1,1):
    side=prism_y('Full-depth ventilated handguard',[(sign*x,z) for x,z in wall],.282,.608,bevel=.00055)
    for y in (.315,.362,.409,.456,.503,.550,.589):
        length=.032 if y<.58 else .017
        slot(side,(sign*.027,y,.122),(.016,length,.012),.0042)
        slot(side,(sign*.027,y,.091),(.016,length,.010),.0037)
    for y in (.329,.383,.437,.491,.545,.583):
        slot(side,(sign*.0228,y,.1397),(.016,.022,.004),.0015)
    for y in (.293,.395,.491,.596):fastener(side,sign,y,.0758,.027,.0017)
    # Countersunk lower seam and separate support pads read as assembled metal.
    for y in (.299,.598):fastener(side,sign,y,.107,.028,.0022)
    carrier=box('Side rail fitted carrier',(sign*.030,.532,.120),(.006,.102,.010),bevel=.0004)
    for y in (.487,.575):
        box('Side rail foot',(sign*.028,y,.120),(.004,.010,.014),bevel=.0003)
        fastener(carrier,sign,y,.120,.033,.0020)
    for j in range(8):
        y=.495+j*.0095
        xz=[(.031,.113),(.032,.111),(.036,.113),(.036,.127),(.032,.129),(.031,.127)]
        prism_y('Side rail dovetail',[(sign*x,z) for x,z in xz],y,y+.0053,bevel=.00025)

# One closed formed belly plate. Top/bottom edges meet the wall returns.
belly=[(-.0215,.0673),(-.011,.0661),(0,.0658),(.011,.0661),(.0215,.0673),
       (.023,.071),(.011,.0700),(0,.0696),(-.011,.0700),(-.023,.071)]
floor=prism_y('Continuous lower handguard',belly,.277,.608,bevel=.00035)
for y in (.320,.362,.535,.577):
    slot(floor,(0,y,.067),(.015,.026,.014),.003)
# Middle lower face is solid at the existing support grip and bipod mount.
outer=[(-.0215,.0673),(.0215,.0673),(.0282,.079),(.0282,.1348),(.0227,.1448),
       (-.0227,.1448),(-.0282,.1348),(-.0282,.079)]
for y,d in ((.282,.006),(.608,.006)):
    collar=prism_y('Closed handguard bulkhead',outer,y-d/2,y+d/2,bevel=.0006)
    cut(collar,cylinder('Barrel free-float opening',(0,y,.11391),.0205,d+.014,'Y',coat,80,.00025))
    for sign in (-1,1):fastener(collar,sign,y,.086,.0282,.0017)
prism_y('Top continuous rail',[(-.0095,.1426),(.0095,.1426),(.0100,.1455),(-.0100,.1455)],.279,.614,bevel=.00025)
for j in range(33):
    y=.286+j*.010
    prism_y('Top rail tooth',[(-.009,.1448),(.009,.1448),(.013,.1463),(.013,.1477),(.0107,.1503),(-.0107,.1503),(-.013,.1477),(-.013,.1463)],y-.0031,y+.0031,bevel=.00022)

# Production join, tangents and unique-mask UVs are shared with DetailV2.
tail='#'+(O.parent/'DetailV2/author.py').read_text(encoding='utf-8').split('# Apply only authored features.')[1]
tail=tail.replace('DetailV2','FullBodyV3').replace('host_modified=False','host_modified=True')
exec(compile(tail,'M24 full-body export','exec'))

# A saved source presentation uses a copy with hidden native front faces;
# the shipping native skeleton is partitioned in UE without reimporting it.
preview=native.data.copy();native.data=preview
bm=bmesh.new();bm.from_mesh(preview);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.faces[i] for i in selected],context='FACES');bm.to_mesh(preview);bm.free()
(O/'partition.json').write_text(json.dumps(dict(face_count=len(selected),original_stock_retained=True,
    boundary_loops=loops,bolt_and_barrel_retained=True,source_face_centers=str(O/'factory_front_faces.json')),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_AdvancedAction_FullBodyV3.blend'))
