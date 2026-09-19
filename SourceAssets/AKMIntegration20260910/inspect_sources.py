import bpy,json
from pathlib import Path
O=Path(__file__).parent;report={}
for tag,path in [('akm',O.parent/'ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend'),('m4',O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path))
 report[tag]={'objects':[(o.name,o.type,len(o.data.vertices) if o.type=='MESH' else 0) for o in bpy.context.scene.objects], 'rigs':{o.name:{b.name:[list(b.head_local),list(b.tail_local)] for b in o.data.bones} for o in bpy.context.scene.objects if o.type=='ARMATURE'},'actions':[(a.name,list(a.frame_range)) for a in bpy.data.actions]}
(O/'sources.json').write_text(json.dumps(report,indent=2));print('SOURCES_INSPECTED')
