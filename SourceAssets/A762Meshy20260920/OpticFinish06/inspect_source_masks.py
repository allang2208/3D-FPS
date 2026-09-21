"""Read existing source UVs and optical interior masks; no scene changes/render."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
report={}
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Accessories05'/('SM_A762_'+key+'.blend')))
    report[key]=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        colors={}
        for attr in ob.data.color_attributes:
            values=[x.color[0] for x in attr.data]
            colors[attr.name]={'count':len(values),'min':min(values),'max':max(values),'inner_loops':sum(v<.01 for v in values),'outer_loops':sum(v>.99 for v in values)}
        report[key].append({'object':ob.name,'uvs':[x.name for x in ob.data.uv_layers],'colors':colors})
(O/'source_masks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('A762_OPTIC_SOURCE_MASKS_READ',flush=True)
