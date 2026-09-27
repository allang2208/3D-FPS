"""Read the accepted game mesh's mounting frame for authoring new game parts."""
import bpy, json
from pathlib import Path

O=Path(__file__).parent
try:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error): raise
rig=bpy.data.objects['SK_DW715_Manny']
inv=rig.data.bones['WPN_root'].matrix_local.inverted()
parts={}
for ob in bpy.data.objects:
    if ob.type!='MESH' or not ob.name.startswith('DW715'): continue
    points=[inv@v.co for v in ob.data.vertices]
    parts[ob.name]={'materials':[s.name for s in ob.data.materials], 'vertices':len(points),
        'min':[round(min(p[i] for p in points),6) for i in range(3)],
        'max':[round(max(p[i] for p in points),6) for i in range(3)]}
(O/'source_contract.json').write_text(json.dumps(parts,indent=2))
print(json.dumps(parts,indent=2),flush=True)
