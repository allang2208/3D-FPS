import bpy,pathlib,json,math
from mathutils import Vector
R=pathlib.Path(__file__).resolve().parents[1];r=[]
for lod in range(3):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(R/f'output/SM_Incinerator_LOD{lod}.fbx'))
 o=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=o.data;me.calc_loop_triangles();co=[o.matrix_world@Vector(c) for c in o.bound_box]
 entry={'lod':lod,'objects':len(list(bpy.context.scene.objects)),'triangles':len(me.loop_triangles),'material_slots':len(me.materials),'uv_layers':len(me.uv_layers),'origin':list(o.location),'bounds_min':[min(v[i] for v in co) for i in range(3)],'bounds_max':[max(v[i] for v in co) for i in range(3)],'nonfinite_vertices':sum(not all(math.isfinite(v) for v in vert.co) for vert in me.vertices),'zero_area_triangles':sum(t.area<1e-14 for t in me.loop_triangles)}
 r.append(entry)
(R/'output/export_validation.json').write_text(json.dumps(r,indent=2));print('VALIDATION',json.dumps(r))
