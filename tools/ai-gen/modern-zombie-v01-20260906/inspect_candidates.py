import bpy,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent
report={}
for name,path in [('pixelhouse_walk',R/'pixelhouse/walk.FBX'),('pixelhouse_fury',R/'pixelhouse/fury.FBX'),('quaternius',R.parents[2]/'assets/models/zombie_quaternius.glb')]:
 try:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
  if path.suffix.lower()=='.fbx':bpy.ops.wm.fbx_import(filepath=str(path))
  else:bpy.ops.import_scene.gltf(filepath=str(path))
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
  arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
  report[name]={'meshes':[{'name':m.name,'vertices':len(m.data.vertices),'triangles':sum(len(p.vertices)-2 for p in m.data.polygons),'materials':[x.name if x else None for x in m.data.materials],'bounds':[[min((m.matrix_world@v.co)[i] for v in m.data.vertices),max((m.matrix_world@v.co)[i] for v in m.data.vertices)] for i in range(3)]} for m in meshes], 'rigs':[{'name':a.name,'bones':[b.name for b in a.data.bones]} for a in arms],'clips':{a.name:list(a.frame_range) for a in bpy.data.actions}}
  bpy.ops.wm.save_as_mainfile(filepath=str(R/(name+'.blend')))
  print('CANDIDATE',name,json.dumps(report[name]),flush=True)
 except Exception as e:report[name]={'error':str(e)};traceback.print_exc()
(R/'candidate-report.json').write_text(json.dumps(report,indent=2))
