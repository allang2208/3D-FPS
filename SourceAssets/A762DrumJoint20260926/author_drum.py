"""Replace the distorted tower by an ordered, closed loft to A762's seated well.

The drum below the 24 mm cut retains its positions, per-corner UVs and normals.
New surfaces use A762's existing magazine finish rather than stretched donor UVs.
Units: metres, WPN_SOCKET_Magazine local, matching the current static attachment.
"""
import json
import math
from collections import defaultdict
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

O = Path(__file__).resolve().parent
S = O.parent
INPUT = S / 'A762DrumNeck20260925/SM_A762_drum.blend'
ACC = S / 'A762Meshy20260920/Accessories05'
CUT = .024
OUT = O / 'Exports'
OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
data = json.loads((O / 'interface_inputs.json').read_text(encoding='utf-8'))
collar = data['objects']['A762_R02_Receiver_MagwellCollar']
collar_min_z = collar['min_mm'][2] / 1000
collar_max_z = collar['max_mm'][2] / 1000

# Extract the real inner interface contour from a horizontal cut through the rim.
def plane_loops(points, faces, z):
    segments = set()
    def key(p): return tuple(round(v, 6) for v in p)
    for face in faces:
        hit = []
        for a, b in zip(face, face[1:] + face[:1]):
            p, q = Vector(points[a]), Vector(points[b])
            if (p.z-z)*(q.z-z) < 0:
                hit.append(key(p.lerp(q, (z-p.z)/(q.z-p.z))))
        if len(hit) == 2 and hit[0] != hit[1]:
            segments.add(tuple(sorted(hit)))
    links = defaultdict(set)
    for a, b in segments: links[a].add(b); links[b].add(a)
    loops = []
    while links:
        start = min(links); p = start; prev = None; loop = []
        while True:
            loop.append(Vector(p))
            nxt = next(q for q in links[p] if q != prev)
            prev, p = p, nxt
            if p == start: break
        for v in loop: del links[key(v)]
        loops.append(loop)
    return loops

rim_loops = plane_loops(collar['vertices_m'], collar['faces'], (collar_min_z+collar_max_z)/2)
rim = min(rim_loops, key=lambda pts: max(p.x for p in pts)-min(p.x for p in pts))
cx = (min(p.x for p in rim)+max(p.x for p in rim))/2
cy = (min(p.y for p in rim)+max(p.y for p in rim))/2
rim.sort(key=lambda p: math.atan2(p.y-cy, p.x-cx))

def ray_to_rim(theta):
    d = Vector((math.cos(theta), math.sin(theta)))
    for p, q in zip(rim, rim[1:]+rim[:1]):
        a = Vector((p.x-cx, p.y-cy)); e = Vector((q.x-p.x, q.y-p.y))
        cross = d.x*e.y-d.y*e.x
        if abs(cross) < 1e-12: continue
        t = (a.x*e.y-a.y*e.x)/cross
        u = (a.x*d.y-a.y*d.x)/cross
        if t > 0 and -.00001 <= u <= 1.00001:
            # 0.20 mm overlap at the real well inner wall conceals the joint.
            return Vector((cx+d.x*(t+.00020), cy+d.y*(t+.00020), 0))
    raise RuntimeError('Cannot construct a point on the actual well contour')

# Bring only the established factory finish materials into the editable source.
bpy.ops.wm.open_mainfile(filepath=str(INPUT), use_scripts=False)
with bpy.data.libraries.load(str(ACC / 'A762_AccessoryReady_Editable.blend'), link=False) as (src, dst):
    dst.materials = ['M_A762_Magazine_Rebuilt', 'M_A762_MagazineInside_Rebuilt']
neck_mat, inside_mat = dst.materials
neck_mat.name = 'A762_drum_Neck'; inside_mat.name = 'A762_drum_Inside'
old = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
me = old.data
verts, faces, corner_data, mats, smooth = [], [], [], [], []
lookup = {}
uv_names = [uv.name for uv in me.uv_layers]
original_normals = [v.vector.copy() for v in me.corner_normals]

def vertex(p):
    k = tuple(round(c, 7 if abs(p.z-CUT)<1e-8 else 10) for c in p)
    if k not in lookup: lookup[k] = len(verts); verts.append(tuple(p))
    return lookup[k]

def face(points, attributes, material, shading=True):
    idx = [vertex(p) for p in points]
    clean = [j for j in range(len(idx)) if idx[j] != idx[j-1]]
    if len(clean) < 3: return
    faces.append(tuple(idx[j] for j in clean))
    corner_data.append([attributes[j] for j in clean] if attributes else None)
    mats.append(material); smooth.append(shading)

# Clip only the old upper neck, interpolating source corner attributes at the cut.
for p in me.polygons:
    poly = [(me.vertices[me.loops[li].vertex_index].co.copy(),
             original_normals[li], [layer.data[li].uv.copy() for layer in me.uv_layers]) for li in p.loop_indices]
    clipped = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        ina, inb = a[0].z <= CUT, b[0].z <= CUT
        if ina: clipped.append(a)
        if ina != inb:
            t = (CUT-a[0].z)/(b[0].z-a[0].z)
            q = a[0].lerp(b[0], t); q.z = CUT
            clipped.append((q, a[1].lerp(b[1], t).normalized(), [u.lerp(v,t) for u,v in zip(a[2],b[2])]))
    face([a[0] for a in clipped], [(a[1],a[2]) for a in clipped], p.material_index, p.use_smooth)

# Recover ordered lower outer/inner cut rings; no nearest-neighbour point matching.
edge_count = defaultdict(int)
for f in faces:
    for a,b in zip(f, f[1:]+f[:1]): edge_count[tuple(sorted((a,b)))] += 1
