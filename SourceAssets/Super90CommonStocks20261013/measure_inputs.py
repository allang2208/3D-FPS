"""Authoring measurements: native manufacturing islands and donor mounting frames."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
result={}
for path in (O/'Inputs').glob('*.fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    rows=[]
    for ob in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        bm=bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.transform(bm,matrix=ob.matrix_world,verts=list(bm.verts))
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
        unseen=set(bm.faces)
        while unseen:
            seed=unseen.pop();fs={seed};stack=[seed]
            while stack:
                for v in stack.pop().verts:
                    for f in v.link_faces:
                        if f in unseen:unseen.remove(f);fs.add(f);stack.append(f)
            vs={v for f in fs for v in f.verts}
            rows.append({'faces':len(fs),'lo':[min(v.co[j] for v in vs) for j in range(3)],'hi':[max(v.co[j] for v in vs) for j in range(3)],'slots':sorted({ob.data.materials[f.material_index].name for f in fs})})
        bm.free()
    result[path.stem]=sorted(rows,key=lambda x:-x['faces'])
(O/'measurements.json').write_text(json.dumps(result,indent=2))
print('AUTHORING_MEASUREMENTS_WRITTEN')
