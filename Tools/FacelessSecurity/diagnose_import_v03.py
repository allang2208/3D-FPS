import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
report={}
for name,path in [('delivery',ROOT/'V01/Delivery/SK_FacelessSecurity_V01.fbx'),('ue',ROOT/'V03/Diagnosis/SK_Security_Before.fbx')]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    report[name]={}
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        p=np.array([o.matrix_world@v.co for v in o.data.vertices]);groups={g.index:g.name for g in o.vertex_groups};row={}
        for b in ['hand_l','hand_r','foot_l','foot_r','ball_l','ball_r','middle_01_l','middle_03_l']:
            ids=[v.index for v in o.data.vertices if sum(g.weight for g in v.groups if groups[g.group]==b)>.45]
            if ids:row[b]={'count':len(ids),'bounds':[p[ids].min(0).tolist(),p[ids].max(0).tolist()]}
        row['materials']=[m.name for m in o.data.materials];row['verts']=len(p);row['polys']=len(o.data.polygons)
        report[name][o.name]=row
(ROOT/'V03/Diagnosis/import_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
