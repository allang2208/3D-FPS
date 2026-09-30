import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/BeltFeed08')
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Skin07/LMG201_SkinProfile_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();R=r.data.bones['WPN_root'].matrix_local.inverted()
out={'bones':{b.name:{'parent':b.parent.name if b.parent else None,'head':list(R@b.head_local)} for b in r.data.bones if b.name.startswith(('WPN','IK_'))},'objects':{}}
for ob in bpy.data.objects:
 if ob.type=='MESH' and ob.name.startswith('LMG201'):
  vs=[R@ob.matrix_world@v.co for v in ob.data.vertices]
  out['objects'][ob.name]={'vertices':len(vs),'bounds':[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],'groups':[g.name for g in ob.vertex_groups],'materials':[m.name if m else None for m in ob.data.materials]}
(O/'authoring_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out),flush=True)