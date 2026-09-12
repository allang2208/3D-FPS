import bpy, json
from pathlib import Path

O = Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'))
obj = bpy.data.objects['SK_Manny_Arms_Export']
groups = {g.index: g.name for g in obj.vertex_groups}
regions = {}
for poly in obj.data.polygons:
    scores = {}
    for vi in poly.vertices:
        for g in obj.data.vertices[vi].groups:
            name = groups[g.group]
            part = 'hand' if name.startswith(('hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) else name
            scores[part] = scores.get(part, 0) + g.weight
    region = max(scores, key=scores.get) if scores else 'none'
    key = obj.data.materials[poly.material_index].name + ':' + region
    row = regions.setdefault(key, {'polygons':0,'uv_min':[1e9,1e9],'uv_max':[-1e9,-1e9]})
    row['polygons'] += 1
    for li in poly.loop_indices:
        uv = obj.data.uv_layers.active.data[li].uv
        for j in range(2):
            row['uv_min'][j] = min(row['uv_min'][j], uv[j])
            row['uv_max'][j] = max(row['uv_max'][j], uv[j])
(O/'regions.json').write_text(json.dumps(regions, indent=2))
print('ARMS_REGIONS', json.dumps(regions))
parents = list(range(len(obj.data.vertices)))
def find(i):
    while parents[i] != i:
        parents[i] = parents[parents[i]]
        i = parents[i]
    return i
for edge in obj.data.edges:
    a, b = [find(i) for i in edge.vertices]
    parents[b] = a
parts = {}
for v in obj.data.vertices:
    row = parts.setdefault(find(v.index), {'verts':[], 'hand':0})
    row['verts'].append(v.index)
    row['hand'] += sum(g.weight for g in v.groups if groups[g.group].startswith(('hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')))
summary = [{'id':k,'verts':len(v['verts']),'hand':v['hand']/len(v['verts'])} for k,v in parts.items()]
(O/'components.json').write_text(json.dumps(summary,indent=2))
hand_parts = {k for k,v in parts.items() if v['hand']/len(v['verts']) > .5}
uv_faces = []
for p in obj.data.polygons:
    if find(p.vertices[0]) in hand_parts:
        assert obj.data.materials[p.material_index].name == 'MI_Manny_02'
        uv_faces.append([list(obj.data.uv_layers.active.data[li].uv) for li in p.loop_indices])
(O/'glove_uv_faces.json').write_text(json.dumps(uv_faces))
print('GLOVE_COMPONENTS', [r for r in summary if r['id'] in hand_parts], 'faces',len(uv_faces))
