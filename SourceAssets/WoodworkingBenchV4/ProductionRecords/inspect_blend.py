import bpy,json
from pathlib import Path
from mathutils import Vector
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_v4_import_20261008')
R=Path('D:/FPS3D/FPSGAME/SourceAssets/WoodworkingBenchV4/Source/WoodworkingBench')
dg=bpy.context.evaluated_depsgraph_get();records=[]
for o in bpy.context.scene.objects:
    if o.type not in {'MESH','CURVE','SURFACE','FONT'}:continue
    e=o.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();pts=[o.matrix_world@v.co for v in m.vertices]
    records.append({'name':o.name,'type':o.type,'tris':len(m.loop_triangles),'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)],'matrix':[list(r) for r in o.matrix_world],'materials':[s.material.name if s.material else None for s in o.material_slots],'props':{k:str(v) for k,v in o.items()},'uvs':[v.name for v in m.uv_layers]})
    e.to_mesh_clear()
mats=[]
for m in bpy.data.materials:
    mats.append({'name':m.name,'nodes':[{'name':n.name,'type':n.type,'inputs':{s.name:str(s.default_value[:]) if hasattr(s.default_value,'__len__') else str(s.default_value) for s in n.inputs if hasattr(s,'default_value')},'image':n.image.filepath if n.type=='TEX_IMAGE' and n.image else None} for n in m.node_tree.nodes] if m.use_nodes else [],'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links] if m.use_nodes else []})
report={'objects':records,'objects_count':len(records),'triangles':sum(r['tris'] for r in records),'materials':mats,'images':[{'name':i.name,'path':i.filepath,'packed':bool(i.packed_file)} for i in bpy.data.images],'units':bpy.context.scene.unit_settings.scale_length}
(W/'blend_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V4_INSPECTION',len(records),report['triangles'])
for r in records:
    if any(s in r['name'].lower() for s in ['retained','blade','guard','insert','throat']):print(json.dumps(r))
