import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Bipod07/PKM_Gameplay_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig']
report={'objects':[], 'bones':len(r.data.bones),'actions':[]}
for o in bpy.context.scene.objects:
 if o.type=='MESH' and (o.get('source_part_id') in list(range(6))+[113,126] or o.get('mechanical_bone') in ['PKM_Belt_00','PKM_Belt_01']):
  report['objects'].append({'name':o.name,'properties':{k:str(o[k]) for k in o.keys()},'vertices':len(o.data.vertices),'materials':[s.material.name if s.material else None for s in o.material_slots], 'matrix':[list(row) for row in o.matrix_world], 'uv':[u.name for u in o.data.uv_layers]})
for a in bpy.data.actions:
 if a.name.startswith('PKM'):report['actions'].append({'name':a.name,'frames':list(a.frame_range),'slots':[s.identifier for s in a.slots]})
(O/'authoring_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2),flush=True)
