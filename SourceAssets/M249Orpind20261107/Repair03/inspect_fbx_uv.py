from pathlib import Path
import bpy,json,numpy as np
r=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(r.parent/'Exports/SK_M249_V7.fbx'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
uv=o.data.uv_layers[0];out={}
for i,m in enumerate(o.data.materials):
    a=np.array([uv.data[j].uv[:] for p in o.data.polygons if p.material_index==i for j in p.loop_indices])
    if len(a):out[m.name]=dict(min=a.min(0).tolist(),max=a.max(0).tolist(),nonzero_fraction=float(np.mean(np.linalg.norm(a,axis=1)>1e-5)))
(r/'fbx_uv_inspection.json').write_text(json.dumps(out,indent=2))
