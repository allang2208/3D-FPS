import bpy, json
from pathlib import Path
from collections import defaultdict
O = Path(__file__).parent
S = O.parent / 'BenelliM4Super9020261006'
result = {}
for name in ('BenelliM4_Original_Editable.blend', 'Super90_Gameplay_Editable.blend'):
    bpy.ops.wm.open_mainfile(filepath=str(S/name))
    rows = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or not ('benelli' in ob.name.lower() or ob.name in ('Super90_body', 'Super90_bolt', 'Super90_loading_gate', 'Super90_trigger', '12g_12gauge_0')):
            continue
        me = ob.data
        uv = me.uv_layers[0].data
        row = {'name': ob.name, 'mapping': me.get('Super90AtlasMapping'), 'layers': [v.name for v in me.uv_layers], 'islands': [], 'materials': []}
        for m in me.materials:
            row['materials'].append({'name': m.name, 'nodes': [{'name': n.name, 'type': n.type, 'image': n.image.filepath if n.type == 'TEX_IMAGE' and n.image else None, 'inputs': {i.name: list(i.default_value) for i in n.inputs if i.type == 'VECTOR'}} for n in m.node_tree.nodes] if m.use_nodes else []})
        parent = list(range(len(me.polygons)))
        corner = {}
        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for f in me.polygons:
            for li in f.loop_indices:
                k = (*[round(x, 6) for x in me.vertices[me.loops[li].vertex_index].co], *[round(x, 6) for x in uv[li].uv], f.material_index)
                if k in corner:
                    parent[find(f.index)] = find(corner[k])
                else:
                    corner[k] = f.index
        groups = defaultdict(list)
        for f in me.polygons:
            groups[find(f.index)].append(f)
        for faces in sorted(groups.values(), key=lambda fs: sum(f.area for f in fs), reverse=True)[:30]:
            coords = [me.vertices[me.loops[li].vertex_index].co for f in faces for li in f.loop_indices]
            uvs = [uv[li].uv for f in faces for li in f.loop_indices]
            row['islands'].append({'faces': len(faces), 'material': me.materials[faces[0].material_index].name, 'xyz_bounds': [[min(c[k] for c in coords),max(c[k] for c in coords)] for k in range(3)], 'uv_bounds': [[min(c[k] for c in uvs),max(c[k] for c in uvs)] for k in range(2)], 'sample': [{'co': list(me.vertices[me.loops[li].vertex_index].co), 'uv': list(uv[li].uv)} for li in faces[0].loop_indices]})
        rows.append(row)
    result[name] = rows
(O/'author_inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('SUPER90_AUTHOR_READ', [(k, len(v)) for k,v in result.items()])
