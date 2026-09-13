import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'QBZ191_ReceiverCoating_Editable.blend'))
data=json.loads((O/'coating.json').read_text())
for key,info in data.items():info['export_slots']=[m.name for m in bpy.data.objects['SM_QBZ191_'+key].data.materials]
(O/'coating.json').write_text(json.dumps(data,indent=2))
