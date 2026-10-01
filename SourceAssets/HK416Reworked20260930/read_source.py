"""Source component inventory requested by the user; also supplies authoring measurements."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Original/source/HK_416_Full_HighPoly.fbx'))
rows=[]
for ob in bpy.context.scene.objects:
    record={'name':ob.name,'type':ob.type,'parent':ob.parent.name if ob.parent else None,'matrix_world':[list(r) for r in ob.matrix_world]}
    if ob.type=='MESH':
        mesh=ob.data;mesh.calc_loop_triangles();points=[ob.matrix_world@v.co for v in mesh.vertices]
        record.update(vertices=len(points),triangles=len(mesh.loop_triangles),materials=[m.name if m else None for m in mesh.materials],
            bounds={'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]},
            uv_layers=[x.name for x in mesh.uv_layers],groups=[g.name for g in ob.vertex_groups])
    elif ob.type=='ARMATURE':record['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None} for b in ob.data.bones]
    rows.append(record)
out={'objects':rows,'actions':[a.name for a in bpy.data.actions],'materials':[m.name for m in bpy.data.materials]}
(O/'source_inventory.json').write_text(json.dumps(out,indent=2))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'HK416_Original_Editable.blend'))
for row in rows:print('SOURCE_PART',json.dumps({k:v for k,v in row.items() if k!='matrix_world'}),flush=True)
print('SOURCE_TOTAL_TRIANGLES',sum(r.get('triangles',0) for r in rows),flush=True)
