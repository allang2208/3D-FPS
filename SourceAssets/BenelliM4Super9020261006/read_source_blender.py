import bpy,json
from pathlib import Path
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Original/Source/source/HandWithGloves_AnimateRDY.fbx'))
rows=[]
for ob in bpy.context.scene.objects:
 r={'name':ob.name,'type':ob.type,'parent':ob.parent.name if ob.parent else None,'matrix_world':[list(row) for row in ob.matrix_world]}
 if ob.type=='MESH':
  m=ob.data;m.calc_loop_triangles();points=[ob.matrix_world@v.co for v in m.vertices]
  weight={}
  for v in m.vertices:
   for g in v.groups:
    name=ob.vertex_groups[g.group].name;weight[name]=weight.get(name,0)+g.weight
  r.update(vertices=len(points),triangles=len(m.loop_triangles),materials=[m.name if m else None for m in m.materials],bounds={'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]},groups=weight)
 if ob.type=='ARMATURE':r['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local),'matrix':[list(row) for row in b.matrix_local]} for b in ob.data.bones]
 rows.append(r)
report={'fps':bpy.context.scene.render.fps,'objects':rows,'actions':[{'name':a.name,'range':list(a.frame_range),'slots':[{'identifier':s.identifier,'target_id_type':s.target_id_type} for s in a.slots]} for a in bpy.data.actions]}
(O/'source_inventory.json').write_text(json.dumps(report,indent=2))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'BenelliM4_Original_Editable.blend'))
print(json.dumps({'fps':report['fps'],'objects':[{k:v for k,v in r.items() if k not in ('matrix_world','bones')} for r in rows],'actions':report['actions']},indent=2),flush=True)
