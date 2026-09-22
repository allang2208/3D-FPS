"""Read existing anatomical sources and rest frames needed for authoring."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'WitchMeshy20260919'
files={'quinn':ROOT.parent/'WitchFoundation20260920/Sources/Quinn.fbx',
       'nurse':OLD/'Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx'}
report={}
for key,file in files.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(file),use_anim=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    source=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
    rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
    materials=[]
    for i,mat in enumerate(source.data.materials):
        ps=[p for p in source.data.polygons if p.material_index==i]
        if not ps:continue
        ids=set(j for p in ps for j in p.vertices)
        pts=[source.matrix_world@source.data.vertices[j].co for j in ids]
        materials.append({'index':i,'name':mat.name,'faces':len(ps),'vertices':len(ids),
                          'min':[min(p[k] for p in pts) for k in range(3)],'max':[max(p[k] for p in pts) for k in range(3)]})
    report[key]={'file':str(file),'rig':rig.name,'mesh':source.name,'materials':materials,
                 'rest':{n:[list(r) for r in m] for n,m in rest.items()}}
ROOT.mkdir(parents=True,exist_ok=True)
(ROOT/'author_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:{'rig':v['rig'],'materials':v['materials']} for k,v in report.items()}))
