"""Read the actual exported game meshes; author-requested topology, UV and metre checks."""
import bpy,bmesh,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
manifest=json.loads((OUT/'model-manifest.json').read_text());rows=[]
for asset in manifest['assets']:
    for lod in asset['lods']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=lod['file'],use_custom_normals=True)
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(objects)==1
        o=objects[0];d=o.data;d.calc_loop_triangles();points=[o.matrix_world@v.co for v in d.vertices]
        bounds=[[min(v[i] for v in points)*100 for i in range(3)],[max(v[i] for v in points)*100 for i in range(3)]]
        bm=bmesh.new();bm.from_mesh(d);edges=sum(not e.is_manifold for e in bm.edges);bm.free()
        zero=sum(t.area<1e-12 for t in d.loop_triangles);uvzero=0;uv=d.uv_layers[0]
        for t in d.loop_triangles:
            a,b,c=[uv.data[i].uv for i in t.loops];uvzero+=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-11
        delta=max(abs(bounds[j][i]-asset['bounds_blender_cm'][j][i]) for j in range(2) for i in range(3))
        row=dict(mesh=asset['name'],lod=lod['level'],triangles=len(d.loop_triangles),open_edges=edges,degenerate_triangles=zero,degenerate_uv_triangles=uvzero,bounds_cm=bounds,bounds_delta_cm=delta,uv_layers=[a.name for a in d.uv_layers])
        rows.append(row)
        print('FBX_READBACK',asset['name'],lod['level'],row['triangles'],edges,zero,uvzero,round(delta,5))
        assert not edges and not zero,(asset['name'],lod['level'],'geometry')
        assert delta<.05 if lod['level']==0 else delta<2,(asset['name'],lod['level'],'bounds')
(OUT/'fbx-audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('FBX_AUDIT_COMPLETE',len(rows))
