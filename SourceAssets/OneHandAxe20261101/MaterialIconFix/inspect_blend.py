import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'TacticalHatchet_Editable.blend'))
r={'images':[], 'materials':[]}
for im in bpy.data.images:
    if im.type=='IMAGE':r['images'].append(dict(name=im.name,path=im.filepath,colorspace=im.colorspace_settings.name))
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    r['materials'].append({'name':mat.name,'nodes':[{'name':n.name,'type':n.type,'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None} for n in mat.node_tree.nodes]})
(P/'blend_before.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('HATCHET_BLEND_READ '+json.dumps(r))
