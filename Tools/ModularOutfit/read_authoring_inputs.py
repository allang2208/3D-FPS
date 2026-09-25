import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
report={}
for key in ('Body','M4','PKM','SVD','M1911_l'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'Inputs'/f'{key}.fbx'),use_anim=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    def co(v):return [round(x,5) for x in v]
    report[key]={'rig':rig.name,'scale':co(rig.scale),'bones':{b.name:co(rig.matrix_world@b.head_local) for b in rig.data.bones if b.name in ('root','pelvis','spine_01','spine_03','neck_01','upperarm_l','lowerarm_l','hand_l','middle_01_l','middle_03_l','upperarm_r','lowerarm_r','hand_r')},'objects':[]}
    for obj in bpy.data.objects:
        if obj.type!='MESH':continue
        coords=[obj.matrix_world@v.co for v in obj.data.vertices]
        report[key]['objects'].append({'name':obj.name,'verts':len(coords),'min':co(Vector(tuple(min(v[i] for v in coords) for i in range(3)))),'max':co(Vector(tuple(max(v[i] for v in coords) for i in range(3)))),'materials':[m.name if m else '' for m in obj.data.materials]})
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=str(ROOT/'Donor/sweater_fisherman.obj'))
obj=next(o for o in bpy.data.objects if o.type=='MESH')
vs=[obj.matrix_world@v.co for v in obj.data.vertices]
report['sweater']={'verts':len(vs),'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)]}
(ROOT/'authoring-inputs.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
