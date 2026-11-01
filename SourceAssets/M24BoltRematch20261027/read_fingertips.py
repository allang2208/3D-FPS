import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'M24CustomScope20261026/Donor/Source/source/arms@sniper.fbx'))
s=bpy.context.scene;r=bpy.data.objects['Armature'];skin=bpy.data.objects['armmesh'];tips={};groups={}
for name in ('R_thumb3','R_point3','R_middle3','R_ring3','R_pink3'):
 g=skin.vertex_groups[name];groups[name]=[v.index for v in skin.data.vertices if any(x.group==g.index and x.weight>.75 for x in v.groups)]
for f in range(1,202):
 s.frame_set(f);bpy.context.view_layer.update();ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();tips[str(f)]={}
 for name,indices in groups.items():
  P=np.array([list(ev.matrix_world@me.vertices[i].co) for i in indices]);head=np.array(r.matrix_world@r.pose.bones[name].head)
  ix=np.argsort(np.linalg.norm(P-head,axis=1));tips[str(f)][name]=P[ix[len(ix)//2:]].mean(0).tolist()
 ev.to_mesh_clear()
(O/'raw_fingertips.json').write_text(json.dumps(tips));print('RAW_SURFACE_TIPS_SAVED',flush=True)
