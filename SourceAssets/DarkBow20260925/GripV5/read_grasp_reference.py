import bpy,json
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).parent;ROOT=P.parents[2]
source=ROOT/'SourceAssets/MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
fit=json.loads((ROOT/'SourceAssets/MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
grip=rig.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])
out={'source':str(source),'grip':[list(v) for v in grip],
     'rest':{b.name:[list(v) for v in b.matrix_local] for b in rig.data.bones},
     'pose':{b.name:[list(v) for v in b.matrix] for b in rig.pose.bones}}
(P/'grasp_reference.json').write_text(json.dumps(out),encoding='utf-8')
print('BOW_GRASP_REFERENCE_READ',rig.animation_data.action.name)
