import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
out={}
for label in ('m24','baseline'):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(O/(label+'.fbx')),use_anim=False)
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');meshes=[o for o in bpy.data.objects if o.type=='MESH']
 out[label]={'rig':rig.name,'rig_matrix':[list(x) for x in rig.matrix_world],'bones':{b.name:[list(x) for x in b.matrix_local] for b in rig.data.bones},'objects':[]}
 for m in meshes:
  out[label]['objects'].append({'name':m.name,'matrix':[list(x) for x in m.matrix_world],'vertices':len(m.data.vertices),'triangles':len(m.data.polygons),'materials':[x.name if x else None for x in m.data.materials],'shapes':[k.name for k in m.data.shape_keys.key_blocks] if m.data.shape_keys else []})
(O/'mesh_probe.json').write_text(json.dumps(out,indent=2));print('MESH_PROBE_COMPLETE',flush=True)
