from pathlib import Path
import bpy,numpy as np,json
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O.parent/'M24Meshy1105135808Replacement/Input/Meshy_AI_Carbon_Stock_1105135808_texture.glb'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data
p=np.array([v.co[:] for v in me.vertices]);ed=np.array([e.vertices[:] for e in me.edges]);a,b=p[ed[:,0]],p[ed[:,1]]
r={'bounds':[p.min(0).tolist(),p.max(0).tolist()],'matrix':[list(row) for row in ob.matrix_world],'sections':{}}
scale=.3185991175/1.90327501
for x in (-.950,-.941,-.920,-.900,-.870,-.840,-.80,-.75):
    mask=((a[:,0]<x)&(b[:,0]>=x))|((b[:,0]<x)&(a[:,0]>=x))
    aa,bb=a[mask],b[mask];v=aa+(bb-aa)*((x-aa[:,0])/(bb[:,0]-aa[:,0]))[:,None]
    r['sections'][str(x)]={'lo':v.min(0).tolist(),'hi':v.max(0).tolist(),'size_at_game_mm':((v.max(0)-v.min(0))*scale*1000).tolist()}
(O/'raw_sections.json').write_text(json.dumps(r,indent=2));print(r)
