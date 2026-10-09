"""Authoring input: the V7 skin basis before conversion to the native Super90 rig."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
P=O.parents[2]
source=P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
data={'source':str(source),'rig':rig.name,
      'rest':{b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones},
      'parents':{b.name:b.parent.name if b.parent else None for b in rig.data.bones}}
(O/'v7_skin_basis.json').write_text(json.dumps(data,separators=(',',':')))
print('SUPER90_V7_BASIS_READ',len(data['rest']),flush=True)
