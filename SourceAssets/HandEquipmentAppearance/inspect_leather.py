"""Read the accepted Manny arms; export metrics for leather material authoring."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).parent
SOURCE = OUT.parent / 'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
obj = bpy.data.objects['SK_Manny_Arms_Export']
rig = obj.find_armature()
data = {'mesh': obj.name, 'object_scale': list(obj.scale),
        'unit_scale': bpy.context.scene.unit_settings.scale_length,
        'bones': {}, 'components': []}
for name in ('hand_l', 'hand_r', 'index_01_l', 'pinky_01_l', 'thumb_01_l'):
    bone = rig.data.bones.get(name)
    if bone:
        data['bones'][name] = {'head': list(bone.head_local), 'tail': list(bone.tail_local),
                              'x': list(bone.x_axis), 'y': list(bone.y_axis), 'z': list(bone.z_axis)}
parents = list(range(len(obj.data.vertices)))
def find(i):
    while parents[i] != i:
        parents[i] = parents[parents[i]]
        i = parents[i]
    return i
for e in obj.data.edges:
    a, b = (find(i) for i in e.vertices)
    parents[b] = a
parts = {}
for v in obj.data.vertices:
    parts.setdefault(find(v.index), []).append(v)
accepted = {r['id'] for r in json.loads((OUT/'components.json').read_text()) if r['hand'] > .5}
uv = obj.data.uv_layers.active.data
total_uv = total_area = 0.0
region_faces = []
seam_segments = []
edge_uses = {}
for p in obj.data.polygons:
    for edge in p.edge_keys:
        edge_uses[edge] = edge_uses.get(edge,0)+1
for root, verts in parts.items():
    if root not in accepted:
        continue
    faces = [p for p in obj.data.polygons if find(p.vertices[0]) == root]
    avg = sum((v.co for v in verts), Vector()) / len(verts)
    area = sum(p.area for p in faces)
    uv_area = 0.0
    boundary = {}
    for p in faces:
        loops = list(p.loop_indices)
        for j, li in enumerate(loops):
            lj = loops[(j+1)%len(loops)]
            va, vb = obj.data.loops[li].vertex_index, obj.data.loops[lj].vertex_index
            if edge_uses[tuple(sorted((va,vb)))] == 1:
                boundary[va] = (vb, uv[li].uv.copy(), uv[lj].uv.copy(),
                                sum((uv[k].uv for k in loops), Vector((0,0)))/len(loops))
    # Follow true mesh shell edges. UV cuts inside a shell never become stitches.
    remaining = set(boundary)
    while remaining:
        start = min(remaining)
        vertex = start
        distance = 0.0
        while vertex in remaining:
            remaining.remove(vertex)
            other, a, b, center = boundary[vertex]
            length = (obj.data.vertices[vertex].co-obj.data.vertices[other].co).length
            seam_segments.append({'component':root, 'palm':len(verts) in (1267,188,278),
                                  'a':list(a), 'b':list(b), 'inside':list(center),
                                  'distance':distance, 'length':length})
            distance += length
            vertex = other
    for p in faces:
        pts = [uv[i].uv for i in p.loop_indices]
        uv_area += abs(sum(a.x*b.y-b.x*a.y for a,b in zip(pts,pts[1:]+pts[:1])))/2
        # Accepted mesh already separates its palm, dorsal and finger pad shells.
        region_faces.append({'component':root, 'palm':len(verts) in (1267,188,278),
                             'uv':[list(v) for v in pts]})
    data['components'].append({'id':root, 'verts':len(verts), 'center':list(avg),
                               'area':area, 'uv_area':uv_area,
                               'boundary_edges':sum(edge_uses[e.key]==1 for e in obj.data.edges if find(e.vertices[0])==root),
                               'bounds':[[min(v.co[i] for v in verts), max(v.co[i] for v in verts)] for i in range(3)]})
    total_uv += uv_area
    total_area += area
data['total_uv_area'] = total_uv
data['total_mesh_area'] = total_area
data['leather_uv_repeat_for_25cm_scan'] = (total_area/total_uv)**.5/.25
(OUT/'geometry_metrics.json').write_text(json.dumps(data,indent=2))
(OUT/'region_faces.json').write_text(json.dumps(region_faces))
(OUT/'seam_segments.json').write_text(json.dumps(seam_segments))
print('ARMS_LEATHER_GEOMETRY',json.dumps(data))
