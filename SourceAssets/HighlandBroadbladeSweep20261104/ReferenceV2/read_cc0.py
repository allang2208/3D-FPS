import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'CC0-Arms.fbx'))
report={'actions':[{ 'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions],'objects':[{ 'name':o.name,'type':o.type,'bones':[b.name for b in o.data.bones] if o.type=='ARMATURE' else []} for o in bpy.context.scene.objects]}
(P/'cc0-actions.json').write_text(json.dumps(report,indent=2))
print('CC0_ACTIONS',report['actions'])
