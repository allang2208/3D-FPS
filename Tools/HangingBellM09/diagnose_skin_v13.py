"""Offline diagnosis requested for stretched Gaze hands; no render or game launch."""
import bpy, json,sys
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'SkinDeathV13/Records';OUT.mkdir(parents=True,exist_ok=True)
after='--after' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(ROOT/('SkinDeathV13/Authoring/M09_Rigged_V13.blend' if after else 'GazeV08/Authoring/M09_Gaze_V08.blend')))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene
if after:
 with bpy.data.libraries.load(str(ROOT/'GazeV08/Authoring/M09_Gaze_V08.blend')) as (src,dst):dst.actions=['A_M09_Gaze_V08']
 rig.animation_data_create();rig.animation_data.action=dst.actions[0]
 rig.animation_data.action_slot=dst.actions[0].slots[0]
recipe=json.loads((ROOT/'RigV03/Authoring/rig_recipe_v03.json').read_text())
report=[]
for part in recipe['parts']:
 if part['id'] not in (0,7,8,9):continue
 ob=bpy.data.objects[part['name']];mesh=ob.data
 rest=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',rest.ravel())
 matrix=np.array(ob.matrix_world);rest=rest@matrix[:3,:3].T+matrix[:3,3]
 edges=np.empty((len(mesh.edges),2),np.int32);mesh.edges.foreach_get('vertices',edges.ravel())
 base=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
 for frame in (1,43,76,112):
  scene.frame_set(frame);bpy.context.view_layer.update()
  eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=eo.to_mesh()
  posed=np.empty_like(rest);em.vertices.foreach_get('co',posed.ravel());m=np.array(eo.matrix_world)
  posed=posed@m[:3,:3].T+m[:3,3];eo.to_mesh_clear()
  lengths=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)
  extra=lengths-base
  order=np.argsort(extra)[-12:][::-1]
  worst=[]
  for e in order:
   verts=[]
   for vi in edges[e]:
    v=mesh.vertices[int(vi)]
    verts.append({'id':int(vi),'rest':rest[vi].tolist(),'posed':posed[vi].tolist(),
      'weights':{ob.vertex_groups[g.group].name:round(g.weight,4) for g in v.groups if g.weight>0}})
   worst.append({'rest_cm':float(base[e]*100),'posed_cm':float(lengths[e]*100),'vertices':verts})
  item={'part':part['name'],'frame':frame,'edges_stretched_over_5cm':int((extra>.05).sum()),
    'max_extra_cm':float(extra.max()*100),'worst':worst}
  source=np.empty(len(mesh.vertices),np.int32);mesh.attributes['source_vertex_id'].data.foreach_get('value',source)
  original=(source[edges]>=0).all(axis=1)
  original_order=np.flatnonzero(original)[np.argsort(extra[original])[-8:][::-1]]
  item['original_max_extra_cm']=float(extra[original].max()*100)
  item['original_bad']=[{'rest_cm':float(base[e]*100),'posed_cm':float(lengths[e]*100),
   'vertices':[{'id':int(v),'rest':rest[v].tolist(),'weights':{ob.vertex_groups[g.group].name:round(g.weight,4) for g in mesh.vertices[int(v)].groups if g.weight>0}} for v in edges[e]]} for e in original_order]
  report.append(item);print('M09_SKIN_DIAG',part['name'],frame,item['edges_stretched_over_5cm'],item['max_extra_cm'],flush=True)
(OUT/('skin_after.json' if after else 'skin_before.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
