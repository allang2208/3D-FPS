import bpy, json
from pathlib import Path
sources=[Path('E:/3d/m16-staging/m16-modular-editable.blend'),Path('E:/3d/hands-geometry-20260909/accepted_bare_hands_v2/editable_bare_v2/m16.blend')]
for source in sources:
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    result={'source':str(source),'frame':bpy.context.scene.frame_current,'objects':[]}
    for o in bpy.context.scene.objects:
        if o.type not in {'MESH','ARMATURE','EMPTY'}: continue
        item={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'scale':list(o.scale)}
        if o.type=='MESH': item.update(vertices=len(o.data.vertices),materials=[m.name if m else None for m in o.data.materials],groups=[g.name for g in o.vertex_groups])
        if o.type=='ARMATURE': item['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(o.matrix_world@b.head_local)} for b in o.data.bones if o.name=='M16_Mechanism']
        result['objects'].append(item)
    print('M16_SOURCE '+json.dumps(result))
