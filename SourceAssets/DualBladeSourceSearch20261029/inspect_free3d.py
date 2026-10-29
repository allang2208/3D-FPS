import bpy,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
report={}
for path in OUT.glob('Free3D_*.fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    info={'objects':[{'name':o.name,'type':o.type} for o in bpy.data.objects],
          'fps':bpy.context.scene.render.fps/bpy.context.scene.render.fps_base,
          'actions':[{'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions]}
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    info['bones']=[b.name for b in arm.data.bones]
    report[path.name]=info
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(path.stem+'.blend')))
(OUT/'free3d-inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
