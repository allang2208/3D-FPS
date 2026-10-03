"""Compare PSO_ScopeBody topology across A762, AKM, and SVD source."""
import bpy, json
from pathlib import Path

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
rows = []

def fingerprint(path, obj_names):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    out = {'path': str(path)}
    for name in obj_names:
        ob = bpy.data.objects.get(name)
        if not ob:
            out[name] = None; continue
        me = ob.data
        out[name] = {
            'verts': len(me.vertices), 'edges': len(me.edges), 'faces': len(me.polygons),
            'boundary': sum(1 for e in me.edges if len([p for p in me.polygons if e.vertices[0] in p.vertices and e.vertices[1] in p.vertices])==1),
        }
        # cheaper boundary via bmesh
    import bmesh
    for name in obj_names:
        ob = bpy.data.objects.get(name)
        if not ob: continue
        bm = bmesh.new(); bm.from_mesh(ob.data)
        out[name]['boundary'] = sum(1 for e in bm.edges if e.is_boundary)
        out[name]['islands'] = 0
        # island count
        parent = list(range(len(bm.verts)))
        def find(i):
            while parent[i]!=i: parent[i]=parent[parent[i]]; i=parent[i]
            return i
        for e in bm.edges:
            a,b = e.verts; parent[find(a.index)] = find(b.index)
        out[name]['islands'] = len({find(i) for i in range(len(bm.verts))})
        bm.free()
    return out

rows.append(fingerprint(O/'PSO1Russian20260923/PSO1_A762_Editable.blend', ['PSO_ScopeBody','PSO_ScopeMount','PSO_ScopeLens']))
rows.append(fingerprint(O/'PSO1Russian20260923/PSO1_AKM_Editable.blend', ['PSO_ScopeBody','PSO_ScopeMount','PSO_ScopeLens']))
# SVD matte if present
svd = O/'SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend'
if svd.exists():
    rows.append(fingerprint(svd, ['SM_SVD_ScopeBody','SM_SVD_ScopeMount','SM_SVD_ScopeLens']))

(O/'PSO1Russian20260923/inspect_akm_a762/body_compare.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('BODY_COMPARE', json.dumps(rows), flush=True)
