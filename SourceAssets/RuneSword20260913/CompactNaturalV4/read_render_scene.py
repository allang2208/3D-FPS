import bpy,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
report={'objects':[],'scene':bpy.context.scene.name,'scenes':[s.name for s in bpy.data.scenes]}
for o in bpy.context.scene.objects:
    report['objects'].append({'name':o.name,'type':o.type,'hide_render':o.hide_render,'visible':o.visible_get(),'instance_type':o.instance_type,'dims':list(o.dimensions),'matrix':[list(row) for row in o.matrix_world]})
(P/'render_scene.json').write_text(json.dumps(report,indent=2))
