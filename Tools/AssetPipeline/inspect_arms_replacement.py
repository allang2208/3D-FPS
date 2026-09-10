import bpy, json
from pathlib import Path
root=Path(r'D:\FPS3D\FPSGAME\SourceAssets\ArmsReplacement')
report={}
for name,file in [('wrad',root/'WRAD_Original/arms.blend'),('target',Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend'))]:
    bpy.ops.wm.open_mainfile(filepath=str(file))
    report[name]=[]
    for obj in bpy.data.objects:
        if obj.type not in ('MESH','ARMATURE'): continue
        data={'name':obj.name,'type':obj.type,'matrix':[list(r) for r in obj.matrix_world],'dimensions':list(obj.dimensions)}
        if obj.type=='MESH':
            data.update(vertices=len(obj.data.vertices),faces=len(obj.data.polygons),materials=[m.name if m else None for m in obj.data.materials],groups=[g.name for g in obj.vertex_groups],modifiers=[{'type':m.type,'object':m.object.name if m.type=='ARMATURE' and m.object else None} for m in obj.modifiers])
        else:
            data['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in obj.data.bones]
        report[name].append(data)
(root/'arms_replacement_inspect.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
