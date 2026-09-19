"""Locate the generated silver inlay so it faces the sword's broad face."""
import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ballast_rune/FrostPommel_Editable.blend'))
obj=bpy.data.objects['SM_FrostPommel_ballast_rune'];d=obj.data
im=bpy.data.images['base_color'];pixels=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(pixels);pixels=pixels.reshape((im.size[1],im.size[0],4))
bins={n:{'white_area':0,'body_area':0} for n in ['+X','-X','+Y','-Y']}
for f in d.polygons:
    if f.material_index!=1:continue
    co=f.center;axis=0 if abs(co.x)>abs(co.y) else 1;key=('+' if co[axis]>0 else '-')+'XY'[axis]
    uv=sum((d.uv_layers[0].data[i].uv for i in f.loop_indices),Vector((0,0)))/len(f.loop_indices)
    c=pixels[min(im.size[1]-1,max(0,int(uv.y*im.size[1]))),min(im.size[0]-1,max(0,int(uv.x*im.size[0]))),:3]
    bins[key]['body_area']+=f.area
    if min(c)>.40 and max(c)-min(c)<.2:bins[key]['white_area']+=f.area
print('RUNE_DIRECTION',json.dumps(bins),flush=True)
(P/'rune_direction.json').write_text(json.dumps(bins,indent=2))
