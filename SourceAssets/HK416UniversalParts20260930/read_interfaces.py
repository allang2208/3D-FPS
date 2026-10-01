import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent
files={'M1911':S/'M1911AttachmentPolish20260927/M1911_holographic_RoundedMount_Editable.blend','G18':S/'G18AttachmentRepair20260930/Exports/SM_G18_holographic_Editable.blend','DW715':S/'DanWesson715Attachments20260914/holographic/DW715_Attachment_Editable.blend'}
r={}
for key,file in files.items():
    bpy.ops.wm.open_mainfile(filepath=str(file));r[key]={'file':str(file),'meshes':{}}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        mats={}
        for i,m in enumerate(ob.data.materials):
            v=[ob.matrix_world@ob.data.vertices[j].co for f in ob.data.polygons if f.material_index==i for j in f.vertices]
            if v:mats[m.name]={'faces':sum(f.material_index==i for f in ob.data.polygons),'bounds':[[min(p[k] for p in v),max(p[k] for p in v)] for k in range(3)]}
        r[key]['meshes'][ob.name]=mats
(O/'interfaces.json').write_text(json.dumps(r,indent=2))
