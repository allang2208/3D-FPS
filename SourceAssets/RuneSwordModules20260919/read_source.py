"""Read original geometry needed to place the modular cuts; no renders/tests."""
import bpy,json
from pathlib import Path
P=Path(__file__).parent
source=P.parent/'RuneSword20260913/CompactNaturalV4/AzureRunesword_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_RuneSword_Rig']; obj=bpy.data.objects['RuneSword_Blade']
frame=rig.data.bones['WPN_root'].matrix_local
points=[frame.inverted()@v.co for v in obj.data.vertices]
rows=[]
for k in range(-32,21):
 z=k*.01; band=[p for p in points if abs(p.z-z)<.004]
 if band: rows.append({'z':round(z,3),'x':[min(p.x for p in band),max(p.x for p in band)],'y':[min(p.y for p in band),max(p.y for p in band)]})
data={'source':str(source),'bounds':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],'slices':rows,'materials':[m.name for m in obj.data.materials],'trace':{name:list(frame.inverted()@rig.data.bones[name].head_local) for name in ['Blade_Base','Blade_Tip']}}
(P/'source_dimensions.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
