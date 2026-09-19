import bpy,json
from pathlib import Path
O=Path(__file__).parent;result={}
for gun in ['M4','AKM','QBZ']:
 bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ExtMagRebuild20260919'/(gun+'_ExtMag_Editable.blend')))
 m=bpy.data.objects['Factory_'+gun].data;m.calc_loop_triangles();uv=m.uv_layers.active.data
 print(gun,[(l.name,l.active_render,len({tuple(x.uv) for x in l.data})) for l in m.uv_layers],flush=True)
 result[gun]=[{'uv':list(sum((uv[i].uv for i in t.loops),uv[t.loops[0]].uv*0)/3),'area':t.area} for t in m.loop_triangles]
(O/'uv_samples.json').write_text(json.dumps(result))
