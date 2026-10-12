import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_Super90']
d={'objects':{},'bones':{b.name:[list(row) for row in r.matrix_world@b.matrix_local] for b in r.data.bones},'actions':{a.name:list(a.frame_range) for a in bpy.data.actions}}
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or not ob.name.startswith('Super90_V7_'):continue
 groups={g.index:g.name for g in ob.vertex_groups}
 d['objects'][ob.name]={'positions':[list(ob.matrix_world@v.co) for v in ob.data.vertices], 'weights':[{groups[g.group]:g.weight for g in v.groups} for v in ob.data.vertices], 'materials':[s.material.name if s.material else None for s in ob.material_slots]}
(O/'blend_source.json').write_text(json.dumps(d,separators=(',',':')))
print('SUPER90_BLEND_SOURCE',[(n,len(v['positions'])) for n,v in d['objects'].items()],list(d['actions']))
