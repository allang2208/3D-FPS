"""Read authoring reticle geometry and its original image, without rendering."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent;record={}
for key in ['holographic','panoramic_red_dot']:
    bpy.ops.wm.open_mainfile(filepath=str(S/'M1911AttachmentPolish20260927'/('M1911_'+key+'_RoundedMount_Editable.blend')))
    ob=bpy.data.objects['SM_M1911_'+key+'_Rounded20260927'];me=ob.data
    slot=next(i for i,m in enumerate(me.materials) if m and 'Reticle' in m.name)
    ids={i for f in me.polygons if f.material_index==slot for i in f.vertices};pts=[me.vertices[i].co for i in ids]
    record[key]={'slot':slot,'material':me.materials[slot].name,'bounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],
                 'images':[{'name':im.name,'path':im.filepath} for im in bpy.data.images if 'Red' in im.name or 'Dot' in im.name]}
    if key=='holographic':
        mat=me.materials[slot]
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image:
                im=node.image;im.filepath_raw=str(O/'source_holo_reticle.png');im.file_format='PNG';im.save();record[key]['image_export']=im.filepath_raw
(O/'source_inputs.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('RETICLE_AUTHORING_INPUTS_READY',flush=True)
