import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24SprintSupport20261028/M24_SupportedSprint_Editable.blend'),use_scripts=False)
skin=bpy.data.objects['M24_V9_BareArms'];deltas=np.load(O/'elbow_correctives.npz');P=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data])
for name in deltas.files:
 key=skin.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(P+deltas[name]/100).ravel());key.value=0
skin.data.update();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ElbowCorrected_Editable.blend'));print('M24_ELBOW_SOURCE_SAVED',len(deltas.files),flush=True)
