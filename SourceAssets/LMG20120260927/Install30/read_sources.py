import bpy,json
from pathlib import Path
O=Path(__file__).parent
out={}
for key,src in [('native','Video26/LMG201_Video26_Editable.blend'),('candidate','Refine29/LMG201_R29_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/src),use_scripts=False)
    rig=bpy.data.objects.get('SK_M4_Infima')
    root=rig.data.bones['WPN_root'].matrix_local.copy() if rig else None
    items=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or ob.name.startswith('H26_') or ob.name.startswith('HIGH_'):continue
        tf=root.inverted()@ob.matrix_world if root else ob.matrix_world
        ps=[tf@v.co for v in ob.data.vertices]
        if not ps:continue
        items.append(dict(name=ob.name,materials=[m.name if m else None for m in ob.data.materials],
          groups=[g.name for g in ob.vertex_groups],hidden=ob.hide_render,
          bounds=[[min(p[k] for p in ps),max(p[k] for p in ps)] for k in range(3)],
          custom=dict(ob.items())))
    out[key]={'objects':items}
    if rig:out[key]['rig']={'matrix':[list(row) for row in rig.matrix_world],
        'bones':{b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones},
        'root_bounds_frame':'Blender WPN_root local'}
(O/'source_interfaces.json').write_text(json.dumps(out,indent=2,default=str))
print('Source interfaces written',flush=True)
