import bpy,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima')
p=root/'Original/Blender_Source_Files_FreeFpsTemplate/Animations/Animations_Assault_Rifle.blend'
bpy.ops.wm.open_mainfile(filepath=str(p))
report={'objects':[{'name':o.name,'type':o.type,'library':o.library.filepath if o.library else None,'bones':[b.name for b in o.data.bones] if o.type=='ARMATURE' else [],'parent':o.parent.name if o.parent else None}for o in bpy.data.objects],'actions':[{'name':a.name,'range':list(a.frame_range)}for a in bpy.data.actions],'fps':bpy.context.scene.render.fps}
(root/'source_inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
