import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent
R={}
for name in ('vertical','tactical_vertical','canted','prism','angled'):
    p=S/'RSH12Foregrips20261004/Exports'/('SM_RSH12_'+name+'_Editable.blend')
    bpy.ops.wm.open_mainfile(filepath=str(p))
    ob=bpy.data.objects.get('SM_RSH12_'+name)
    R[name]={'source':str(p),'uv_names':[x.name for x in ob.data.uv_layers],'uv_count':len(ob.data.uv_layers)}
(O/'source_uv.json').write_text(json.dumps(R,indent=2),encoding='utf8')
print(json.dumps(R))