links = defaultdict(set)
for (a,b), n in edge_count.items():
    if n == 1 and abs(verts[a][2]-CUT)<1e-8 and abs(verts[b][2]-CUT)<1e-8:
        links[a].add(b);links[b].add(a)
loops=[]
while links:
    start=min(links);p=start;prev=None;loop=[]
    while True:
        loop.append(p)
        nxt=next(q for q in links[p] if q != prev)
        prev,p=p,nxt
        if p == start: break
    for i in loop: del links[i]
    loops.append(loop)
outer=max(loops,key=lambda l:max(verts[i][0] for i in l)-min(verts[i][0] for i in l))
bcx=(min(verts[i][0] for i in outer)+max(verts[i][0] for i in outer))/2
bcy=(min(verts[i][1] for i in outer)+max(verts[i][1] for i in outer))/2
outer.sort(key=lambda i: math.atan2(verts[i][1]-bcy,verts[i][0]-bcx))
# The old inner void ends here. Close only that new cut, inside the preserved shell.
for loop in loops:
    if loop != outer and set(loop) != set(outer):
        pts=[Vector(verts[i]) for i in loop]
        pts.sort(key=lambda p: math.atan2(p.y-bcy,p.x-bcx))
        face(list(reversed(pts)), None, 4, False)

bottom=[Vector(verts[i]) for i in outer]
angles=[math.atan2(p.y-bcy,p.x-bcx) for p in bottom]
target=[ray_to_rim(t) for t in angles]
seat_z=collar_min_z-.00020
top_z=collar_max_z+.00050
rows=[bottom]
# Linear loft: every longitudinal vertex follows a straight line to its target.
for t in (.25,.5,.75,1.0):
    rows.append([Vector((p.x+(q.x-p.x)*t,p.y+(q.y-p.y)*t,CUT+(seat_z-CUT)*t)) for p,q in zip(bottom,target)])
rows.append([Vector((p.x,p.y,top_z)) for p in target])

def bridge(a,b,mat,reverse=False):
    for i in range(len(a)):
        j=(i+1)%len(a)
        pts=[a[i],a[j],b[j],b[i]]
        if reverse: pts.reverse()
        face(pts,None,mat,False)

for a,b in zip(rows,rows[1:]): bridge(a,b,3)
# Copy the factory mouth's inner proportions, retain four walls and a finite floor.
inner=[]
for p in rows[-1]:
    inner.append(Vector((cx+(p.x-cx)*.73,cy+(p.y-cy)*.88,top_z)))
bridge(rows[-1],inner,3)
floor=[Vector((p.x,p.y,top_z-.006)) for p in inner]
bridge(inner,floor,4)
face(floor,None,4,False)

mesh=bpy.data.meshes.new('A762_Drum_ContinuousJoint')
mesh.from_pydata(verts,[],faces);mesh.update()
for m in list(me.materials)+[neck_mat,inside_mat]:mesh.materials.append(m)
for name in uv_names:mesh.uv_layers.new(name=name)
# New walls have explicit, face-oriented normals; curved rim samples retain
# deliberately small facets. Existing corner normals and UVs are restored verbatim.
normals=[]
for p,attr,mat,shade in zip(mesh.polygons,corner_data,mats,smooth):
    p.material_index=mat;p.use_smooth=shade
    axis=max(range(3),key=lambda i:abs(p.normal[i]));a,b=[i for i in range(3) if i != axis]
    for j,li in enumerate(p.loop_indices):
        pos=mesh.vertices[mesh.loops[li].vertex_index].co
        normals.append(tuple(attr[j][0] if attr else p.normal))
        for layer_index,layer in enumerate(mesh.uv_layers):
            layer.data[li].uv=attr[j][1][layer_index] if attr else (pos[a]*36,pos[b]*36)
# Set smoothing before custom corner normals, per Blender's mesh normal contract.
mesh.normals_split_custom_set(normals)
new=bpy.data.objects.new('SM_A762_drum',mesh);bpy.context.scene.collection.objects.link(new)
new.matrix_world=Matrix.Identity(4)
bpy.data.objects.remove(old,do_unlink=True)
new['revision']='A762DrumJoint20260926'
new['interface']='Actual A762 seated well contour; WPN_SOCKET_Magazine local'
bpy.ops.object.select_all(action='DESELECT');new.select_set(True);bpy.context.view_layer.objects.active=new
# Explicit triangulation preserves source split normals and prevents importer-dependent ngons.
tri=new.modifiers.new('Export triangles with retained normals','TRIANGULATE');tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SM_A762_drum.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_A762_drum.fbx'),use_selection=True,object_types={'MESH'},
                        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
receipt={'source':str(INPUT),'editable':str(O/'SM_A762_drum.blend'),'fbx':str(OUT/'SM_A762_drum.fbx'),
         'frame':'WPN_SOCKET_Magazine local, metres, unchanged pivot',
         'preserved_drum_below_mm':CUT*1000,'well_rim_z_mm':[collar_min_z*1000,collar_max_z*1000],
         'new_interface_z_mm':[seat_z*1000,top_z*1000],'well_wall_overlap_mm':.2,
         'interface_center_mm':[cx*1000,cy*1000],
         'construction':'Closed linear ordered loft; original lower drum; finite 6 mm mouth recess',
         'material_slots':[m.name for m in new.data.materials],
         'new_finish_sources':['M_A762_Magazine_Rebuilt','M_A762_MagazineInside_Rebuilt'],
         'triangles':len(new.data.polygons),'game_tested':False,'acceptance_rendered':False}
(O/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('A762_DRUM_JOINT_AUTHORED',json.dumps(receipt),flush=True)
