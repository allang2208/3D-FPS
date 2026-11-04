"""Authoring measurements of the accepted source, used to choose mating cuts."""
import bpy, json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'TacticalHatchet_Editable.blend'))
o=bpy.data.objects['SM_TacticalHatchet'];m=o.data
im=bpy.data.images.load(str(P.parent/'Textures/source_image_02.png'),check_existing=True)
w,h=im.size;pixels=list(im.pixels)
profile={}
for poly in m.polygons:
    z=sum(m.vertices[i].co.z for i in poly.vertices)/len(poly.vertices)
    key=round(z*100)
    uv=sum((m.uv_layers.active.data[i].uv for i in poly.loop_indices),__import__('mathutils').Vector((0,0)))/len(poly.loop_indices)
    metallic=pixels[4*(min(h-1,max(0,int(uv.y*h)))*w+min(w-1,max(0,int(uv.x*w))))+2]
    row=profile.setdefault(key,dict(faces=0,nonmetal=0,xmin=1,xmax=-1,ymin=1,ymax=-1))
    row['faces']+=1;row['nonmetal']+=int(metallic<.5)
    for i in poly.vertices:
        v=m.vertices[i].co
        row['xmin']=min(row['xmin'],v.x);row['xmax']=max(row['xmax'],v.x)
        row['ymin']=min(row['ymin'],v.y);row['ymax']=max(row['ymax'],v.y)
(P/'interface_measurements.json').write_text(json.dumps(profile,indent=2))
print('SECTION_PROFILE '+json.dumps(profile))
