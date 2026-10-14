import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];scene=bpy.context.scene;arm=bpy.data.objects['GamedevTreasureChestRig'];scene.frame_set(1)
meshes=[o for o in scene.objects if o.type=='MESH' and o.parent==arm]
report={'blender':bpy.app.version_string,'unit_scale':scene.unit_settings.scale_length,'parts':len(meshes),'bones':[b.name for b in arm.data.bones],'fps':scene.render.fps,'frames':[scene.frame_start,scene.frame_end],'action':arm.animation_data.action.name,'mesh_audits':[],'animation_samples':[]}
for ob in meshes:
    me=ob.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me)
    u=me.uv_layers[0];zero_uv=0;zero_geo=0
    for t in me.loop_triangles:
        a,b,c=[u.data[j].uv for j in t.loops]
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-12:zero_uv+=1
        if t.area<1e-10:zero_geo+=1
    report['mesh_audits'].append({'name':ob.name,'triangles':len(me.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_triangles':zero_geo,'zero_uv_triangles':zero_uv,'uv_names':[l.name for l in me.uv_layers]});bm.free()
report['totals']={key:sum(x[key] for x in report['mesh_audits']) for key in ['triangles','boundary_edges','nonmanifold_edges','zero_area_triangles','zero_uv_triangles']}
for f in range(1,32):
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in meshes:
        ev=o.evaluated_get(dg);pts += [ev.matrix_world@Vector(p) for p in ev.bound_box]
    report['animation_samples'].append({'frame':f,'lid_matrix':[list(row) for row in arm.pose.bones['Lid'].matrix],'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]})
scene.frame_set(1)

(ROOT/'reports/validation_v3.json').write_text(json.dumps(report,indent=2));print('V3_TOTALS',report['totals'])
