import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
out={}
for ob in bpy.data.objects:
 if ob.type=='MESH' and ('Ammo' in ob.name or 'TopCover' in ob.name):
  vs=[v.co for v in ob.data.vertices]
  out[ob.name]={'bounds':[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)],'vertices':len(vs),'materials':[m.name for m in ob.data.materials],'world':[list(row) for row in ob.matrix_world]}
(O/'geometry_inputs.json').write_text(json.dumps(out,indent=2))
print('CLOTH_GEOMETRY',json.dumps(out),flush=True)
