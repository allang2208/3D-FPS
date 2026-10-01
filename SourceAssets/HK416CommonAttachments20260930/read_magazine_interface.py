import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;H=O.parent/'HK416Reworked20260930';R=Matrix(json.loads((H/'authoring.json').read_text())['root_matrix'])
for key,file,name in [('drum',O/'Meshes/SM_HK416_large_drum.blend','SM_HK416_large_drum'),('factory',H/'Exports/Attachments/SM_HK416_factory_magazine_Editable.blend','SM_HK416_factory_magazine')]:
 with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
 ob=dst.objects[0];pts=[R.inverted()@v.co for v in ob.data.vertices]
 print(key,'bounds',[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)],flush=True)
 for z in [-.05,-.04,-.03,-.02,-.01,0,.01,.02,.04]:
  sample=[p for p in pts if abs(p.z-z)<.004]
  if sample:print(z,[[min(p[i] for p in sample),max(p[i] for p in sample)] for i in [0,1]],flush=True)
