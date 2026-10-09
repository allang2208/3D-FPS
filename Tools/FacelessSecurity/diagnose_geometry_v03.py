"""Report the geometry and evaluated extremities for the reported disappearance."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
OUT=ROOT/'V03/Diagnosis';OUT.mkdir(parents=True,exist_ok=True)
report={}
def describe():
    result={}
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        if o.name not in ['Security_OutfitBody','Security_Shirt_Continuous','Security_Trousers_Continuous'] and not o.name.startswith(('Security_Boot_','Security_BootSole_','Security_Cuff_')):continue
        dg=bpy.context.evaluated_depsgraph_get();obj=o.evaluated_get(dg);me=obj.to_mesh()
        points=np.array([obj.matrix_world@v.co for v in me.vertices]);groups={g.index:g.name for g in o.vertex_groups}
        row={'vertices':len(points),'bounds':[points.min(0).tolist(),points.max(0).tolist()],'limbs':{}}
        for b in ['hand_l','hand_r','foot_l','foot_r','ball_l','ball_r']:
            ids=[v.index for v in o.data.vertices if sum(g.weight for g in v.groups if groups[g.group]==b)>.45]
            if ids and len(points)==len(o.data.vertices):
                p=points[ids];row['limbs'][b]={'vertices':len(ids),'bounds':[p.min(0).tolist(),p.max(0).tolist()]}
        result[o.name]=row;obj.to_mesh_clear()
    return result
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'V01/Authoring/FacelessSecurity_V01.blend'))
rig=bpy.data.objects['root'];rig.animation_data_clear();bpy.context.view_layer.update()
report['rest']=describe();report['rig_matrix']=[list(x) for x in rig.matrix_world]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'V02/Motion/FacelessSecurity_MaleMotion_V02.blend'))
rig=bpy.data.objects['root']
for tr in rig.animation_data.nla_tracks:tr.mute=True
for role in ['idle','walk','attack']:
    act=bpy.data.actions['Security_MaleV02_'+role];rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0]
    for f in [1,37]:
        bpy.context.scene.frame_set(f);report[role+str(f)]=describe()
(OUT/'geometry_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_GEOMETRY_CAPTURED',flush=True)
