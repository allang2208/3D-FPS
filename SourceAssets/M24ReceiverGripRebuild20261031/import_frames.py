import bpy,json,gzip
import numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent;D=json.load(gzip.open(O/'Inputs/geometry.json.gz','rt'));out={}
for key in ('balanced','phantom','stable','advanced'):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')))
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];v=np.array([list(o.matrix_world@p.co) for o in obs for p in o.data.vertices]);raw=np.array(D[key]['positions'])*.01
 out[key]={'import_min':v.min(0).tolist(),'import_max':v.max(0).tolist(),'ue_min':raw.min(0).tolist(),'ue_max':raw.max(0).tolist(),'objects':[o.name for o in obs]}
(O/'Inputs/fbx_frames.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
